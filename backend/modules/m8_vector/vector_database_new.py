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
    def __init__(self):
        if not VECTOR_DEPS_AVAILABLE:
            raise ImportError("Vector dependencies not available. Install chromadb and sentence-transformers.")

        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chroma_client = chromadb.PersistentClient(path=settings.vector_db_path)
        self.podcast_collection = self.chroma_client.get_or_create_collection(
            name="podcast_insights",
            metadata={"description": "NFL DFS insights from podcast transcripts"}
        )
        self.news_collection = self.chroma_client.get_or_create_collection(
            name="news_sentiment",
            metadata={"description": "News articles with sentiment analysis"}
        )

    async def store_podcast_transcript(self, podcast_data: Dict[str, Any]) -> str:
        """Store podcast transcript in vector database."""
        try:
            doc_id = str(uuid.uuid4())

            # Prepare document content
            content = f"{podcast_data.get('team_name', '')} {podcast_data.get('episode_title', '')} {podcast_data.get('transcript', '')}"

            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()

            # Prepare metadata
            metadata = {
                "team_name": podcast_data.get("team_name", ""),
                "episode_title": podcast_data.get("episode_title", ""),
                "publish_date": podcast_data.get("publish_date", ""),
                "duration": str(podcast_data.get("duration", "")),
                "podcast_id": podcast_data.get("podcast_id", ""),
                "episode_id": podcast_data.get("episode_id", ""),
                "content_type": "podcast",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Store in ChromaDB
            self.podcast_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[content]
            )

            logger.info("Podcast transcript stored in vector database", doc_id=doc_id)
            return doc_id

        except Exception as e:
            logger.error("Error storing podcast transcript", error=str(e))
            raise

    async def search_podcasts(self, query: str, limit: int = 5, team_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search podcast transcripts."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Prepare search filter
            where_clause = {"content_type": "podcast"}
            if team_filter:
                where_clause["team_name"] = team_filter

            # Search
            results = self.podcast_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause
            )

            # Format results
            formatted_results = []
            for i, doc_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    "doc_id": doc_id,
                    "content": results['documents'][0][i][:500] + "..." if len(results['documents'][0][i]) > 500 else results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "similarity_score": 1.0 - (results['distances'][0][i] if 'distances' in results else 0.0)
                })

            logger.info("Podcast search completed", query=query, results_count=len(formatted_results))
            return formatted_results

        except Exception as e:
            logger.error("Error searching podcasts", query=query, error=str(e))
            return []

    async def store_news_article(self, article_data: Dict[str, Any]) -> str:
        """Store news article in vector database."""
        try:
            doc_id = str(uuid.uuid4())

            # Prepare document content
            content = f"{article_data.get('title', '')} {article_data.get('content', '')}"

            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()

            # Prepare metadata
            metadata = {
                "title": article_data.get("title", ""),
                "source": article_data.get("source", ""),
                "publish_date": article_data.get("publish_date", ""),
                "sentiment_score": str(article_data.get("sentiment_score", "")),
                "content_type": "news",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Store in ChromaDB
            self.news_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[content]
            )

            logger.info("News article stored in vector database", doc_id=doc_id)
            return doc_id

        except Exception as e:
            logger.error("Error storing news article", error=str(e))
            raise

    async def search_news(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search news articles."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Search
            results = self.news_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where={"content_type": "news"}
            )

            # Format results
            formatted_results = []
            for i, doc_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    "doc_id": doc_id,
                    "content": results['documents'][0][i][:500] + "..." if len(results['documents'][0][i]) > 500 else results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "similarity_score": 1.0 - (results['distances'][0][i] if 'distances' in results else 0.0)
                })

            logger.info("News search completed", query=query, results_count=len(formatted_results))
            return formatted_results

        except Exception as e:
            logger.error("Error searching news", query=query, error=str(e))
            return []

    async def search_combined(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search both podcasts and news."""
        try:
            podcast_results = await self.search_podcasts(query, limit=limit//2)
            news_results = await self.search_news(query, limit=limit//2)

            return {
                "query": query,
                "total_results": len(podcast_results) + len(news_results),
                "podcast_results": podcast_results,
                "news_results": news_results,
                "search_timestamp": datetime.now(timezone.utc).timestamp()
            }

        except Exception as e:
            logger.error("Error in combined search", query=query, error=str(e))
            return {
                "query": query,
                "total_results": 0,
                "podcast_results": [],
                "news_results": [],
                "search_timestamp": datetime.now(timezone.utc).timestamp(),
                "error": str(e)
            }

    def _chunk_transcript(self, transcript: str, chunk_size: int = 1000) -> List[str]:
        """Chunk transcript into smaller pieces for better search."""
        words = transcript.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about vector collections."""
        try:
            podcast_count = self.podcast_collection.count()
            news_count = self.news_collection.count()

            return {
                "podcast_collection": {
                    "document_count": podcast_count,
                    "name": "podcast_insights"
                },
                "news_collection": {
                    "document_count": news_count,
                    "name": "news_sentiment"
                },
                "total_documents": podcast_count + news_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error("Error getting collection stats", error=str(e))
            return {"error": str(e)}
