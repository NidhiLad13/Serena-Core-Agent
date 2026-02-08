# main.py
from fastapi import FastAPI
from app.api.websocket import chat_ws
from app.api.voice_websocket import voice_ws
from app.api.rest import router as rest_router
from fastapi.middleware.cors import CORSMiddleware


# Add this route (
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003"
    ],  # Allow multiple Vite dev server ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API routes
app.include_router(rest_router, prefix="/api", tags=["api"])

# WebSocket routes
app.add_api_websocket_route("/ws/chat/{conversation_id}", chat_ws)
app.add_api_websocket_route("/ws/voice/{conversation_id}", voice_ws)