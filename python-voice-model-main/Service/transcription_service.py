import asyncio
import json
from datetime import datetime
from typing import ClassVar, Dict, List, Literal, Set
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

class TranscriptionService:

    messages: ClassVar[List[Dict[str, str]]] = []
    connections: ClassVar[Set[WebSocket]] = set()

    def __init__(self):
        pass

    @classmethod
    def add_message(cls, type: Literal["bot", "user"], message: str) -> None:
        cls.messages.append({"type": type, "message": message, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        if cls.connections:
            payload = json.dumps(cls.messages)
            for websocket in list(cls.connections):
                asyncio.create_task(cls._send_update(websocket, payload))

    @classmethod
    def get_transcription(cls) -> List[Dict[str, str]]:
        return cls.messages

    @classmethod
    async def _send_update(cls, websocket: WebSocket, payload: str) -> None:
        try:
            await websocket.send_text(payload)
        except Exception as e:
            logger.warning(f"Removing transcription subscriber due to send error: {e}")
            cls.connections.discard(websocket)

    @classmethod
    async def transcription_socket_endpoint(cls, websocket: WebSocket) -> None:
        await websocket.accept()
        cls.connections.add(websocket)

        try:
            if cls.messages:
                await websocket.send_text(json.dumps(cls.messages))

            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"Error in transcription socket endpoint: {e}")
        finally:
            cls.connections.discard(websocket)
            # Clear transcription messages when the last connection disconnects
            if not cls.connections:
                cls.messages.clear()
            await websocket.close()