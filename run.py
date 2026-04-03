"""Open Jam — Development server launcher.

Usage:
    python run.py

Visit: http://localhost:8000

NOTE: reload=True breaks WebSocket transport (uvicorn reloader doesn't proxy
WS upgrades). Run without reload for proper real-time Socket.IO via WebSocket.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
