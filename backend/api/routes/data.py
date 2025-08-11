from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import structlog

from shared.database import get_db
from modules.m1_data_core import DataIngestionEngine, DataValidator, DataScheduler

logger = structlog.get_logger()
router = APIRouter()

data_scheduler = DataScheduler()


@router.post("/ingest")
async def trigger_data_ingestion(
    background_tasks: BackgroundTasks,
    data_type: Optional[str] = "all",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger manual data ingestion for specified data type.
    
    Args:
        data_type: Type of data to ingest ('all', 'vegas_odds', 'player_stats', 'news_sentiment', 'dfs_data')
    """
    logger.info("Manual data ingestion triggered", data_type=data_type)
    
    try:
        if not data_scheduler.is_running:
            await data_scheduler.start_scheduler()
        
        result = await data_scheduler.trigger_manual_ingestion(data_type)
        
        return {
            "status": "success",
            "message": f"Data ingestion triggered for {data_type}",
            "result": result
        }
        
    except Exception as e:
        logger.error("Failed to trigger data ingestion", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger data ingestion: {str(e)}")


@router.get("/validation")
async def get_validation_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get current data validation status and consistency metrics.
    """
    logger.info("Data validation status requested")
    
    try:
        validator = DataValidator()
        validation_result = await validator.validate_all_data()
        
        return {
            "status": "success",
            "validation_result": validation_result
        }
        
    except Exception as e:
        logger.error("Failed to get validation status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get validation status: {str(e)}")


@router.post("/validation/run")
async def run_validation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually trigger data validation cycle.
    """
    logger.info("Manual data validation triggered")
    
    try:
        validator = DataValidator()
        
        def run_validation_task():
            import asyncio
            return asyncio.run(validator.validate_all_data())
        
        background_tasks.add_task(run_validation_task)
        
        return {
            "status": "success",
            "message": "Data validation started in background"
        }
        
    except Exception as e:
        logger.error("Failed to trigger validation", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger validation: {str(e)}")


@router.get("/scheduler/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """
    Get current data scheduler status and job information.
    """
    try:
        status = await data_scheduler.get_scheduler_status()
        
        return {
            "status": "success",
            "scheduler": status
        }
        
    except Exception as e:
        logger.error("Failed to get scheduler status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/scheduler/start")
async def start_scheduler() -> Dict[str, Any]:
    """
    Start the data scheduling system.
    """
    logger.info("Starting data scheduler")
    
    try:
        if data_scheduler.is_running:
            return {
                "status": "success",
                "message": "Scheduler is already running"
            }
        
        await data_scheduler.start_scheduler()
        
        return {
            "status": "success",
            "message": "Data scheduler started successfully"
        }
        
    except Exception as e:
        logger.error("Failed to start scheduler", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/scheduler/stop")
async def stop_scheduler() -> Dict[str, Any]:
    """
    Stop the data scheduling system.
    """
    logger.info("Stopping data scheduler")
    
    try:
        if not data_scheduler.is_running:
            return {
                "status": "success",
                "message": "Scheduler is already stopped"
            }
        
        await data_scheduler.stop_scheduler()
        
        return {
            "status": "success",
            "message": "Data scheduler stopped successfully"
        }
        
    except Exception as e:
        logger.error("Failed to stop scheduler", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@router.get("/sources/status")
async def get_data_sources_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get status of all data sources and their last update times.
    """
    try:
        async with DataIngestionEngine() as engine:
            status = {
                "sportradar": {
                    "configured": bool(engine.data_processor),
                    "last_update": None,
                    "status": "unknown"
                },
                "vegas_odds": {
                    "draftkings": {"configured": True, "last_update": None},
                    "fanduel": {"configured": True, "last_update": None},
                    "betmgm": {"configured": True, "last_update": None}
                },
                "news_sources": {
                    "news_api": {"configured": True, "last_update": None},
                    "twitter": {"configured": True, "last_update": None}
                },
                "dfs_platforms": {
                    "draftkings": {"configured": True, "last_update": None}
                }
            }
        
        return {
            "status": "success",
            "data_sources": status
        }
        
    except Exception as e:
        logger.error("Failed to get data sources status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get data sources status: {str(e)}")
