# Vector Database Manager for ATHENA v2.2
import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    VECTOR_DEPS_AVAILABLE = True
except ImportError:
    VECTOR_DEPS_AVAILABLE = False
    chromadb = None
    SentenceTransformer = None

from shared.config import settings

logger = structlog.get_logger()


class VectorDatabaseManager:
    """
    ChromaDB-based vector database for storing and retrieving embeddings
    of news articles and podcast transcripts with temporal metadata.
    """

    def __init__(self):
        if not VECTOR_DEPS_AVAILABLE:
            raise ImportError("Vector dependencies not available. Install chromadb and sentence-transformers.")

        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chroma_client = chromadb.PersistentClient(path=settings.vector_db_path)

        # Collections for different content types
        self.podcast_collection = self.chroma_client.get_or_create_collection(
            name="podcast_insights",
            metadata={"description": "NFL DFS insights from podcast transcripts"}
        )

        self.news_collection = self.chroma_client.get_or_create_collection(
            name="news_sentiment",
            metadata={"description": "News articles with sentiment analysis"}
        )

    async def store_podcast_transcript(self, podcast_data: Dict[str, Any]) -> str:
        """
        Store podcast transcript with embeddings and metadata.

        Args:
            podcast_data: Dictionary containing:
                - team_name: NFL team name
                - episode_title: Podcast episode title
                - transcript: Full transcript text
                - insights: Extracted DFS insights
                - publish_date: Episode publish date

        Returns:
            Document ID for the stored transcript
        """
        try:
            doc_id = str(uuid.uuid4())

            # Create chunks for better retrieval
            chunks = self._chunk_transcript(podcast_data['transcript'])

            # Extract DFS-relevant insights
            insights = podcast_data.get('insights', [])
            insight_text = " ".join([insight.get('content', '') for insight in insights])

            # Combine transcript and insights for embedding
            full_content = f"{podcast_data['transcript']} {insight_text}"

            # Generate embeddings
            embeddings = self.embedding_model.encode([full_content])

            # Prepare metadata
            metadata = {
                "team_name": podcast_data["team_name"],
                "episode_title": podcast_data["episode_title"],
                "publish_date": podcast_data.get("publish_date", ""),
                "duration": podcast_data.get("duration", ""),
                "insights_count": len(insights),
                "chunk_count": len(chunks),
                "content_type": "podcast_transcript",
                "stored_at": datetime.now(timezone.utc).isoformat()
            }

            # Store in ChromaDB
            self.podcast_collection.add(
                embeddings=embeddings.tolist(),
                documents=[full_content],
                metadatas=[metadata],
                ids=[doc_id]
            )

            logger.info("Podcast transcript stored in vector database",
                       doc_id=doc_id, team=podcast_data["team_name"])

            return doc_id

        except Exception as e:
            logger.error("Error storing podcast transcript", error=str(e))
            raise

    async def search_podcasts(self, query: str, limit: int = 5, team_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Semantic search through podcast transcripts.

        Args:
            query: Search query
            limit: Maximum results to return
            team_filter: Optional team name filter

        Returns:
            List of relevant podcast segments with metadata
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode([query])

            # Build search filter if team specified
            where_clause = None
            if team_filter:
                where_clause = {"team_name": team_filter}

            # Search the collection
            results = self.podcast_collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=limit,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            formatted_results = []
            if results['documents'] and results['metadatas']:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    formatted_results.append({
                        "rank": i + 1,
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "team_name": metadata.get("team_name", ""),
                        "episode_title": metadata.get("episode_title", ""),
                        "publish_date": metadata.get("publish_date", ""),
                        "insights_count": metadata.get("insights_count", 0),
                        "relevance_score": 1 - distance,  # Convert distance to similarity
                        "content_type": "podcast_transcript"
                    })

            logger.info("Podcast search completed",
                       query=query, results_count=len(formatted_results))

            return formatted_results

        except Exception as e:
            logger.error("Error searching podcasts", query=query, error=str(e))
            return []

    async def store_news_article(self, article_data: Dict[str, Any]) -> str:
        """
        Store news article with sentiment analysis and embeddings.
        """
        try:
            doc_id = str(uuid.uuid4())

            # Extract sentiment if available
            sentiment = article_data.get('sentiment', {})
            sentiment_text = f"Sentiment: {sentiment.get('label', 'neutral')}"

            # Combine content and sentiment for embedding
            full_content = f"{article_data['content']} {sentiment_text}"

            # Generate embeddings
            embeddings = self.embedding_model.encode([full_content])

            # Prepare metadata
            metadata = {
                "title": article_data["title"],
                "source": article_data.get("source", ""),
                "publish_date": article_data.get("publish_date", ""),
                "sentiment_label": sentiment.get("label", "neutral"),
                "sentiment_score": sentiment.get("score", 0.0),
                "content_type": "news_article",
                "stored_at": datetime.now(timezone.utc).isoformat()
            }

            # Store in ChromaDB
            self.news_collection.add(
                embeddings=embeddings.tolist(),
                documents=[full_content],
                metadatas=[metadata],
                ids=[doc_id]
            )

            logger.info("News article stored in vector database",
                       doc_id=doc_id, title=article_data["title"])

            return doc_id

        except Exception as e:
            logger.error("Error storing news article", error=str(e))
            raise

    async def search_combined(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search across both podcasts and news for comprehensive insights.
        """
        try:
            # Search both collections
            podcast_results = await self.search_podcasts(query, limit // 2)
            news_results = await self.search_news(query, limit // 2)

            # Combine and sort by relevance
            combined_results = podcast_results + news_results
            combined_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            combined_results = combined_results[:limit]

            return {
                "query": query,
                "total_results": len(combined_results),
                "podcast_results": len(podcast_results),
                "news_results": len(news_results),
                "results": combined_results
            }

        except Exception as e:
            logger.error("Error in combined search", query=query, error=str(e))
            return {"query": query, "results": []}

    async def search_news(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search news articles for relevant content.
        """
        try:
            query_embedding = self.embedding_model.encode([query])

            results = self.news_collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )

            formatted_results = []
            if results['documents'] and results['metadatas']:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    formatted_results.append({
                        "rank": i + 1,
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "title": metadata.get("title", ""),
                        "source": metadata.get("source", ""),
                        "publish_date": metadata.get("publish_date", ""),
                        "sentiment": metadata.get("sentiment_label", "neutral"),
                        "relevance_score": 1 - distance,
                        "content_type": "news_article"
                    })

            return formatted_results

        except Exception as e:
            logger.error("Error searching news", query=query, error=str(e))
            return []

    def _chunk_transcript(self, transcript: str, chunk_size: int = 1000) -> List[str]:
        """
        Split long transcripts into manageable chunks for better retrieval.
        """
        words = transcript.split()
        chunks = []

        for i in range(0, len(words), chunk_size // 10):  # Approximate word-based chunking
            chunk = " ".join(words[i:i + chunk_size // 10])
            if chunk.strip():
                chunks.append(chunk)

        return chunks if chunks else [transcript]

    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database collections.
        """
        try:
            podcast_count = self.podcast_collection.count()
            news_count = self.news_collection.count()

            return {
                "podcast_transcripts": podcast_count,
                "news_articles": news_count,
                "total_documents": podcast_count + news_count,
                "vector_dimensions": self.embedding_model.get_sentence_embedding_dimension()
            }

        except Exception as e:
            logger.error("Error getting collection stats", error=str(e))
            return {"error": str(e)}
