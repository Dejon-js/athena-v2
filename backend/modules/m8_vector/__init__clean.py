# ATHENA v2.2 - Vector Database Module
# Clean imports to avoid encoding issues

try:
    from .vector_database import VectorDatabaseManager, VECTOR_DEPS_AVAILABLE as VDB_AVAILABLE
    from .temporal_processor import TemporalVectorProcessor
    from .content_processor import ContentVectorProcessor, SENTENCE_TRANSFORMERS_AVAILABLE
    VECTOR_DEPS_AVAILABLE = VDB_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE
except ImportError as e:
    print(f'Vector dependencies not available: {e}')
    VectorDatabaseManager = None
    TemporalVectorProcessor = None
    ContentVectorProcessor = None
    VECTOR_DEPS_AVAILABLE = False

__all__ = [
    'VectorDatabaseManager',
    'TemporalVectorProcessor', 
    'ContentVectorProcessor',
    'VectorIntegrationService',
    'VECTOR_DEPS_AVAILABLE'
]


class VectorIntegrationService:
    def __init__(self):
        if not VECTOR_DEPS_AVAILABLE:
            raise ImportError('Vector dependencies not available')
        
        self.vector_db = VectorDatabaseManager()
        self.content_processor = ContentVectorProcessor()
        self.temporal_processor = TemporalVectorProcessor()

    async def initialize(self):
        pass

    async def process_and_store_podcast(self, podcast_data):
        if not VECTOR_DEPS_AVAILABLE:
            return None
        processed_data = await self.content_processor.process_podcast_transcript(podcast_data)
        doc_id = await self.vector_db.store_podcast_transcript(processed_data)
        return doc_id

    async def process_and_store_news(self, news_data):
        if not VECTOR_DEPS_AVAILABLE:
            return None
        processed_data = await self.content_processor.process_news_article(news_data)
        doc_id = await self.vector_db.store_news_article(processed_data)
        return doc_id

    async def search_fantasy_insights(self, query, limit=5):
        if not VECTOR_DEPS_AVAILABLE:
            return {
                'query': query,
                'total_results': 0,
                'results': [],
                'freshness_distribution': {},
                'search_timestamp': 0
            }
        
        search_results = await self.vector_db.search_combined(query, limit)
        temporal_results = await self.temporal_processor.apply_temporal_scoring(search_results)
        filtered_results = await self.temporal_processor.filter_by_freshness(temporal_results)
        
        return {
            'query': query,
            'total_results': len(filtered_results),
            'results': filtered_results,
            'freshness_distribution': {},
            'search_timestamp': 0
        }

    async def get_collection_stats(self):
        if not VECTOR_DEPS_AVAILABLE:
            return {'error': 'Vector dependencies not available'}
        return await self.vector_db.get_collection_stats()
