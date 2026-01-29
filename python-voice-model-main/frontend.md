# Frontend Implementation Guide for Voice AI Assistant (Next.js)

## Architecture Overview

The frontend acts as a **continuous audio streaming client** that:
1. Captures microphone audio continuously
2. Processes and formats audio chunks
3. Streams to backend via WebSocket
4. Receives and plays back AI responses
5. Updates UI based on conversation state

**Important**: Frontend does NOT implement Voice Activity Detection (VAD) - the backend handles all speech detection.

---

## Tech Stack

- **Next.js 14+** (App Router or Pages Router)
- **React 18+** with Hooks
- **TypeScript** (recommended)
- **Web Audio API**: For audio capture and processing
- **WebSocket API**: For real-time bidirectional communication

---

## Project Structure

```
app/
├── components/
│   └── VoiceAssistant.tsx       # Main voice component
├── hooks/
│   ├── useVoiceClient.ts        # Voice client hook
│   └── useAudioProcessor.ts     # Audio processing hook
├── lib/
│   ├── audioUtils.ts            # Audio utility functions
│   └── websocketClient.ts       # WebSocket client class
└── page.tsx                     # Main page
```

---

## Implementation Steps

### 1. Audio Utility Functions (`lib/audioUtils.ts`)

Create reusable audio processing functions:

```typescript
// lib/audioUtils.ts

/**
 * Convert Float32Array to Int16Array (PCM format)
 */
export function convertFloat32ToInt16(float32Array: Float32Array): Int16Array {
  const int16Array = new Int16Array(float32Array.length);
  
  for (let i = 0; i < float32Array.length; i++) {
    const clamped = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7FFF;
  }
  
  return int16Array;
}

/**
 * Downsample audio buffer from one sample rate to another
 */
export function downsampleBuffer(
  inputBuffer: Int16Array,
  inputSampleRate: number,
  targetSampleRate: number
): Int16Array {
  if (inputSampleRate === targetSampleRate) {
    return inputBuffer;
  }

  const sampleRateRatio = inputSampleRate / targetSampleRate;
  const newLength = Math.round(inputBuffer.length / sampleRateRatio);
  const result = new Int16Array(newLength);

  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < newLength) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    
    let accum = 0;
    let count = 0;
    
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < inputBuffer.length; i++) {
      accum += inputBuffer[i];
      count++;
    }
    
    const avgSample = accum / (count || 1);
    const clamped = Math.max(-1, Math.min(1, avgSample));
    result[offsetResult] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7FFF;
    
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

/**
 * Convert ArrayBuffer to Base64 string
 */
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  
  return btoa(binary);
}

/**
 * Convert Base64 string to ArrayBuffer
 */
export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const len = binary.length;
  const buffer = new ArrayBuffer(len);
  const view = new Uint8Array(buffer);
  
  for (let i = 0; i < len; i++) {
    view[i] = binary.charCodeAt(i);
  }
  
  return buffer;
}

/**
 * Play PCM audio through Web Audio API
 */
export function playPcmAudio(
  int16Array: Int16Array,
  sampleRate: number,
  audioContext: AudioContext
): void {
  // Convert Int16 to Float32
  const float32Array = new Float32Array(int16Array.length);
  for (let i = 0; i < int16Array.length; i++) {
    float32Array[i] = int16Array[i] / 0x8000;
  }

  // Create audio buffer
  const audioBuffer = audioContext.createBuffer(1, float32Array.length, sampleRate);
  audioBuffer.copyToChannel(float32Array, 0);

  // Create source and play
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start();
}
```

---

### 2. Custom Hook: useVoiceClient (`hooks/useVoiceClient.ts`)

Create a React hook to manage the voice client:

```typescript
// hooks/useVoiceClient.ts
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  convertFloat32ToInt16,
  downsampleBuffer,
  arrayBufferToBase64,
  base64ToArrayBuffer,
  playPcmAudio,
} from '@/lib/audioUtils';

type ConversationState = 'idle' | 'listening' | 'processing' | 'responding';

interface UseVoiceClientOptions {
  wsUrl?: string;
  targetSampleRate?: number;
  bufferSize?: number;
}

export function useVoiceClient(options: UseVoiceClientOptions = {}) {
  const {
    wsUrl = 'ws://localhost:8000/api/ws',
    targetSampleRate = 16000,
    bufferSize = 4096,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationState, setConversationState] = useState<ConversationState>('idle');
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);

  // Initialize playback context once
  useEffect(() => {
    if (typeof window !== 'undefined') {
      playbackContextRef.current = new AudioContext();
    }
    
    return () => {
      playbackContextRef.current?.close();
    };
  }, []);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const payload = JSON.parse(event.data);

      switch (payload.type) {
        case 'audio': {
          // Play received audio
          const pcmBuffer = base64ToArrayBuffer(payload.data);
          const int16Array = new Int16Array(pcmBuffer);
          const sampleRate = payload.sample_rate || 48000;
          
          if (playbackContextRef.current) {
            playPcmAudio(int16Array, sampleRate, playbackContextRef.current);
          }
          break;
        }

        case 'message': {
          // Handle state messages
          let data = payload.data;
          if (typeof data === 'string') {
            data = JSON.parse(data);
          }

          if (data.type === 'state') {
            setConversationState(data.value);
          }
          break;
        }

        default:
          console.warn('Unknown message type:', payload.type);
      }
    } catch (err) {
      console.error('Failed to handle message:', err);
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    return new Promise<void>((resolve, reject) => {
      try {
        const socket = new WebSocket(wsUrl);
        socket.binaryType = 'arraybuffer';

        socket.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
          setError(null);
          resolve();
        };

        socket.onerror = (err) => {
          console.error('WebSocket error:', err);
          setError('Connection failed');
          reject(err);
        };

        socket.onclose = () => {
          console.log('WebSocket closed');
          setIsConnected(false);
          setConversationState('idle');
        };

        socket.onmessage = handleMessage;

        socketRef.current = socket;
      } catch (err) {
        reject(err);
      }
    });
  }, [wsUrl, handleMessage]);

  // Setup audio processing
  const setupAudioProcessing = useCallback(
    async (stream: MediaStream) => {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      const audioContext = audioContextRef.current;
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);

      processor.onaudioprocess = (event) => {
        if (!isStreaming || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
          return;
        }

        const inputData = event.inputBuffer.getChannelData(0);
        const int16Data = convertFloat32ToInt16(inputData);
        const downsampled = downsampleBuffer(
          int16Data,
          audioContext.sampleRate,
          targetSampleRate
        );

        const message = {
          type: 'audio',
          data: arrayBufferToBase64(downsampled.buffer),
          sample_rate: targetSampleRate,
          channels: 1,
        };

        socketRef.current.send(JSON.stringify(message));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      sourceNodeRef.current = source;
      processorNodeRef.current = processor;
    },
    [bufferSize, targetSampleRate, isStreaming]
  );

  // Start streaming session
  const startSession = useCallback(async () => {
    try {
      setError(null);

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 48000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      mediaStreamRef.current = stream;

      // Setup audio processing
      await setupAudioProcessing(stream);

      // Connect to WebSocket
      await connect();

      setIsStreaming(true);
      console.log('Voice session started');
    } catch (err: any) {
      console.error('Failed to start session:', err);
      
      if (err.name === 'NotAllowedError') {
        setError('Microphone permission denied');
      } else if (err.name === 'NotFoundError') {
        setError('No microphone found');
      } else {
        setError('Failed to start session');
      }
      
      cleanup();
    }
  }, [connect, setupAudioProcessing]);

  // Stop streaming session
  const stopSession = useCallback(() => {
    setIsStreaming(false);
    cleanup();
    console.log('Voice session stopped');
  }, []);

  // Cleanup resources
  const cleanup = useCallback(() => {
    setIsStreaming(false);

    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current.onaudioprocess = null;
      processorNodeRef.current = null;
    }

    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setIsConnected(false);
    setConversationState('idle');
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    isConnected,
    isStreaming,
    conversationState,
    error,
    startSession,
    stopSession,
  };
}
```

---

### 3. Voice Assistant Component (`components/VoiceAssistant.tsx`)

Create the main React component:

```typescript
// components/VoiceAssistant.tsx
'use client';

import { useVoiceClient } from '@/hooks/useVoiceClient';

const stateConfig = {
  idle: {
    color: 'text-gray-400',
    bg: 'bg-gray-900',
    text: 'Ready',
    icon: '⚫',
  },
  listening: {
    color: 'text-green-500',
    bg: 'bg-green-900/20',
    text: 'Listening...',
    icon: '🎤',
  },
  processing: {
    color: 'text-orange-500',
    bg: 'bg-orange-900/20',
    text: 'Processing...',
    icon: '⚙️',
  },
  responding: {
    color: 'text-blue-500',
    bg: 'bg-blue-900/20',
    text: 'Speaking...',
    icon: '🔊',
  },
};

export default function VoiceAssistant() {
  const {
    isConnected,
    isStreaming,
    conversationState,
    error,
    startSession,
    stopSession,
  } = useVoiceClient({
    wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/ws',
  });

  const currentState = stateConfig[conversationState];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Voice AI Assistant</h1>
          <p className="text-gray-400">
            Click Start to begin a voice conversation with the AI assistant
          </p>
        </div>

        {/* Status Card */}
        <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800 mb-8">
          {/* Connection Status */}
          <div className="flex items-center justify-between mb-6">
            <span className="text-gray-400">Connection:</span>
            <div className="flex items-center gap-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className={isConnected ? 'text-green-500' : 'text-red-500'}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          {/* Conversation State */}
          <div className="flex items-center justify-between mb-8">
            <span className="text-gray-400">Assistant:</span>
            <div className={`flex items-center gap-3 px-4 py-2 rounded-full ${currentState.bg}`}>
              <span className="text-2xl">{currentState.icon}</span>
              <span className={`font-semibold ${currentState.color}`}>
                {currentState.text}
              </span>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-900/20 border border-red-500 rounded-lg">
              <p className="text-red-500">{error}</p>
            </div>
          )}

          {/* Control Buttons */}
          <div className="flex gap-4">
            <button
              onClick={startSession}
              disabled={isStreaming}
              className={`flex-1 py-4 px-6 rounded-full font-semibold text-lg transition-all ${
                isStreaming
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-500 text-white'
              }`}
            >
              {isStreaming ? 'Session Active' : 'Start Session'}
            </button>

            <button
              onClick={stopSession}
              disabled={!isStreaming}
              className={`flex-1 py-4 px-6 rounded-full font-semibold text-lg transition-all ${
                !isStreaming
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-500 text-white'
              }`}
            >
              Stop Session
            </button>
          </div>
        </div>

        {/* Info Card */}
        <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h3 className="text-lg font-semibold mb-3">How it works:</h3>
          <ul className="space-y-2 text-gray-400">
            <li>• Click "Start Session" to begin</li>
            <li>• Speak naturally into your microphone</li>
            <li>• The AI will automatically detect when you finish speaking</li>
            <li>• Listen to the AI's response</li>
            <li>• Continue the conversation naturally</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
```

---

### 4. Main Page (`app/page.tsx`)

For App Router:

```typescript
// app/page.tsx
import VoiceAssistant from '@/components/VoiceAssistant';

export default function Home() {
  return <VoiceAssistant />;
}
```

Or for Pages Router:

```typescript
// pages/index.tsx
import VoiceAssistant from '@/components/VoiceAssistant';

export default function Home() {
  return <VoiceAssistant />;
}
```

---

### 5. Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws
```

For production:

```bash
NEXT_PUBLIC_WS_URL=wss://your-domain.com/api/ws
```

---

## Message Format Specification

### Outgoing (Frontend → Backend)

#### Audio Message
```json
{
  "type": "audio",
  "data": "<base64-encoded-int16-pcm>",
  "sample_rate": 16000,
  "channels": 1
}
```

### Incoming (Backend → Frontend)

#### Audio Response
```json
{
  "type": "audio",
  "data": "<base64-encoded-int16-pcm>",
  "sample_rate": 48000,
  "channels": 1
}
```

#### State Update
```json
{
  "type": "message",
  "data": "{\"type\":\"state\",\"value\":\"listening\"}"
}
```

Possible state values:
- `"listening"` - Waiting for user speech
- `"processing"` - Speech detected, processing with LLM
- `"responding"` - AI speaking response

---

## Performance Considerations

### Buffer Size
- **4096 samples** provides good balance between latency and CPU usage
- Smaller buffers = lower latency but higher CPU usage
- Larger buffers = higher latency but lower CPU usage

### Sample Rate
- Frontend captures at **48000 Hz** (browser default)
- Downsamples to **16000 Hz** for backend (reduces bandwidth by 67%)
- Backend responds at **48000 Hz** (high quality TTS)

### Network Optimization
- Each chunk ~0.085 seconds of audio (4096 samples @ 48kHz)
- After downsampling: ~1.4KB per chunk
- Bandwidth: ~16KB/s upload, ~48KB/s download

---

## 6. TypeScript Types (Optional but Recommended)

Create type definitions:

```typescript
// types/voice.ts

export type ConversationState = 'idle' | 'listening' | 'processing' | 'responding';

export interface AudioMessage {
  type: 'audio';
  data: string;
  sample_rate: number;
  channels: number;
}

export interface StateMessage {
  type: 'message';
  data: string | {
    type: 'state';
    value: ConversationState;
  };
}

export type ServerMessage = AudioMessage | StateMessage;

export interface VoiceClientConfig {
  wsUrl: string;
  targetSampleRate?: number;
  bufferSize?: number;
}
```

---

## 7. Advanced Features

### Add Audio Visualization

```typescript
// components/AudioVisualizer.tsx
'use client';

import { useEffect, useRef } from 'react';

interface AudioVisualizerProps {
  isActive: boolean;
}

export function AudioVisualizer({ isActive }: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();

  useEffect(() => {
    if (!isActive) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bars = 32;
    const barWidth = canvas.width / bars;

    const animate = () => {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.3)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      for (let i = 0; i < bars; i++) {
        const height = Math.random() * canvas.height * 0.7;
        const x = i * barWidth;
        const y = canvas.height - height;

        const gradient = ctx.createLinearGradient(0, y, 0, canvas.height);
        gradient.addColorStop(0, '#22c55e');
        gradient.addColorStop(1, '#16a34a');

        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth - 2, height);
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={200}
      className="w-full h-32 rounded-lg"
    />
  );
}
```

### Add Conversation History

```typescript
// hooks/useConversationHistory.ts
'use client';

import { useState, useCallback } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export function useConversationHistory() {
  const [messages, setMessages] = useState<Message[]>([]);

  const addMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    const message: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, message]);
  }, []);

  const clearHistory = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, addMessage, clearHistory };
}
```

---

## Configuration

### next.config.js

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Disable strict mode in production if audio issues occur
  // reactStrictMode: process.env.NODE_ENV === 'development',
};

module.exports = nextConfig;
```

### tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

### package.json

```json
{
  "name": "voice-assistant-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "next": "^14"
  },
  "devDependencies": {
    "typescript": "^5",
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10",
    "postcss": "^8",
    "tailwindcss": "^3",
    "eslint": "^8",
    "eslint-config-next": "^14"
  }
}
```

---

## Browser Compatibility

### Required APIs
- ✅ WebSocket API (all modern browsers)
- ✅ Web Audio API (all modern browsers)
- ✅ MediaDevices.getUserMedia (all modern browsers)

### Tested Browsers
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

### Not Supported
- Internet Explorer
- Old mobile browsers (pre-2020)

---

## Important Next.js Considerations

### Client-Side Only Code

Always use `'use client'` directive for components using:
- Web Audio API
- WebSocket API
- Browser APIs (navigator, window, etc.)

### Hydration Issues

Prevent hydration mismatches:

```typescript
const [mounted, setMounted] = useState(false);

useEffect(() => {
  setMounted(true);
}, []);

if (!mounted) {
  return null; // or loading spinner
}
```

### Environment Variables

- Use `NEXT_PUBLIC_` prefix for client-side env vars
- Never expose backend API keys to the frontend

---

## Security Considerations

### HTTPS/WSS Requirement
- Use `wss://` in production (not `ws://`)
- Next.js automatically handles HTTPS in production
- Vercel/Netlify provide SSL certificates

### CORS Configuration
- Backend already has CORS enabled (`allow_origins=["*"]`)
- For production, restrict to specific domains

### Permissions
- Microphone permission required
- User must explicitly grant access
- Permission persists per origin

---

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Environment Variables in Vercel
1. Go to Project Settings
2. Add `NEXT_PUBLIC_WS_URL` with production WebSocket URL
3. Redeploy

### Docker

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

---

## Debugging Tips

### Enable Console Logging

Add debug mode to hook:

```typescript
const [debug, setDebug] = useState(false);

useEffect(() => {
  if (debug) {
    console.log('State:', conversationState);
    console.log('Connected:', isConnected);
    console.log('Streaming:', isStreaming);
  }
}, [debug, conversationState, isConnected, isStreaming]);
```

### Monitor Audio Levels

```typescript
processor.onaudioprocess = (event) => {
  const inputData = event.inputBuffer.getChannelData(0);
  const rms = Math.sqrt(
    inputData.reduce((sum, val) => sum + val * val, 0) / inputData.length
  );
  console.log('Audio RMS:', rms);
  
  // ... rest of processing
};
```

### WebSocket State Monitoring

```typescript
useEffect(() => {
  const interval = setInterval(() => {
    if (socketRef.current) {
      console.log('WebSocket readyState:', socketRef.current.readyState);
    }
  }, 5000);

  return () => clearInterval(interval);
}, []);
```

---

## Common Issues & Solutions

### Issue: "Window is not defined" error
**Solution**: Use `'use client'` directive and check `typeof window !== 'undefined'`

### Issue: No audio captured
**Solution**: Check microphone permissions in browser settings

### Issue: Echo/feedback
**Solution**: Ensure `echoCancellation: true` in getUserMedia constraints

### Issue: Choppy playback
**Solution**: Increase buffer size to 8192 or check network latency

### Issue: WebSocket disconnects
**Solution**: Backend timeout is 300s, implement reconnection logic

### Issue: React StrictMode double-mounting
**Solution**: Use refs to prevent duplicate connections or disable StrictMode

---

## Quick Start

### 1. Create Next.js Project

```bash
npx create-next-app@latest voice-assistant --typescript --tailwind --app
cd voice-assistant
```

### 2. Create Project Structure

```bash
mkdir -p lib hooks components types
```

### 3. Copy Files

Copy the code from sections above into respective files:
- `lib/audioUtils.ts`
- `hooks/useVoiceClient.ts`
- `components/VoiceAssistant.tsx`
- `app/page.tsx`

### 4. Add Environment Variable

Create `.env.local`:

```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws
```

### 5. Run Development Server

```bash
npm run dev
```

Visit `http://localhost:3000`

---

## Testing Checklist

- [ ] Microphone permission granted
- [ ] WebSocket connects successfully
- [ ] Audio streaming starts when clicking "Start Session"
- [ ] Conversation state updates correctly
- [ ] AI responses play back clearly
- [ ] Session stops cleanly
- [ ] No memory leaks on component unmount
- [ ] Works in Chrome, Firefox, Safari

---

## Performance Tips

1. **Buffer Size**: Start with 4096, increase to 8192 if CPU usage is low
2. **Sample Rate**: 16kHz is optimal for speech recognition
3. **Downsampling**: Essential to reduce bandwidth (67% reduction)
4. **Audio Context**: Reuse single instance per session
5. **WebSocket**: Keep-alive prevents disconnections

---

## Next Steps

1. ✅ Copy the utility functions to `lib/audioUtils.ts`
2. ✅ Implement the custom hook in `hooks/useVoiceClient.ts`
3. ✅ Create the component in `components/VoiceAssistant.tsx`
4. ✅ Update your page to use the component
5. ✅ Test with backend at `ws://localhost:8000/api/ws`
6. ⚙️ Add conversation history display (optional)
7. ⚙️ Add audio visualization (optional)
8. 🚀 Deploy to Vercel/Netlify with WSS URL

---

## Additional Resources

- [Web Audio API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [WebSocket API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Next.js Documentation](https://nextjs.org/docs)
- [React Hooks Documentation](https://react.dev/reference/react)

**Reference**: The existing `test_voice_client.html` demonstrates the same concepts in vanilla JavaScript.
