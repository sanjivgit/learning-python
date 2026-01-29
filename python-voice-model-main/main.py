from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from Service import HealthService
from Service.voice_service import VoiceService
from Service.transcription_service import TranscriptionService
import uvicorn

app = FastAPI(
    title="Voice Model Service",
    description="A simple FastAPI service backed by static JSON data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Voice Model Service is running"}

@app.get("/health", response_model=dict)
async def health_check():
    health = HealthService.check_health()
    return {
        "status": health.status,
        "database": health.database,
        "message": health.message
    }

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await VoiceService.websocket_endpoint(websocket)

@app.websocket("/api/transcription")
async def transcription_endpoint(websocket: WebSocket):
    await TranscriptionService.transcription_socket_endpoint(websocket)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )