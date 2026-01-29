# Technical Decision Document

## WebRTC vs WebSocket Choice and Justification

WebRTC is a peer-to-peer protocol with very low latency, but has some complexity in implementation with UDP setup and NAT traversal. On the other hand, WebSocket is easier to implement and good for small scale applications, with out-of-the-box support by pipecat.

## STT/TTS Provider Selection

I used Groq for STT and TTS as it is easy to use and cost-effective compared to other providers. The specific models used are "whisper-large-v3-turbo" for STT and "playai-tts" for TTS with the "Celeste-PlayAI" voice. Groq's advantage is that it provides all these models in one place and is easy to set up with a single API key.

## LLM Selection

For the LLM, I chose Groq's "llama-3.3-70b-versatile" model. For smaller applications, models with fewer parameters are generally better as they are faster and more cost-effective.

## Audio Format and Codec Choices

The client sends raw audio to the server wrapped in a JSON structure. The JsonFrameSerializer is used to decode the JSON structure and extract the raw audio data. The audio gets converted into pipecat frames and passed to the pipeline for processing. Similarly, for audio output, the system uses the serializer to convert the pipecat frames back into a JSON structure to send to the client.

## Streaming vs Batch Processing Approach

I implemented a streaming approach for STT and TTS as it is more efficient and provides real-time feedback to the user. In contrast, batch processing would wait until the entire audio is recorded before sending it all at once. This approach would cause delays and make the feedback slower. Additionally, if the connection breaks during transmission, the entire audio would need to be resent, which is inefficient with both time and resources. Batch processing is more suitable for scenarios where immediate responses aren't necessary and higher accuracy is prioritized over speed.