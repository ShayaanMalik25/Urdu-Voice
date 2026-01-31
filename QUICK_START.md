# Quick Start: Self-Hosted STT/LLM Setup

## Prerequisites Checklist

- [ ] Ollama server running on `localhost:11434`
- [ ] Qwen model pulled: `ollama pull qwen2.5:7b`
- [ ] LiveKit server configured (self-hosted or cloud)
- [ ] ElevenLabs API key ready
- [ ] Environment variables configured

## 5-Minute Setup

### 1. Start Ollama (if not running)

```bash
ollama serve > /workspace/ollama.log 2>&1 &
ollama pull qwen2.5:7b
```

### 2. Configure Environment

Create `.env` file:

```env
LIVEKIT_URL=wss://livekit.urduai.store
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret
ELEVEN_API_KEY=your-elevenlabs-key
```

### 3. Install & Run

```bash
pip install -r requirements.txt
python agent.py start
```

## That's It! 🎉

Your agent now uses:
- ✅ In-process STT (Faster Whisper)
- ✅ Self-hosted LLM (Ollama)
- ✅ ElevenLabs TTS (API)

## Verify It's Working

Check logs for:
- `✅ Whisper model loaded successfully`
- `Transcribed: [your text]`
- LLM responses appearing

## Troubleshooting

**STT not working?**
- Check GPU: `nvidia-smi`
- Try CPU: Set `WHISPER_DEVICE=cpu` in `.env`

**LLM not working?**
- Check Ollama: `curl http://localhost:11434/v1/models`
- Make sure model is pulled: `ollama list`

**TTS not working?**
- Check API key: `ELEVEN_API_KEY` in `.env`
- Verify at https://elevenlabs.io/

## Next: Deploy to RunPod

See `SETUP_GUIDE.md` for detailed deployment instructions.
