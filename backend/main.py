"""Open Jam — Main application entry point."""

import logging
import socketio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.logger import setup_logging, get_logger
from backend.routes.auth import router as auth_router
from backend.routes.rooms import router as rooms_router
from backend.routes.queue import router as queue_router
from backend.sockets.connection import register_connection_handlers
from backend.sockets.chat import register_chat_handlers
from backend.sockets.playback import register_playback_handlers
from backend.sockets.queue import register_queue_handlers

# Initialize logging
setup_logging()
logger = get_logger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.ALLOWED_ORIGINS,
    logger=True,
    engineio_logger=False,
)

app = FastAPI(title="Open Jam", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(queue_router)

register_connection_handlers(sio)
register_chat_handlers(sio)
register_playback_handlers(sio)
register_queue_handlers(sio)

socket_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.on_event("startup")
async def startup():
    logger.info("Starting Open Jam application...")
    init_db()
    logger.info(f"CORS allowed origins: {settings.ALLOWED_ORIGINS}")
    logger.info("Database initialized successfully")
    logger.info("Open Jam startup complete")


@app.get("/health")
async def health():
    logger.debug("Health check requested")
    return JSONResponse({"status": "ok", "app": "Open Jam"})


@app.get("/")
async def serve_home():
    return FileResponse("frontend/index.html")


@app.get("/room/{room_id}")
async def serve_room(room_id: str):
    return FileResponse("frontend/room.html")


@app.get("/config.js")
async def serve_config():
    """Expose safe frontend config (API keys for public APIs)."""
    js = f'window.YOUTUBE_API_KEY = "{settings.YOUTUBE_API_KEY}";'
    return Response(content=js, media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
