# Setup Guide: Self-Hosted STT/LLM with ElevenLabs TTS

This guide explains how to set up your LiveKit agent with:
- **In-process STT** (Faster Whisper) - runs in the agent process
- **Self-hosted LLM** (Ollama) - runs on localhost
- **ElevenLabs TTS** (API) - cloud-based for quality

## Architecture

```
┌─────────────────────────────────┐
│  LiveKit Agent Process          │
│  ├── STT (Faster Whisper)       │ ← In-process (no network)
│  ├── LLM Client (Ollama)        │ ← localhost:11434
│  └── TTS Client (ElevenLabs)    │ ← API call
└─────────────────────────────────┘
         │
         ├──→ Ollama Server (localhost:11434)
         └──→ ElevenLabs API (cloud)
```

## Step 1: Set Up Ollama LLM Server

### On RunPod (or your server):

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve > /workspace/ollama.log 2>&1 &

# Pull Qwen model (takes 5-10 minutes)
ollama pull qwen2.5:7b

# Verify it's working
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### Alternative Models:

```bash
# Llama 3 8B
ollama pull llama3:8b

# Or use any other Ollama model
ollama list  # See available models
```

## Step 2: Configure Environment Variables

Create `.env` file in `livekit-demo/`:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://livekit.urduai.store
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# ElevenLabs TTS
ELEVEN_API_KEY=your-elevenlabs-api-key

# Ollama LLM (Self-hosted)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:7b

# Faster Whisper STT (In-process)
WHISPER_MODEL=base          # base, small, medium, large-v2, large-v3
WHISPER_DEVICE=cuda         # cuda or cpu
WHISPER_COMPUTE_TYPE=float16  # float16, float32, int8
WHISPER_CACHE_DIR=/workspace/models/whisper
```

## Step 3: Install Dependencies

```bash
cd livekit-demo
pip install -r requirements.txt
```

## Step 4: Test the Setup

### Test 1: Verify Ollama is running

```bash
curl http://localhost:11434/v1/models
```

Should return list of models.

### Test 2: Test Whisper model loading

```bash
python -c "from models.stt import WhisperSTT; stt = WhisperSTT(); print('✅ STT loaded')"
```

### Test 3: Run the agent

```bash
python agent.py start
```

## Step 5: Deploy to RunPod

### Option A: Direct Deployment

1. **SSH into RunPod**
2. **Clone your repo** (or upload files)
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set environment variables** in `.env`
5. **Start agent:**
   ```bash
   python agent.py start
   ```

### Option B: Docker Deployment

1. **Build Docker image:**
   ```bash
   docker build -t your-username/livekit-agent:latest .
   ```

2. **Push to Docker Hub:**
   ```bash
   docker push your-username/livekit-agent:latest
   ```

3. **On RunPod, pull and run:**
   ```bash
   docker pull your-username/livekit-agent:latest
   docker run -d \
     --name livekit-agent \
     --gpus all \
     -e LIVEKIT_URL=wss://livekit.urduai.store \
     -e LIVEKIT_API_KEY=your-key \
     -e LIVEKIT_API_SECRET=your-secret \
     -e ELEVEN_API_KEY=your-key \
     -e OLLAMA_BASE_URL=http://localhost:11434/v1 \
     -e OLLAMA_MODEL=qwen2.5:7b \
     your-username/livekit-agent:latest
   ```

## Configuration Options

### Whisper Model Sizes

| Model | Size | VRAM | Speed | Quality |
|-------|------|------|-------|---------|
| base | ~150MB | 1GB | Fast | Good |
| small | ~500MB | 2GB | Medium | Better |
| medium | ~1.5GB | 5GB | Slower | Best |
| large-v3 | ~3GB | 10GB | Slowest | Excellent |

**Recommendation**: Start with `base` for testing, upgrade to `small` or `medium` if needed.

### Ollama Models

| Model | Size | VRAM | Speed | Quality |
|-------|------|------|-------|---------|
| qwen2.5:7b | 4-5GB | 6-8GB | Fast | Excellent |
| llama3:8b | 4.5-5.5GB | 7-9GB | Fast | Excellent |
| llama3:70b | 40GB | 48GB+ | Slow | Best |

**Recommendation**: Use `qwen2.5:7b` for your RTX 4090 (24GB VRAM).

## Troubleshooting

### STT Issues

**Problem**: "CUDA out of memory"
- **Solution**: Use smaller model (`base` instead of `large-v3`)
- Or use CPU: `WHISPER_DEVICE=cpu`

**Problem**: "Model not found"
- **Solution**: Model downloads automatically on first use
- Check internet connection

### LLM Issues

**Problem**: "Connection refused" to Ollama
- **Solution**: Make sure Ollama is running:
  ```bash
  ollama serve
  ```

**Problem**: "Model not found"
- **Solution**: Pull the model:
  ```bash
  ollama pull qwen2.5:7b
  ```

### TTS Issues

**Problem**: "API key invalid"
- **Solution**: Check `ELEVEN_API_KEY` in `.env`
- Verify key at https://elevenlabs.io/

## Performance Optimization

### For Lower Latency:

1. **Use smaller Whisper model**: `base` or `small`
2. **Use quantized Ollama model**: Already using `qwen2.5:7b` (good)
3. **Use GPU for both**: Set `WHISPER_DEVICE=cuda`
4. **Colocate everything**: Run agent, Ollama, and LiveKit on same instance

### Expected Latencies:

- **STT**: 100-200ms (in-process)
- **LLM TTFT**: 100-300ms (localhost)
- **TTS**: 200-300ms (ElevenLabs API)
- **Total**: 400-800ms (vs 600-1500ms with cloud APIs)

## Next Steps

1. ✅ Set up Ollama server
2. ✅ Configure environment variables
3. ✅ Test locally
4. ✅ Deploy to RunPod
5. ✅ Connect to your Vercel app

Your agent is now using self-hosted STT/LLM for lower latency! 🚀
