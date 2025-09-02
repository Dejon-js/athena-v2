import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import structlog

from modules.m1_data_core.data_ingestion import DataIngestionEngine
from modules.m1_data_core.data_validation import DataValidator
from shared.config import settings
from shared.database import redis_client

logger = structlog.get_logger()


class DataScheduler:
    """
    Orchestrates scheduled data pipelines using APScheduler.
    Manages data ingestion frequency and validation cycles.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.data_engine = DataIngestionEngine()
        self.data_validator = DataValidator()
        self.is_running = False
        
        # NFL Season Scheduling Strategy - Optimized for real-time DFS
        # Strategy adapts based on season phase and game schedule
        self.schedule_config = self._get_season_optimized_schedule()
    
    def _get_season_optimized_schedule(self) -> Dict[str, Dict[str, int]]:
        """
        Get season-optimized scheduling configuration based on NFL calendar.

        Returns different frequencies based on:
        - Pre-season (low frequency)
        - Regular season (high frequency)
        - Playoffs (very high frequency)
        - Off-season (maintenance mode)
        """
        from datetime import datetime

        current_date = datetime.now()
        current_month = current_date.month
        current_day = current_date.day

        # NFL Season Phases
        if current_month in [1, 2, 3, 4, 5, 6, 7]:  # Off-season
            return self._get_off_season_schedule()
        elif current_month == 8:  # Pre-season
            return self._get_pre_season_schedule()
        elif current_month in [9, 10, 11, 12]:  # Regular season
            return self._get_regular_season_schedule()
        else:  # Default to regular season
            return self._get_regular_season_schedule()

    def _get_regular_season_schedule(self) -> Dict[str, Dict[str, int]]:
        """High-frequency schedule for regular season (Sept-Dec)"""
        return {
            # CRITICAL - Game day updates (every few minutes)
            'injury_status': {'minutes': 3},   # Injuries change game outcomes
            'vegas_odds': {'minutes': 10},     # Lines move rapidly during games

            # HIGH FREQUENCY - Real-time DFS (15-30 min)
            'news_sentiment': {'minutes': 15}, # Breaking news affects lineups
            'rss_feeds': {'minutes': 20},      # NFL news and injury reports

            # MEDIUM FREQUENCY - DFS data (1-3 hours)
            'dfs_data': {'hours': 1},          # Slate updates and ownership
            'player_stats': {'hours': 2},      # Game stats and projections

            # MEDIUM FREQUENCY - Podcasts (4-6 hours)
            'podcast_data': {'hours': 4},      # New episodes during season

            # LOW FREQUENCY - Maintenance
            'validation_cycle': {'hours': 1},  # Data quality checks
            'full_ingestion': {'hours': 12}    # Complete system refresh
        }

    def _get_pre_season_schedule(self) -> Dict[str, Dict[str, int]]:
        """Medium-frequency schedule for pre-season (Aug)"""
        return {
            'injury_status': {'minutes': 15},
            'vegas_odds': {'minutes': 30},
            'news_sentiment': {'minutes': 45},
            'rss_feeds': {'minutes': 60},
            'dfs_data': {'hours': 3},
            'player_stats': {'hours': 6},
            'podcast_data': {'hours': 8},
            'validation_cycle': {'hours': 2},
            'full_ingestion': {'hours': 24}
        }

    def _get_off_season_schedule(self) -> Dict[str, Dict[str, int]]:
        """Low-frequency schedule for off-season (Jan-Jul)"""
        return {
            'injury_status': {'hours': 6},
            'vegas_odds': {'hours': 12},
            'news_sentiment': {'hours': 4},
            'rss_feeds': {'hours': 6},
            'dfs_data': {'hours': 24},         # No active DFS during off-season
            'player_stats': {'hours': 24},
            'podcast_data': {'hours': 12},
            'validation_cycle': {'hours': 6},
            'full_ingestion': {'hours': 48}    # Weekly refresh during off-season
        }

    async def start_scheduler(self):
        """Start the data scheduling system"""
        logger.info("Starting data scheduler")
        
        try:
            await self._setup_scheduled_jobs()
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Data scheduler started successfully")
            
            await self._store_scheduler_status('running')
            
        except Exception as e:
            logger.error("Failed to start data scheduler", error=str(e))
            await self._store_scheduler_status('error', str(e))
            raise
    
    async def stop_scheduler(self):
        """Stop the data scheduling system"""
        logger.info("Stopping data scheduler")
        
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            
            if self.data_engine:
                await self.data_engine.__aexit__(None, None, None)
            
            self.is_running = False
            await self._store_scheduler_status('stopped')
            
            logger.info("Data scheduler stopped successfully")
            
        except Exception as e:
            logger.error("Error stopping data scheduler", error=str(e))
            await self._store_scheduler_status('error', str(e))
    
    async def _setup_scheduled_jobs(self):
        """Setup all scheduled data ingestion jobs"""
        logger.info("Setting up scheduled jobs")
        
        self.scheduler.add_job(
            self._ingest_vegas_odds,
            IntervalTrigger(**self.schedule_config['vegas_odds']),
            id='vegas_odds_ingestion',
            name='Vegas Odds Ingestion',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._ingest_injury_status,
            IntervalTrigger(**self.schedule_config['injury_status']),
            id='injury_status_ingestion',
            name='Injury Status Ingestion',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._ingest_player_stats,
            IntervalTrigger(**self.schedule_config['player_stats']),
            id='player_stats_ingestion',
            name='Player Stats Ingestion',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._ingest_news_sentiment,
            IntervalTrigger(**self.schedule_config['news_sentiment']),
            id='news_sentiment_ingestion',
            name='News Sentiment Ingestion',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._ingest_dfs_data,
            IntervalTrigger(**self.schedule_config['dfs_data']),
            id='dfs_data_ingestion',
            name='DFS Data Ingestion',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._ingest_rss_feeds,
            IntervalTrigger(minutes=5),
            id='rss_feed_ingestion',
            name='RSS Feed Data Ingestion',
            max_instances=1,
            coalesce=True
        )

        self.scheduler.add_job(
            self._ingest_podcast_data,
            IntervalTrigger(**self.schedule_config['podcast_data']),
            id='podcast_data_ingestion',
            name='Podcast Data Ingestion',
            max_instances=1,
            coalesce=True
        )

        self.scheduler.add_job(
            self._run_validation_cycle,
            IntervalTrigger(**self.schedule_config['validation_cycle']),
            id='validation_cycle',
            name='Data Validation Cycle',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._run_full_ingestion,
            IntervalTrigger(**self.schedule_config['full_ingestion']),
            id='full_ingestion_cycle',
            name='Full Data Ingestion Cycle',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._cleanup_old_data,
            CronTrigger(hour=2, minute=0),  # Daily at 2 AM
            id='data_cleanup',
            name='Data Cleanup',
            max_instances=1
        )
        
        logger.info("Scheduled jobs setup completed", job_count=len(self.scheduler.get_jobs()))
    
    async def _ingest_vegas_odds(self):
        """Scheduled Vegas odds ingestion"""
        logger.info("Running scheduled Vegas odds ingestion")
        
        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_vegas_odds()
                await self._log_job_result('vegas_odds', result)
                
        except Exception as e:
            logger.error("Error in scheduled Vegas odds ingestion", error=str(e))
            await self._log_job_result('vegas_odds', {'status': 'error', 'error': str(e)})
    
    async def _ingest_injury_status(self):
        """Scheduled injury status ingestion"""
        logger.info("Running scheduled injury status ingestion")
        
        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_news_sentiment()
                await self._log_job_result('injury_status', result)
                
        except Exception as e:
            logger.error("Error in scheduled injury status ingestion", error=str(e))
            await self._log_job_result('injury_status', {'status': 'error', 'error': str(e)})
    
    async def _ingest_player_stats(self):
        """Scheduled player stats ingestion"""
        logger.info("Running scheduled player stats ingestion")
        
        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_player_stats()
                await self._log_job_result('player_stats', result)
                
        except Exception as e:
            logger.error("Error in scheduled player stats ingestion", error=str(e))
            await self._log_job_result('player_stats', {'status': 'error', 'error': str(e)})
    
    async def _ingest_news_sentiment(self):
        """Scheduled news sentiment ingestion"""
        logger.info("Running scheduled news sentiment ingestion")
        
        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_news_sentiment()
                await self._log_job_result('news_sentiment', result)
                
        except Exception as e:
            logger.error("Error in scheduled news sentiment ingestion", error=str(e))
            await self._log_job_result('news_sentiment', {'status': 'error', 'error': str(e)})
    
    async def _ingest_dfs_data(self):
        """Scheduled DFS data ingestion"""
        logger.info("Running scheduled DFS data ingestion")
        
        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_dfs_data()
                await self._log_job_result('dfs_data', result)
                
        except Exception as e:
            logger.error("Error in scheduled DFS data ingestion", error=str(e))
            await self._log_job_result('dfs_data', {'status': 'error', 'error': str(e)})
    
    async def _ingest_rss_feeds(self):
        """Scheduled RSS feed ingestion"""
        logger.info("Running scheduled RSS feed ingestion")

        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_rss_feeds()
                await self._log_job_result('rss_feeds', result)

        except Exception as e:
            logger.error("Error in scheduled RSS feed ingestion", error=str(e))
            await self._log_job_result('rss_feeds', {'status': 'error', 'error': str(e)})

    async def _ingest_podcast_data(self):
        """Scheduled podcast data ingestion"""
        logger.info("Running scheduled podcast data ingestion")

        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_podcast_data()
                await self._log_job_result('podcast_data', result)

        except Exception as e:
            logger.error("Error in scheduled podcast data ingestion", error=str(e))
            await self._log_job_result('podcast_data', {'status': 'error', 'error': str(e)})

    async def _run_validation_cycle(self):
        """Scheduled data validation cycle"""
        logger.info("Running scheduled data validation cycle")
        
        try:
            result = await self.data_validator.validate_all_data()
            await self._log_job_result('validation', result)
            
            if result.get('overall_consistency', 0) < 0.95:
                logger.warning("Data consistency below 95% threshold", 
                             consistency=result.get('overall_consistency'))
                await self._alert_low_consistency(result)
                
        except Exception as e:
            logger.error("Error in scheduled validation cycle", error=str(e))
            await self._log_job_result('validation', {'status': 'error', 'error': str(e)})
    
    async def _run_full_ingestion(self):
        """Scheduled full data ingestion cycle"""
        logger.info("Running scheduled full data ingestion cycle")
        
        try:
            async with self.data_engine:
                result = await self.data_engine.ingest_all_data()
                await self._log_job_result('full_ingestion', result)
                
        except Exception as e:
            logger.error("Error in scheduled full ingestion cycle", error=str(e))
            await self._log_job_result('full_ingestion', {'status': 'error', 'error': str(e)})
    
    async def _cleanup_old_data(self):
        """Cleanup old cached data and logs"""
        logger.info("Running scheduled data cleanup")
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            
            cleanup_patterns = [
                'job_result:*',
                'conflict:*',
                'player:*',
                'validation:*'
            ]
            
            cleaned_count = 0
            for pattern in cleanup_patterns:
                keys = redis_client.keys(pattern)
                for key in keys:
                    try:
                        key_data = redis_client.get(key)
                        if key_data and 'timestamp' in str(key_data):
                            redis_client.delete(key)
                            cleaned_count += 1
                    except Exception:
                        continue
            
            logger.info("Data cleanup completed", cleaned_keys=cleaned_count)
            await self._log_job_result('cleanup', {'status': 'success', 'cleaned_keys': cleaned_count})
            
        except Exception as e:
            logger.error("Error in scheduled data cleanup", error=str(e))
            await self._log_job_result('cleanup', {'status': 'error', 'error': str(e)})
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and job information"""
        if not self.is_running:
            return {'status': 'stopped', 'jobs': []}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            jobs.append(job_info)
        
        return {
            'status': 'running',
            'jobs': jobs,
            'job_count': len(jobs)
        }
    
    async def trigger_manual_ingestion(self, data_type: str) -> Dict[str, Any]:
        """Manually trigger specific data ingestion"""
        logger.info("Triggering manual data ingestion", data_type=data_type)
        
        try:
            async with self.data_engine:
                if data_type == 'vegas_odds':
                    result = await self.data_engine.ingest_vegas_odds()
                elif data_type == 'player_stats':
                    result = await self.data_engine.ingest_player_stats()
                elif data_type == 'news_sentiment':
                    result = await self.data_engine.ingest_news_sentiment()
                elif data_type == 'dfs_data':
                    result = await self.data_engine.ingest_dfs_data()
                elif data_type == 'rss_feeds':
                    result = await self.data_engine.ingest_rss_feeds()
                elif data_type == 'podcast_data':
                    result = await self.data_engine.ingest_podcast_data()
                elif data_type == 'all':
                    result = await self.data_engine.ingest_all_data()
                else:
                    return {'status': 'error', 'error': f'Unknown data type: {data_type}'}
                
                await self._log_job_result(f'manual_{data_type}', result)
                return result
                
        except Exception as e:
            logger.error("Error in manual data ingestion", data_type=data_type, error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def _log_job_result(self, job_type: str, result: Dict[str, Any]):
        """Log job execution result to Redis"""
        cache_key = f"job_result:{job_type}:{datetime.now(timezone.utc).isoformat()}"
        redis_client.setex(cache_key, 86400, str(result))  # 24 hour cache
    
    async def _store_scheduler_status(self, status: str, error: Optional[str] = None):
        """Store scheduler status in Redis"""
        status_data = {
            'status': status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error
        }
        redis_client.setex('scheduler:status', 3600, str(status_data))  # 1 hour cache
    
    async def _alert_low_consistency(self, validation_result: Dict[str, Any]):
        """Alert when data consistency falls below threshold"""
        alert_data = {
            'type': 'low_consistency',
            'consistency': validation_result.get('overall_consistency'),
            'threshold': 0.95,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': validation_result
        }
        
        cache_key = f"alert:consistency:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        redis_client.setex(cache_key, 86400, str(alert_data))  # 24 hour cache
        
        logger.critical("Data consistency alert triggered", alert=alert_data)
