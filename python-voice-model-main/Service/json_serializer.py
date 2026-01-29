import base64
import json
from typing import Optional

from pipecat.frames.frames import (
    InputAudioRawFrame,
    InputTransportMessageFrame,
    OutputAudioRawFrame,
    OutputTransportMessageFrame,
    OutputTransportMessageUrgentFrame,
    StartFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType


class JsonFrameSerializer(FrameSerializer):
    """Human-friendly JSON serializer for Pipecat frames.

    Designed for browser clients that exchange audio as base64 PCM chunks and
    transport messages as plain JSON objects over WebSockets.
    """

    def __init__(self):
        super().__init__()
        self._audio_in_sample_rate: Optional[int] = None

    @property
    def type(self) -> FrameSerializerType:
        return FrameSerializerType.TEXT

    async def setup(self, frame: StartFrame):
        self._audio_in_sample_rate = frame.audio_in_sample_rate

    async def serialize(self, frame):
        if isinstance(frame, (OutputTransportMessageFrame, OutputTransportMessageUrgentFrame)):
            payload = {"type": "message", "data": frame.message}
            return json.dumps(payload)

        if isinstance(frame, OutputAudioRawFrame):
            payload = {
                "type": "audio",
                "data": base64.b64encode(frame.audio).decode("ascii"),
                "sample_rate": frame.sample_rate,
                "channels": frame.num_channels,
            }
            return json.dumps(payload)

        return None

    async def deserialize(self, data):
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return None

        ptype = payload.get("type")
        if ptype == "audio":
            audio_b64 = payload.get("data")
            if not audio_b64:
                return None
            audio_bytes = base64.b64decode(audio_b64)
            sample_rate = payload.get("sample_rate") or self._audio_in_sample_rate or 16000
            channels = payload.get("channels") or 1
            return InputAudioRawFrame(audio=audio_bytes, sample_rate=int(sample_rate), num_channels=int(channels))

        if ptype == "message":
            return InputTransportMessageFrame(message=payload.get("data"))

        return None
