# 🧪 Testing Guide for Voice Service

This guide will help you test your voice service to ensure everything is working correctly.

## 📋 Prerequisites

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# or
pip install -r requirements_updated.txt
```

### 2. Set Environment Variables
Create a `.env` file with:
```env
DATABASE_URL=postgresql://postgres:root@localhost/voice_model
GROQ_API_KEY=your_groq_api_key_here
GROQ_STT_MODEL=whisper-large-v3-turbo
GROQ_LLM_MODEL=llama-3.3-70b-versatile
GROQ_TTS_MODEL=playai-tts
GROQ_TTS_VOICE=Celeste-PlayAI
```

### 3. Start PostgreSQL
Make sure PostgreSQL is running and the database `voice_model` exists.

### 4. Install Test Dependencies
```bash
pip install requests websockets numpy wave
```

## 🚀 Quick Test Steps

### Step 1: Start the Server
```bash
uvicorn main:app --reload
```
You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Test Health Endpoint
```bash
python test_health.py
```

Expected output:
```
✅ Health check successful!
Overall Status: healthy
Database: connected
Message: All systems operational
✅ All systems operational!
```

### Step 3: Test WebSocket Connection
```bash
python test_websocket_simple.py
```

Expected output:
```
✅ WebSocket connected successfully!
📝 Testing text message...
Sent: {'type': 'message', 'data': 'Hello, this is a test message!'}
🎵 Testing audio message...
📁 Test audio saved to 'test_tone.wav'
🎧 Listening for responses (10 seconds)...
📊 State: listening
🎉 All tests passed!
```

### Step 4: Test with Browser Client

1. Open `test_voice_client.html` in your browser
2. Click "Start session"
3. Allow microphone access
4. Speak into your microphone
5. You should see the state change from `listening` → `processing` → `responding`
6. Hear the bot's response through your speakers

## 🔍 Advanced Testing

### Testing with cURL

**Test root endpoint:**
```bash
curl http://localhost:8000/
```

**Test health endpoint:**
```bash
curl http://localhost:8000/health
```

### Testing with WebSocket Client Tools

**Using wscat:**
```bash
# Install
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/api/ws

# Send audio (base64 encoded)
{"type": "audio", "data": "base64_encoded_audio_here", "sample_rate": 16000, "channels": 1}
```

### Test Different Audio Formats

The service expects:
- Sample rate: 16000 Hz
- Channels: 1 (mono)
- Format: 16-bit PCM
- Encoding: Base64

## 🐛 Troubleshooting

### Common Issues

1. **"Database connection failed"**
   - Check PostgreSQL is running
   - Verify DATABASE_URL in .env
   - Ensure database `voice_model` exists

2. **"Missing GROQ_API_KEY"**
   - Set GROQ_API_KEY in .env
   - Get API key from https://groq.com

3. **WebSocket won't connect**
   - Check server is running on port 8000
   - Verify endpoint is `/api/ws` (not `/ws`)

4. **No audio response**
   - Check microphone permissions
   - Verify browser supports WebRTC
   - Check console for JavaScript errors

5. **Python test script errors**
   - Install missing dependencies: `pip install requests websockets numpy wave`
   - Check Python version (3.8+ required)

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Server Logs

Look for these messages in server output:
- `🔌 WebSocket connection established`
- `📥 Receiving audio from frontend`
- `🎤 User started speaking`
- `🔊 Bot started speaking`

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] Health endpoint returns "healthy" and "connected"
- [ ] WebSocket connects successfully
- [ ] Audio is received from microphone
- [ ] State changes work (listening → processing → responding)
- [ ] Bot responds with audio
- [ ] Database operations work (if applicable)

## 📞 Getting Help

If you encounter issues:

1. Check the server console output
2. Review browser console (F12) for JavaScript errors
3. Verify all environment variables are set
4. Ensure all dependencies are installed

## 🎓 Next Steps

Once basic testing passes:

1. Test with different microphones
2. Test in different browsers (Chrome, Firefox, Safari)
3. Test with longer conversations
4. Monitor resource usage (CPU, memory)
5. Test with multiple simultaneous connections