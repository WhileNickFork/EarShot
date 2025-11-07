# EarShot - High-Speed Always-Listening AI Assistant

EarShot is a privacy-focused, always-listening AI assistant designed specifically for the Particle Tachyon 5G single-board computer. It performs real-time speech transcription on-device using NPU acceleration, classifies intent without requiring an LLM, and handles various tasks based on the detected intent.

## Key Features

- **Real-time Speech Processing**: Live transcription using Vosk ASR with NPU acceleration
- **Privacy-First Design**: Only summaries are saved - no raw audio or full transcripts stored
- **Fast Intent Classification**: Uses MiniLM ONNX embeddings with cosine similarity (no LLM required)
- **Multi-Modal Output**: E-ink display feedback + structured JSONL logs
- **GPS Integration**: Location tagging for memories using Tachyon's integrated GNSS
- **Smart Task Management**: Automatically summarizes and adds TODOs to TickTick
- **Hybrid Q&A**: Local small LLM with optional remote LLM upgrade for better answers
- **Graceful Fallbacks**: Works without TickTick/remote LLM/e-ink/GPS when unavailable

## Architecture

### Audio Pipeline
USB mic → sounddevice → VAD (Silero/WebRTC) → Vosk ASR → Intent Classifier → Action Handler

### Intent Classification
- Uses sentence embeddings (all-MiniLM-L6-v2 ONNX) with pre-computed prototypes
- No LLM required for intent detection - extremely fast and efficient
- Configurable similarity threshold for intent matching

### Hardware Requirements
- Particle Tachyon 5G SBC (Qualcomm-based with NPU)
- USB microphone
- GPS antenna connected to u.FL "GNSS" port (optional)
- Waveshare 7.5" V2 e-ink display (optional)

## Quick Start

### 1. Prerequisites
```bash
# Clone this repository to your Tachyon
git clone <repository-url>
cd tachyon/EarShot

# Copy environment template
cp .env.example .env
```

### 2. Download Required Models
Place these models in the `models/` directory:
- `silero_vad.onnx` - [Silero VAD model](https://github.com/snakers4/silero-vad)
- `all-MiniLM-L6-v2-onnx/` - [MiniLM ONNX export](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
  - `model.onnx`
  - `tokenizer.json`
  - `tokenizer_config.json`

### 3. Configure (Optional)
Edit `.env` to customize:
```bash
# TickTick integration (optional)
TICKTICK_CLIENT_ID=your_client_id
TICKTICK_CLIENT_SECRET=your_secret
TICKTICK_ACCESS_TOKEN=your_token

# Enable/disable features
SIMULATION_MODE=false      # Set true for testing without hardware
LLM_REMOTE_ENABLED=true    # Enable remote LLM for answer upgrades
DISPLAY_ENABLED=true       # Set false if no e-ink display
INTENT_THRESHOLD=0.28      # Adjust intent classification sensitivity
```

### 4. Run
```bash
# Build and start containers
docker-compose up -d --build

# Pull small LLM model for local Q&A
docker exec -it ollama ollama pull gemma3:270m

# Monitor logs
docker logs -f tachyon-earshot

# Check health
curl http://localhost:8088/health
```

## Project Structure

```
EarShot/
├── app/                    # Main application code
│   ├── Dockerfile         # Container definition
│   ├── requirements.txt   # Python dependencies
│   ├── main.py           # Entry point
│   ├── audio.py          # Audio capture & processing
│   ├── vad.py            # Voice activity detection
│   ├── asr.py            # Speech recognition (Vosk)
│   ├── intent.py         # Intent classification
│   ├── llm.py            # LLM integration (local/remote)
│   ├── display.py        # E-ink display control
│   ├── gps_tachyon.py    # GPS/GNSS integration
│   ├── ticktick.py       # TickTick task management
│   └── ...
├── models/                # ONNX models (not in git)
├── docker-compose.yml     # Container orchestration
├── .env.example          # Environment template
└── chat.txt              # Project development history
```

## How It Works

1. **Audio Capture**: Continuously captures audio from USB microphone
2. **Voice Detection**: Silero VAD detects speech segments
3. **Transcription**: Vosk ASR transcribes speech in real-time
4. **Intent Classification**: MiniLM embeddings classify intent (TODO/Question/Memory)
5. **Action Handling**:
   - **TODO**: Summarizes task and adds to TickTick
   - **Question**: Queries local LLM, displays on e-ink, optionally upgrades with remote LLM
   - **Memory**: Saves with GPS location and timestamp
6. **Logging**: All actions logged to JSONL with minimal data retention

## Development

### Running in Simulation Mode
```bash
# Set in .env
SIMULATION_MODE=true

# Or via environment
SIMULATION_MODE=true docker-compose up --build
```

### Viewing Logs
```bash
# Container logs
docker logs -f tachyon-earshot

# Application logs (persistent)
tail -f logs/app.log

# Saved data
cat app_data/intents.jsonl
```

### Testing Components
```bash
# Test audio capture
docker exec -it tachyon-earshot python -c "from app.audio import test_audio; test_audio()"

# Test GPS
docker exec -it tachyon-earshot python -c "from app.gps_tachyon import test_gps; test_gps()"

# Test display
docker exec -it tachyon-earshot python -c "from app.display import test_display; test_display()"
```

## Troubleshooting

### No Audio Input
- Check USB microphone is connected: `ls /dev/snd/`
- Verify container has audio access: `docker exec -it tachyon-earshot ls /dev/snd/`

### GPS Not Working
- Ensure GPS antenna is connected to "GNSS" u.FL port
- Wait 30-60 seconds outdoors for initial satellite fix
- Check GNSS status: `particle-tachyon-ril-ctl gnss`

### E-ink Display Issues
- Verify SPI is enabled and display is connected
- Check permissions: Container runs as privileged for hardware access
- Set `DISPLAY_ENABLED=false` in `.env` to disable

### High CPU Usage
- Adjust `VAD_WINDOW_MS` and `UPDATE_INTERVAL` in `.env`
- Consider using smaller Vosk model
- Check `INTENT_THRESHOLD` - higher values reduce false positives

## Privacy & Security

- **No Audio Storage**: Raw audio is never written to disk
- **No Full Transcripts**: Only intent summaries are logged
- **Local Processing**: All core functionality works offline
- **Minimal Logging**: JSONL logs contain only essential metadata
- **Configurable Features**: All cloud integrations are optional

## License

[Specify your license here]

## Acknowledgments

- Particle Tachyon hardware platform
- Vosk speech recognition
- Silero VAD
- Sentence Transformers (MiniLM)
- Ollama for local LLM support
