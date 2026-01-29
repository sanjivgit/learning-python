
import asyncio
import json
import os
import re
from typing import Optional, Literal
from fastapi import WebSocket
from loguru import logger

from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.tts import GroqTTSService
from Service.json_serializer import JsonFrameSerializer
from Service.order_service import OrderService, OrderStatus
from pipecat.transcriptions.language import Language
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InputAudioRawFrame,
    OutputTransportMessageFrame,
    StartFrame,
    TextFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

from Service.transcription_service import TranscriptionService


class AudioLoggingProcessor(FrameProcessor):
    """Logs audio reception for debugging purposes."""

    def __init__(self):
        super().__init__()
        self._audio_chunk_count = 0
        self._total_audio_bytes = 0

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InputAudioRawFrame):
            self._audio_chunk_count += 1
            audio_size = len(frame.audio)
            self._total_audio_bytes += audio_size
            
            # Log every 50 chunks to avoid spam
            if self._audio_chunk_count % 50 == 1:
                logger.info(
                    f"📥 Receiving audio from frontend | "
                    f"Chunk #{self._audio_chunk_count} | "
                    f"Size: {audio_size} bytes | "
                    f"Sample rate: {frame.sample_rate}Hz | "
                    f"Total received: {self._total_audio_bytes / 1024:.2f} KB"
                )

        await self.push_frame(frame, direction)


class ConversationStateProcessor(FrameProcessor):
    """Pushes conversational state updates downstream when talk/listen events occur."""

    def __init__(self):
        super().__init__()
        self._state: Optional[str] = None

    async def _notify(self, state: str):
        if self._state == state:
            return
        self._state = state
        payload = json.dumps({"type": "state", "value": state})
        await self.push_frame(
            OutputTransportMessageFrame(message=payload),
            FrameDirection.DOWNSTREAM,
        )

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, StartFrame) and direction == FrameDirection.DOWNSTREAM:
            await self._notify("listening")
        elif isinstance(frame, UserStartedSpeakingFrame) and direction == FrameDirection.DOWNSTREAM:
            logger.info("🎤 User started speaking")
            await self._notify("listening")
        elif isinstance(frame, UserStoppedSpeakingFrame) and direction == FrameDirection.DOWNSTREAM:
            logger.info("⏸️  User stopped speaking")
            await self._notify("processing")
        elif isinstance(frame, BotStartedSpeakingFrame):
            logger.info("🔊 Bot started speaking")
            await self._notify("responding")
        elif isinstance(frame, BotStoppedSpeakingFrame):
            logger.info("✅ Bot finished speaking")
            await self._notify("listening")

        await self.push_frame(frame, direction)

class TranscriptionProcessor(FrameProcessor):
    def __init__(self, role: Literal["user", "bot"]):
        super().__init__()
        self._transcription_service = TranscriptionService()
        self._role = role
        self._bot_buffer: str = "" if role == "bot" else ""

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame):
            if self._role == "bot":
                # Buffer bot chunks; do not emit per-chunk entries
                self._bot_buffer += frame.text or ""
            else:
                # User messages stream as-is
                self._transcription_service.add_message("user", frame.text)
                transcription = self._transcription_service.get_transcription()
                await self.push_frame(
                    OutputTransportMessageFrame(message=json.dumps(transcription)),
                    FrameDirection.DOWNSTREAM,
                )

        # When bot finishes speaking, flush a single combined message
        if isinstance(frame, BotStoppedSpeakingFrame) and self._role == "bot":
            text = self._bot_buffer.strip()
            if text:
                self._transcription_service.add_message("bot", text)
            self._bot_buffer = ""

        await self.push_frame(frame, direction)

class OrderKnowledgeProcessor(FrameProcessor):
    def __init__(self, context: OpenAILLMContext):
        super().__init__()
        self._context = context
        self._order_service = OrderService()
        self._awaiting_order_number = False
        self._last_detected_order_number: Optional[str] = None
        self._knowledge_base_tag = "order-knowledge-base"
        self._last_system_messages: dict[str, str] = {}

    def _detect_order_intent(self, text: str) -> bool:
        normalized = text.lower()
        return any(
            keyword in normalized
            for keyword in ("order status", "track my order", "check my order", "order update")
        ) or ("order" in normalized and "status" in normalized)

    def _extract_order_number(self, text: str) -> Optional[str]:
        # Match explicit patterns like:
        #  - "order number is 1003"
        #  - "order #1003"
        #  - "order no. 1003"
        #  - "order 1003"
        match = re.search(
            r"order\s*(?:number|no\.?|#)?(?:\s*(?:is|:))?\s*(\d{3,})",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        # Fallback: find any standalone 3+ digit sequence. We accept 3+ digits to
        # support order numbers like 1003 while avoiding tiny integers like '2'.
        standalone = re.search(r"\b(\d{3,})\b", text)
        if standalone:
            return standalone.group(1)

        return None

    def _status_summary(self, order_status: OrderStatus) -> str:
        mapping = {
            OrderStatus.PENDING: "is pending and awaiting processing."
            " Let the customer know we'll update them once it starts moving.",
            OrderStatus.PROCESSING: "is being prepared right now."
            " Share a reassuring update and let them know we'll notify them once it ships.",
            OrderStatus.SHIPPED: "has shipped."
            " Review the provided delivery estimate and repeat it back accurately.",
            OrderStatus.DELIVERED: "has already been delivered."
            " Confirm the delivery date and offer follow-up help if needed.",
            OrderStatus.CANCELLED: "was cancelled."
            " Clarify the cancellation and offer to help place a new order if appropriate.",
        }
        return mapping.get(order_status, f"has status {order_status.value}.")

    def _add_system_message(self, content: str, tag: Optional[str] = None):
        if tag and self._last_system_messages.get(tag) == content:
            return
        self._context.add_message({"role": "system", "content": content})
        if tag:
            self._last_system_messages[tag] = content

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame) and direction == FrameDirection.DOWNSTREAM:
            text = (frame.text or "").strip()
            logger.success(f"📝 Transcription received: {text}")
            if not text:
                await self.push_frame(frame, direction)
                return

            order_number = self._extract_order_number(text)

            logger.success(f"🔍 Extracted order number: {order_number}")

            if order_number:
                if order_number != self._last_detected_order_number:
                    self._last_detected_order_number = order_number
                    order = self._order_service.get_order_by_id(int(order_number))
                    if order:
                        self._awaiting_order_number = False
                        details = self._order_service.format_order_details(order)
                        summary_hint = f"Order {order.id} {self._status_summary(order.status)}"
                        self._add_system_message(
                            (
                                f"Order lookup result for order number {order_number}:\n"
                                f"{details}\n"
                                "Use ONLY this data when responding."
                                " State the order status and delivery expectation exactly as shown,"\
                                " and mention key items only if needed."
                                " Never invent additional products, dates, or amounts."\
                                f" Hint for tone: {summary_hint}"
                            ),
                            tag="order-lookup",
                        )
                    else:
                        self._add_system_message(
                            (
                                f"No order was found with number {order_number}."
                                " Tell the user you couldn't locate that order in the dataset,"\
                                " and politely ask them to confirm the digits or share a different order number."
                                " Do not guess any details."
                            ),
                            tag="order-not-found",
                        )
                await self.push_frame(frame, direction)
                return

            if self._detect_order_intent(text) and not self._awaiting_order_number:
                self._awaiting_order_number = True
                self._add_system_message(
                    (
                        "The user asked for an order status but has not yet provided an order number."
                        " Ask directly for the order number, mentioning you need it to fetch accurate details."
                    ),
                    tag=self._knowledge_base_tag,
                )

        await self.push_frame(frame, direction)


class VoiceService:
    _groq_api_key = os.getenv("GROQ_API_KEY")
    _stt_model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
    _llm_model = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
    _tts_model = os.getenv("GROQ_TTS_MODEL", "playai-tts")
    _tts_voice = os.getenv("GROQ_TTS_VOICE", "Celeste-PlayAI")

    @classmethod
    async def websocket_endpoint(cls, websocket: WebSocket):
        if not cls._groq_api_key:
            await websocket.close(code=1011)
            logger.error("Missing GROQ_API_KEY environment variable; refusing WebSocket connection")
            return

        await websocket.accept()
        logger.info(f"🔌 WebSocket connection established from {websocket.client.host if websocket.client else 'unknown'}")

        serializer = JsonFrameSerializer()
        # Use Silero VAD (requires pipecat-ai[silero])
        vad_params = VADParams(confidence=0.8, min_volume=0.02, start_secs=0.15, stop_secs=0.15)
        vad_analyzer = SileroVADAnalyzer(params=vad_params)

        transport_params = FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=vad_analyzer,
            serializer=serializer,
            session_timeout=300,
        )

        transport = FastAPIWebsocketTransport(websocket, transport_params)

        audio_logger = AudioLoggingProcessor()
        state_processor = ConversationStateProcessor()

        stt = GroqSTTService(
            api_key=cls._groq_api_key,
            model=cls._stt_model,
            language=Language.EN,
        )
        
        llm = GroqLLMService(
            api_key=cls._groq_api_key,
            model=cls._llm_model,
        )

        tts = GroqTTSService(
            api_key=cls._groq_api_key,
            model_name=cls._tts_model,
            voice_id=cls._tts_voice,
        )

        knowledge_base = (
            "You are a helpful voice assistant for an online store. Keep responses concise and conversational.\n"
            "Knowledge Base:\n"
            "- Customers ask about their orders, products, or account details.\n"
            "- When a customer asks for an order status, make sure you have an order number.\n"
            "- If no order number is available, politely ask for it.\n"
            "- When order details are provided, summarize the status and delivery expectation using the supplied data.\n"
            "- Be empathetic, efficient, and avoid exposing internal system details."
        )

        messages = [
            {
                "role": "system",
                "content": knowledge_base,
            }
        ]
        
        context = OpenAILLMContext(messages)
        context_aggregator = llm.create_context_aggregator(context)
        order_knowledge = OrderKnowledgeProcessor(context)
        transcription_processor_user = TranscriptionProcessor("user")
        transcription_processor_bot = TranscriptionProcessor("bot")

        pipeline = Pipeline(
            [
                transport.input(),
                audio_logger,
                state_processor,
                stt,
                order_knowledge,
                transcription_processor_user,
                context_aggregator.user(),
                llm,
                transcription_processor_bot,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )
        
        logger.info("🚀 Voice pipeline initialized and ready")

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        runner = PipelineRunner(handle_sigint=False)

        try:
            logger.info("▶️  Starting voice pipeline runner")
            await runner.run(task)
        except Exception as exc:
            logger.exception("❌ Voice pipeline terminated unexpectedly: %s", exc)
            raise
        finally:
            logger.info("🔌 WebSocket connection closed")