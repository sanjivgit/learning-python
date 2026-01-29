# Voice Model Service

A simple FastAPI service with PostgreSQL database connection.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and update with your PostgreSQL credentials:
```bash
cp .env.example .env
```

3. Update `DATABASE_URL` in `.env` with your actual database connection string.

4. Run the application:
```bash
uvicorn main:app --reload
```

## API Endpoints

- `WSS /api/ws` - WebSocket endpoint for voice service
- `WSS /api/transcription` - WebSocket endpoint for real-time transcription streaming
- `GET /health` - Health check endpoint
- `GET /` - Root endpoint returning service status

## Voice Service Details

This section provides a detailed explanation of the core components of the real-time voice assistant functionality.

### `Service/json_serializer.py`

This file is responsible for converting data frames used by the `pipecat` framework into a JSON format suitable for WebSocket communication, and vice-versa.

#### `JsonFrameSerializer`

This class is the key component for communication between the browser-based client and the Python backend.

-   **Purpose**: To serialize outgoing `pipecat` frames (like bot audio and messages) into JSON and deserialize incoming JSON messages (like user audio and commands) back into `pipecat` frames.
-   **Why it's required**: WebSockets work best with text or binary data. This serializer uses a human-readable JSON format, which is easy to debug and consume by a JavaScript client. Audio data is encoded in base64 to be embedded in the JSON payload.
-   **Usage**: An instance of this class is passed to the `FastAPIWebsocketTransport` when the voice pipeline is created. It automatically handles the data conversion for all frames flowing to and from the client.

##### Methods

-   `serialize(frame)`
    -   **Use**: Converts outgoing `pipecat` frames to JSON strings.
    -   **Details**:
        -   If the frame is a `OutputTransportMessageFrame` (e.g., a state update), it's wrapped in `{"type": "message", "data": ...}`.
        -   If the frame is an `OutputAudioRawFrame` (audio from the bot), the raw audio bytes are base64 encoded and sent as `{"type": "audio", "data": "...", "sample_rate": ..., "channels": ...}`.
-   `deserialize(data)`
    -   **Use**: Converts incoming JSON strings from the client into `pipecat` frames.
    -   **Details**:
        -   If the message has `type: "audio"`, it decodes the base64 data into an `InputAudioRawFrame` for the STT service to process.
        -   If the message has `type: "message"`, it's converted into an `InputTransportMessageFrame`.

---

### `Service/voice_service.py`

This file contains the primary logic for the voice assistant, including setting up the processing pipeline and managing the conversation flow.

#### `AudioLoggingProcessor`

-   **Purpose**: A debugging utility to monitor the flow of audio data from the client.
-   **Why it's required**: Helps confirm that the server is receiving audio correctly without flooding the console.
-   **Use**: It's placed at the beginning of the pipeline to intercept and log details about incoming `InputAudioRawFrame`s, such as chunk count and total size.

#### `ConversationStateProcessor`

-   **Purpose**: To track and communicate the assistant's state to the client.
-   **Why it's required**: Allows the frontend to display real-time feedback to the user (e.g., showing "listening," "thinking," or "speaking" indicators).
-   **Use**: It inspects frames like `UserStartedSpeakingFrame`, `BotStartedSpeakingFrame`, etc., to determine the current state and sends a `{"type": "state", "value": "..."}` message to the client.

#### `OrderKnowledgeProcessor`

-   **Purpose**: To provide the LLM with the necessary context to handle questions about order statuses. This is a form of Retrieval-Augmented Generation (RAG).
-   **Why it's required**: An LLM, by itself, has no knowledge of your specific database or business data. This processor acts as a bridge, fetching real-time order information and "injecting" it into the LLM's context just in time.
-   **Use**: It's placed in the pipeline after the STT service. It analyzes the user's transcribed text for order-related intent.
    -   If it detects a question about an order but no order number is present, it adds a `system` message to the LLM's context, instructing it to ask the user for one.
    -   If it extracts an order number, it uses `OrderService` to look up the order. It then adds a detailed `system` message to the context, providing the LLM with the order's full details and instructions on how to present the information. This ensures the LLM's response is based on facts from the database, not on its own general knowledge.

#### `VoiceService`

-   **Purpose**: The main class that orchestrates the entire voice interaction over a WebSocket connection.
-   **Why it's required**: It's the entry point that assembles and runs the complete voice pipeline for each connected user.

##### `websocket_endpoint(websocket: WebSocket)`

-   **Use**: This class method is called by FastAPI for each new WebSocket connection.
-   **Working Flow**:
    1.  **Configuration**: It reads API keys and model names from environment variables.
    2.  **Initialization**: It sets up all the necessary components:
        -   `JsonFrameSerializer` for data exchange.
        -   `SileroVADAnalyzer` for Voice Activity Detection, which helps in determining when the user has finished speaking.
        -   `FastAPIWebsocketTransport` to manage the WebSocket connection.
        -   The custom processors: `AudioLoggingProcessor`, `ConversationStateProcessor`, and `OrderKnowledgeProcessor`.
        -   The core AI services from `pipecat`: `GroqSTTService` (Speech-to-Text), `GroqLLMService` (Language Model), and `GroqTTSService` (Text-to-Speech).
    3.  **Context Setup**: It creates an `OpenAILLMContext` with a base "system" prompt that defines the assistant's persona and general instructions. This context will be updated throughout the conversation.
    4.  **Pipeline Assembly**: It defines the step-by-step flow of data in a `pipecat.pipeline.pipeline.Pipeline`. The order is crucial:
        -   **Input**: `transport.input()` receives audio/messages from the user.
        -   **Processing**: The audio passes through the logger, state processor, and then the STT service.
        -   **Knowledge Injection**: The resulting text is processed by `OrderKnowledgeProcessor` to add any real-time order data to the LLM context.
        -   **LLM**: The user's message is added to the context, and the entire history is sent to the `GroqLLMService`.
        -   **TTS**: The LLM's text response is converted to audio by the `GroqTTSService`.
        -   **Output**: The generated audio and any state messages are sent back to the user via `transport.output()`.
        -   **Context Update**: The bot's response is also added to the context to maintain a coherent conversation history.
    5.  **Execution**: It creates and runs a `PipelineTask`, which manages the asynchronous flow of data through the pipeline for the duration of the WebSocket connection.

---

## Transcription Service

`Service/transcription_service.py` provides real-time transcription streaming:

- **WebSocket**: `/api/transcription` - Subscribe to live conversation transcriptions
- **Features**: Stores messages in-memory with timestamps, broadcasts updates to all connected clients
- **Integration**: Automatically captures user speech and bot responses from the voice pipeline