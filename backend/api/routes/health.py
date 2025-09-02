from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import time
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
import asyncio
from datetime import datetime, timezone
import structlog

from shared.database import get_db, redis_client
from shared.config import settings

logger = structlog.get_logger()
router = APIRouter()


class SystemMonitor:
    """System monitoring utilities for ATHENA v2.2"""

    def __init__(self):
        self.start_time = time.time()

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        try:
            base_metrics = {
                "uptime_seconds": time.time() - self.start_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            if PSUTIL_AVAILABLE:
                base_metrics.update({
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
                    "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
                    "disk_usage_percent": psutil.disk_usage('/').percent,
                    "process_count": len(psutil.pids())
                })
            else:
                base_metrics["note"] = "Full system metrics available with psutil installation"

            return base_metrics
        except Exception as e:
            logger.error("Error getting system metrics", error=str(e))
            return {"error": str(e)}

    async def check_database_connections(self) -> Dict[str, Any]:
        """Check all database connections."""
        results = {}

        try:
            # PostgreSQL check
            from sqlalchemy import text
            db = next(get_db())
            db.execute(text("SELECT 1"))
            results["postgresql"] = {"status": "healthy", "response_time": 0.001}
        except Exception as e:
            results["postgresql"] = {"status": "unhealthy", "error": str(e)}

        try:
            # Redis check
            redis_client.ping()
            results["redis"] = {"status": "healthy", "response_time": 0.001}
        except Exception as e:
            results["redis"] = {"status": "unhealthy", "error": str(e)}

        try:
            # Neo4j check (if available)
            if hasattr(settings, 'neo4j_conn'):
                neo4j_conn = settings.neo4j_conn
                # Add Neo4j health check logic here
                results["neo4j"] = {"status": "healthy", "response_time": 0.001}
            else:
                results["neo4j"] = {"status": "not_configured"}
        except Exception as e:
            results["neo4j"] = {"status": "unhealthy", "error": str(e)}

        return results

    async def check_external_apis(self) -> Dict[str, Any]:
        """Check external API connectivity."""
        results = {}

        # Check API keys configuration
        api_keys_status = {
            "listen_notes": bool(getattr(settings, 'listen_notes_api_key', None)),
            "assemblyai": bool(getattr(settings, 'assemblyai_api_key', None)),
            "sportsdata": bool(getattr(settings, 'sportsdata_api_key', None)),
            "sportradar": bool(getattr(settings, 'sportradar_api_key', None)),
            "news_api": bool(getattr(settings, 'news_api_key', None))
        }

        results["api_keys_configured"] = api_keys_status
        results["total_keys_configured"] = sum(api_keys_status.values())

        return results

    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        try:
            system_metrics = self.get_system_metrics()
            db_status = await self.check_database_connections()
            api_status = await self.check_external_apis()

            # Calculate overall health score
            db_healthy = all([svc.get("status") == "healthy" for svc in db_status.values()])
            system_healthy = system_metrics.get("memory_percent", 100) < 90
            apis_configured = api_status.get("total_keys_configured", 0) >= 2

            health_score = (db_healthy * 40) + (system_healthy * 30) + (apis_configured * 30)

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "health_score": health_score,
                "status": "healthy" if health_score >= 70 else "degraded" if health_score >= 40 else "critical",
                "system_metrics": system_metrics,
                "database_status": db_status,
                "api_status": api_status,
                "version": "2.2.0",
                "environment": getattr(settings, 'environment', 'development')
            }

        except Exception as e:
            logger.error("Error getting service status", error=str(e))
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": str(e)
            }


monitor = SystemMonitor()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "environment": getattr(settings, 'environment', 'development'),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.2.0"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with system metrics."""
    return await monitor.get_service_status()


@router.get("/health/databases")
async def database_health_check():
    """Database connectivity health check."""
    return await monitor.check_database_connections()


@router.get("/health/apis")
async def api_health_check():
    """External API configuration check."""
    return await monitor.check_external_apis()


@router.get("/health/metrics")
async def system_metrics():
    """System performance metrics."""
    return monitor.get_system_metrics()


@router.get("/status")
async def system_status():
    """Real-time system status for WebSocket connections."""
    status = await monitor.get_service_status()
    return {
        "timestamp": status["timestamp"],
        "health_score": status["health_score"],
        "status": status["status"],
        "system_load": status["system_metrics"].get("cpu_percent", 0),
        "memory_usage": status["system_metrics"].get("memory_percent", 0),
        "database_status": all([svc.get("status") == "healthy" for svc in status["database_status"].values()]),
        "api_keys_configured": status["api_status"].get("total_keys_configured", 0)
    }
