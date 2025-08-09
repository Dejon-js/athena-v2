import asyncio
import json
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.applications import FastAPI
import structlog

logger = structlog.get_logger()


class WebSocketManager:
    """
    Manages WebSocket connections for real-time status updates.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.app = FastAPI()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup WebSocket routes"""
        
        @self.app.websocket("/status")
        async def websocket_status_endpoint(websocket: WebSocket):
            await self.connect(websocket)
            try:
                while True:
                    await websocket.receive_text()
                    await self.send_status_update(websocket)
            except WebSocketDisconnect:
                self.disconnect(websocket)
        
        @self.app.websocket("/thought-stream")
        async def websocket_thought_stream_endpoint(websocket: WebSocket):
            await self.connect(websocket)
            try:
                while True:
                    await websocket.receive_text()
                    await self.send_thought_stream_update(websocket)
            except WebSocketDisconnect:
                self.disconnect(websocket)
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established", 
                   total_connections=len(self.active_connections))
        
        await self.send_initial_status(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket connection closed", 
                   total_connections=len(self.active_connections))
    
    async def send_initial_status(self, websocket: WebSocket):
        """Send initial status when client connects"""
        initial_status = {
            "type": "status_update",
            "data": {
                "overall_status": "operational",
                "active_module": None,
                "modules": {
                    "m1_data_core": {"status": "ready", "progress": 0},
                    "m2_simulation": {"status": "ready", "progress": 0},
                    "m3_game_theory": {"status": "ready", "progress": 0},
                    "m4_optimizer": {"status": "ready", "progress": 0},
                    "m5_live_ops": {"status": "standby", "progress": 0},
                    "m6_learning": {"status": "ready", "progress": 0},
                    "m7_adaptive": {"status": "ready", "progress": 0}
                },
                "timestamp": "2025-08-09T23:04:33Z"
            }
        }
        
        await websocket.send_text(json.dumps(initial_status))
    
    async def send_status_update(self, websocket: WebSocket):
        """Send status update to specific client"""
        status_update = {
            "type": "status_update",
            "data": {
                "overall_status": "operational",
                "active_module": "m1_data_core",
                "modules": {
                    "m1_data_core": {"status": "running", "progress": 75},
                    "m2_simulation": {"status": "ready", "progress": 0},
                    "m3_game_theory": {"status": "ready", "progress": 0},
                    "m4_optimizer": {"status": "ready", "progress": 0},
                    "m5_live_ops": {"status": "standby", "progress": 0},
                    "m6_learning": {"status": "ready", "progress": 0},
                    "m7_adaptive": {"status": "ready", "progress": 0}
                },
                "timestamp": "2025-08-09T23:04:33Z"
            }
        }
        
        await websocket.send_text(json.dumps(status_update))
    
    async def send_thought_stream_update(self, websocket: WebSocket):
        """Send thought stream update to specific client"""
        thought_update = {
            "type": "thought_stream",
            "data": {
                "module": "m1_data_core",
                "message": "Ingesting player stats from Sportradar API...",
                "timestamp": "2025-08-09T23:04:33Z",
                "level": "info"
            }
        }
        
        await websocket.send_text(json.dumps(thought_update))
    
    async def broadcast_status(self, status_data: Dict[str, Any]):
        """Broadcast status update to all connected clients"""
        if not self.active_connections:
            return
        
        message = {
            "type": "status_update",
            "data": status_data
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error("Failed to send WebSocket message", error=str(e))
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_thought_stream(self, module: str, message: str, level: str = "info"):
        """Broadcast thought stream message to all connected clients"""
        if not self.active_connections:
            return
        
        thought_message = {
            "type": "thought_stream",
            "data": {
                "module": module,
                "message": message,
                "timestamp": "2025-08-09T23:04:33Z",
                "level": level
            }
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(thought_message))
            except Exception as e:
                logger.error("Failed to send thought stream message", error=str(e))
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_module_progress(self, module: str, progress: int, status: str = "running"):
        """Broadcast module progress update"""
        progress_data = {
            "active_module": module,
            "modules": {
                module: {
                    "status": status,
                    "progress": progress
                }
            },
            "timestamp": "2025-08-09T23:04:33Z"
        }
        
        await self.broadcast_status(progress_data)
    
    async def broadcast_optimization_progress(self, lineups_generated: int, total_lineups: int):
        """Broadcast optimization progress"""
        progress = int((lineups_generated / total_lineups) * 100)
        
        await self.broadcast_thought_stream(
            "m4_optimizer",
            f"Generated {lineups_generated}/{total_lineups} lineups ({progress}% complete)",
            "info"
        )
        
        await self.broadcast_module_progress("m4_optimizer", progress)
    
    async def broadcast_simulation_progress(self, iterations_completed: int, total_iterations: int):
        """Broadcast simulation progress"""
        progress = int((iterations_completed / total_iterations) * 100)
        
        await self.broadcast_thought_stream(
            "m2_simulation",
            f"Monte Carlo simulation: {iterations_completed:,}/{total_iterations:,} iterations ({progress}% complete)",
            "info"
        )
        
        await self.broadcast_module_progress("m2_simulation", progress)


websocket_manager = WebSocketManager()
