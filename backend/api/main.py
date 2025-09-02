from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog

from shared.config import settings
from shared.database import init_database, close_connections
from api.routes import data, projections, optimization, status, chat, health
from api.websockets import websocket_manager

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ATHENA v2.2 backend")
    
    try:
        init_database()
        logger.info("Database initialized successfully")
        yield
    finally:
        logger.info("Shutting down ATHENA v2.2 backend")
        close_connections()


app = FastAPI(
    title="ATHENA v2.2 - NFL DFS Optimizer",
    description="Autonomous NFL Daily Fantasy Sports optimizer with 7-module architecture",
    version="2.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router, prefix="/api/v1/data", tags=["data"])
app.include_router(projections.router, prefix="/api/v1/projections", tags=["projections"])
app.include_router(optimization.router, prefix="/api/v1/optimize", tags=["optimization"])
app.include_router(status.router, prefix="/api/v1/status", tags=["status"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])

app.mount("/ws", websocket_manager.app)


@app.get("/")
async def root():
    return {
        "message": "ATHENA v2.2 - NFL DFS Optimizer API",
        "version": "2.2.0",
        "status": "operational",
        "modules": [
            "M1: Data Core",
            "M2: Simulation & Projection Engine", 
            "M3: Game Theory & Ownership Engine",
            "M4: The Optimizer Engine",
            "M5: Live Operations & Suggestion Engine",
            "M6: Learning & Feedback Loop",
            "M7: Early-Season Adaptive Logic"
        ]
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error("HTTP exception occurred", 
                status_code=exc.status_code, 
                detail=exc.detail,
                path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error("Unexpected exception occurred", 
                error=str(exc),
                path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
