import asyncio
from modules.m1_data_core.data_ingestion import DataIngestionEngine

async def test_rss_feeds():
    async with DataIngestionEngine() as engine:
        result = await engine.ingest_rss_feeds()
        print("RSS Feed Ingestion Result:", result)

if __name__ == "__main__":
    asyncio.run(test_rss_feeds())
