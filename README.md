# LiveKit Voice Agent with Self-Hosted STT/LLM

Voice agent with in-process STT (Faster Whisper), self-hosted LLM (Ollama), and ElevenLabs TTS.

## Architecture

- **STT**: In-process Faster Whisper (runs in agent process, no network latency)
- **LLM**: Self-hosted Ollama (localhost:11434, OpenAI-compatible API)
- **TTS**: ElevenLabs API (cloud-based for quality)

## Prerequisites

1. **Ollama LLM Server** running on `localhost:11434`
   ```bash
   ollama serve
   ollama pull qwen2.5:7b
   ```

2. **LiveKit Server** (self-hosted or cloud)
   - Self-hosted: `wss://livekit.yourdomain.com`
   - Cloud: Get credentials from https://livekit.io/

3. **ElevenLabs API Key** from https://elevenlabs.io/

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download Whisper model** (first time only):
   ```bash
   python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu')"
   ```

3. **Configure environment variables** in `.env`:
   ```env
   # LiveKit
   LIVEKIT_URL=wss://livekit.yourdomain.com
   LIVEKIT_API_KEY=your-api-key
   LIVEKIT_API_SECRET=your-api-secret
   
   # ElevenLabs TTS
   ELEVEN_API_KEY=your-elevenlabs-api-key
   
   # Ollama LLM (optional - defaults shown)
   OLLAMA_BASE_URL=http://localhost:11434/v1
   OLLAMA_MODEL=qwen2.5:7b
   
   # Faster Whisper STT (optional - defaults shown)
   WHISPER_MODEL=base
   WHISPER_DEVICE=cuda
   WHISPER_COMPUTE_TYPE=float16
   WHISPER_CACHE_DIR=/workspace/models/whisper
   ```

4. **Start the agent:**
   ```bash
   python agent.py start
   ```

## Docker Deployment

Build and run with Docker:

```bash
docker build -t livekit-agent .
docker run --gpus all \
  -e LIVEKIT_URL=wss://livekit.yourdomain.com \
  -e LIVEKIT_API_KEY=your-key \
  -e LIVEKIT_API_SECRET=your-secret \
  -e ELEVEN_API_KEY=your-key \
  livekit-agent
```

## Performance

- **STT Latency**: ~100-200ms (in-process, no network)
- **LLM TTFT**: ~100-300ms (localhost, no network)
- **TTS Latency**: ~200-300ms (ElevenLabs API)
- **Total**: ~400-800ms end-to-end (vs 600-1500ms with cloud APIs)