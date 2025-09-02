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
            raise ImportError('Vector dependencies not available. Install chromadb and sentence-transformers.')

        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chroma_client = chromadb.PersistentClient(path=settings.vector_db_path)
        self.podcast_collection = self.chroma_client.get_or_create_collection(
            name='podcast_insights',
            metadata={'description': 'NFL DFS insights from podcast transcripts'}
        )
        self.news_collection = self.chroma_client.get_or_create_collection(
            name='news_sentiment',
            metadata={'description': 'News articles with sentiment analysis'}
        )

    async def store_podcast_transcript(self, podcast_data: Dict[str, Any]) -> str:
        doc_id = str(uuid.uuid4())
        team_name = podcast_data.get('team_name', '')
        episode_title = podcast_data.get('episode_title', '')
        transcript = podcast_data.get('transcript', '')
        content = f'{team_name} {episode_title} {transcript}'
        embedding = self.embedding_model.encode(content).tolist()
        
        metadata = {
            'team_name': podcast_data.get('team_name', ''),
            'episode_title': podcast_data.get('episode_title', ''),
            'publish_date': podcast_data.get('publish_date', ''),
            'duration': str(podcast_data.get('duration', '')),
            'podcast_id': podcast_data.get('podcast_id', ''),
            'episode_id': podcast_data.get('episode_id', ''),
            'content_type': 'podcast',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        self.podcast_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[content]
        )

        logger.info('Podcast transcript stored in vector database', doc_id=doc_id)
        return doc_id

    async def search_podcasts(self, query: str, limit: int = 5, team_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_model.encode(query).tolist()
        
        where_clause = {'content_type': 'podcast'}
        if team_filter:
            where_clause['team_name'] = team_filter

        results = self.podcast_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_clause
        )

        formatted_results = []
        for i, doc_id in enumerate(results['ids'][0]):
            content = results['documents'][0][i]
            preview = content[:500] + '...' if len(content) > 500 else content
            formatted_results.append({
                'doc_id': doc_id,
                'content': preview,
                'metadata': results['metadatas'][0][i],
                'similarity_score': 1.0 - (results['distances'][0][i] if 'distances' in results else 0.0)
            })

        logger.info('Podcast search completed', query=query, results_count=len(formatted_results))
        return formatted_results

    async def get_collection_stats(self) -> Dict[str, Any]:
        try:
            podcast_count = self.podcast_collection.count()
            news_count = self.news_collection.count()

            return {
                'podcast_collection': {
                    'document_count': podcast_count,
                    'name': 'podcast_insights'
                },
                'news_collection': {
                    'document_count': news_count,
                    'name': 'news_sentiment'
                },
                'total_documents': podcast_count + news_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error('Error getting collection stats', error=str(e))
            return {'error': str(e)}
