import asyncio
import json
from sqlalchemy.orm import Session
import structlog

# Adjust the imports to be absolute from the project root
from modules.m1_data_core.data_ingestion import DataIngestionEngine
from shared.database import get_db, redis_client
from models.players import Player
from models.games import Game
from models.news import NewsArticle

logger = structlog.get_logger()

async def verify_pipeline():
    """
    An end-to-end test to verify the data ingestion and storage pipeline.
    1. Ingests all data.
    2. Connects to PostgreSQL and Redis.
    3. Verifies that the ingested data exists in the databases.
    """
    logger.info("Starting end-to-end pipeline verification...")

    # --- Step 1: Ingest Data ---
    ingestion_summary = {}
    async with DataIngestionEngine() as engine:
        # We focus on data sources that have concrete storage implementations
        tasks = {
            'player_stats': engine.ingest_player_stats(),
            'rss_feeds': engine.ingest_rss_feeds(),
            'dfs_data': engine.ingest_dfs_data(),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        ingestion_summary = dict(zip(tasks.keys(), results))

    logger.info("Data ingestion phase complete.", summary=ingestion_summary)

    # --- Step 2: Verify Storage ---
    verification_results = {
        "redis": {"found_keys": 0, "total_keys_expected": 0},
        "postgres": {"players": 0, "games": 0, "news_articles": 0}
    }

    # Verify Redis Storage (Player data, RSS articles, etc.)
    logger.info("Verifying Redis storage...")
    try:
        player_keys = redis_client.keys("player:*")
        rss_keys = redis_client.keys("rss_article:*")
        dfs_player_keys = redis_client.keys("dfs_player:*")
        
        verification_results["redis"]["found_keys"] = len(player_keys) + len(rss_keys) + len(dfs_player_keys)
        
        ingested_players = ingestion_summary.get('player_stats', {}).get('players_count', 0)
        ingested_articles = ingestion_summary.get('rss_feeds', {}).get('total_articles', 0)
        ingested_dfs_players = ingestion_summary.get('dfs_data', {}).get('players_count', 0)
        verification_results["redis"]["total_keys_expected"] = ingested_players + ingested_articles + ingested_dfs_players

        logger.info("Redis verification complete.", 
                    found_player_keys=len(player_keys),
                    found_rss_keys=len(rss_keys),
                    found_dfs_keys=len(dfs_player_keys))
    except Exception as e:
        logger.error("Failed to verify Redis storage", error=str(e))

    # Verify PostgreSQL Storage
    logger.info("Verifying PostgreSQL storage...")
    db: Session = next(get_db())
    try:
        player_count = db.query(Player).count()
        game_count = db.query(Game).count()
        news_count = db.query(NewsArticle).count()
        
        verification_results["postgres"]["players"] = player_count
        verification_results["postgres"]["games"] = game_count
        verification_results["postgres"]["news_articles"] = news_count
        logger.info("PostgreSQL verification complete.", 
                    players=player_count, games=game_count, news_articles=news_count)
    except Exception as e:
        logger.error("Failed to verify PostgreSQL storage", error=str(e))
    finally:
        db.close()

    # --- Step 3: Report Results ---
    print("\n--- Pipeline Verification Report ---")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")

    print("--- Ingestion Summary ---")
    print(json.dumps(ingestion_summary, indent=2, default=str))
    print("\n--- Storage Verification ---")
    print(json.dumps(verification_results, indent=2, default=str))
    
    redis_ok = verification_results["redis"]["found_keys"] > 0 and verification_results["redis"]["found_keys"] >= verification_results["redis"]["total_keys_expected"]
    postgres_ok = verification_results["postgres"]["players"] > 0

    print("\n--- Verdict ---")
    if redis_ok and postgres_ok:
        print("✅  Success: Data appears to be flowing correctly into Redis and PostgreSQL.")
    else:
        print("❌ Failure: Discrepancies found between ingested data and stored data.")
        if not redis_ok:
            print("  - Redis check failed. Expected keys were not found.")
        if not postgres_ok:
            print("  - PostgreSQL check failed. Expected records were not found.")
    print("------------------------------------")


if __name__ == "__main__":
    from datetime import datetime, timezone
    asyncio.run(verify_pipeline())
