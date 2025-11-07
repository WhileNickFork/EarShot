# EarShot 🎯

**Privacy-focused ambient speech assistant for Particle Tachyon SBC**

EarShot listens to ambient speech, transcribes it locally, and uses a local LLM to intelligently identify opportunities to help—answering questions, capturing memories, or extracting to-do items. All information is displayed on an e-ink screen for privacy and efficiency.

## 🎯 Core Philosophy

- **Privacy First**: All processing happens locally. No cloud transcription. Transcripts are never stored—only kept in RAM for context.
- **Efficiency**: Multi-stage pipeline with voice activity detection to minimize unnecessary processing.
- **Local LLM**: Uses OpenAI-compatible local endpoint (Ollama, LM Studio, etc.)
- **Minimal Footprint**: Optimized for Particle Tachyon SBC with ARM architecture.

## 📋 Features

- **Ambient Listening**: Background audio capture from USB microphone
- **Voice Activity Detection (VAD)**: Silero ONNX model with energy-based fallback
- **Speech Recognition**: Vosk offline ASR (no internet required)
- **Intent Classification**: Sentence embeddings to identify actionable intents
- **LLM Processing**: Local LLM summarizes memories, extracts todos, answers questions
- **E-ink Display**: Privacy-friendly visual feedback on Waveshare 7.5" display
- **GPS Context**: Location and time metadata from Tachyon GNSS

## 🏗️ Architecture

```
Audio → VAD → ASR → Intent → LLM → Display
  ↓      ↓      ↓       ↓       ↓       ↓
 USB   Filter  Vosk  Classify Local  E-ink
 Mic   Speech        3 Types  Ollama Screen
```

### Pipeline Components

1. **Audio Capture** (`audio.py`): Captures 16kHz audio from USB mic, with automatic sample rate detection
2. **VAD Processor** (`vad.py`): Filters silence, only passes speech segments using Silero VAD
3. **ASR Worker** (`asr.py`): Transcribes speech using Vosk (offline, local model)
4. **Intent Router** (`intent.py`): Classifies transcripts into memory/todo/question/ignore using sentence embeddings
5. **Event Processor** (`events.py`): Sends actionable intents to LLM and displays results
6. **Display** (`display.py`): Shows messages on e-ink screen via `eink.EInkDisplay.draw_slide()`

### Rolling Context Buffer

Maintains last ~25 seconds of speech in RAM only (10s pre + 15s post) to provide context for LLM without storing transcripts permanently.

## 📦 Project Structure

```
EarShot/
├── core2/              # Main application code (cleaned up)
│   ├── audio.py        # Audio capture from USB mic
│   ├── vad.py          # Voice activity detection
│   ├── asr.py          # Speech recognition (Vosk)
│   ├── intent.py       # Intent classification + rolling buffer
│   ├── llm.py          # LLM client (OpenAI-compatible)
│   ├── events.py       # Event processing & display
│   ├── display.py      # E-ink display wrapper
│   ├── config.py       # Configuration management
│   ├── logging_setup.py # Logging configuration
│   └── main.py         # Application entry point
├── eink/               # E-ink display drivers (do not modify)
│   ├── eink.py         # Display hardware interface
│   └── README.md       # Display setup instructions
├── location/           # GPS/GNSS integration (do not modify)
│   └── gps_tachyon.py  # Tachyon GNSS interface
├── models/             # AI models (downloaded on first run)
│   ├── silero_vad.onnx # Voice activity detection
│   └── all-MiniLM-L6-v2/ # Sentence embeddings
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🚀 Getting Started

### Prerequisites

- Particle Tachyon SBC (Ubuntu 20.04, aarch64)
- USB microphone connected
- Waveshare 7.5" e-Paper HAT (800×480)
- Local LLM server (Ollama, LM Studio, etc.)

### Installation

1. **Clone repository**
   ```bash
   cd ~/
   git clone https://github.com/WhileNickFork/EarShot.git
   cd EarShot
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv --system-site-packages .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure environment** (create `.env` file)
   ```bash
   # LLM Configuration (required)
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_MODEL=gemma2:2b
   
   # Optional: Override defaults
   SAMPLE_RATE=16000
   DISPLAY_ENABLED=true
   SIMULATION_MODE=false
   LOG_LEVEL=INFO
   ```

4. **Set up display** (see `eink/README.md` for detailed instructions)
   ```bash
   sudo apt-get install -y python3-venv libgpiod2 libgpiod-dev python3-libgpiod
   sudo usermod -aG spi,gpio $USER
   # Configure udev rules per eink/README.md
   ```

5. **Download models** (happens automatically on first run)
   - Vosk ASR model (~40MB)
   - Silero VAD model (place in `models/silero_vad.onnx`)
   - Sentence transformer (place in `models/all-MiniLM-L6-v2/`)

### Running

```bash
# From project root
python -m core2.main
```

The application will:
1. Initialize audio capture from USB mic
2. Start VAD filtering
3. Begin transcribing speech
4. Classify intents and generate responses
5. Display helpful information on e-ink screen

**Stop**: Press `Ctrl+C`

## 🔧 Configuration

All configuration via environment variables (see `.env` or set in shell):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible LLM endpoint |
| `LLM_MODEL` | `gemma2:2b` | Model name for LLM |
| `LLM_TIMEOUT_SEC` | `10` | LLM request timeout |
| `SAMPLE_RATE` | `16000` | Audio sample rate (auto-detected) |
| `DISPLAY_ENABLED` | `true` | Enable e-ink display |
| `DISPLAY_MAX_CHARS` | `220` | Max characters on screen |
| `CONTEXT_PRE_SEC` | `10` | Context window before trigger |
| `CONTEXT_POST_SEC` | `15` | Context window after trigger |
| `INTENT_THRESHOLD` | `0.28` | Intent classification threshold |
| `SIMULATION_MODE` | `false` | Run without hardware (dev mode) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## 🧠 Intent Types

The system classifies speech into four categories:

1. **Memory**: Personal notes, observations, diary-like statements
   - *"I need to remember that Bob's birthday is next week"*
   - **Action**: Summarize and display on screen

2. **Todo**: Actionable tasks
   - *"I should call the dentist tomorrow"*
   - **Action**: Extract task, display, optionally send to TickTick

3. **Question**: Direct questions seeking answers
   - *"What's the capital of France?"*
   - **Action**: Query LLM, display answer

4. **Ignore**: Small talk, non-actionable speech
   - *"It's a nice day outside"*
   - **Action**: No action taken

## 📊 Data Storage

**Privacy by Design:**
- Transcripts are **never** stored to disk
- Only **RAM-based rolling buffer** for context (~25 seconds)
- Minimal event logs saved (JSONL format):
  - `~/.earshot/events/memory.jsonl` - Summarized memories only
  - `~/.earshot/events/todos.jsonl` - Extracted tasks only
  - `~/.earshot/events/questions.jsonl` - Q&A pairs only

These logs contain **processed outputs** (summaries, tasks, answers), not raw transcripts.

## 🔌 Hardware Details

### Audio
- Automatically detects USB audio devices
- Supports 16kHz, 44.1kHz, 48kHz (auto-resamples for ASR)
- 20ms frame size

### Display
- Waveshare 7.5" e-Paper HAT (UC8179 driver)
- 800×480 monochrome
- Uses `eink.EInkDisplay.draw_slide(title, body)` method
- See `eink/README.md` for wiring and setup

### GPS
- Tachyon RIL interface (`particle-tachyon-ril-ctl gnss`)
- Simulation mode available for development
- Provides location context for events

## 🛠️ Development

### Simulation Mode

For development without hardware:

```bash
export SIMULATION_MODE=true
export DISPLAY_ENABLED=false
python -m core2.main
```

This generates silent audio frames and skips hardware initialization.

### Testing Changes

1. Edit files in `core2/`
2. Run: `python -m core2.main`
3. Monitor logs: `tail -f ~/.earshot/logs/earshot.log`

### Adding Features

- **New intent types**: Update `INTENT_PROTOTYPES` in `intent.py`
- **LLM prompts**: Modify `SYSTEM_PROMPTS` in `llm.py`
- **Display layout**: Changes go in `eink/eink.py` (external module)

## 📝 Logging

Logs written to:
- **Console**: Real-time output
- **File**: `~/.earshot/logs/earshot.log`

Log format: `TIMESTAMP LEVEL MODULE :: MESSAGE`

Example:
```
2025-11-07T10:30:15Z INFO audio :: audio: stream started
2025-11-07T10:30:20Z INFO asr :: asr: 'what time is it'
2025-11-07T10:30:20Z INFO intent :: intent: 'what time is it' -> question (0.875)
2025-11-07T10:30:21Z INFO events :: events: question -> 'It is 10:30 AM'
```

## 🚧 Future Enhancements

- **TickTick Integration**: Automatic task creation (code exists in `tasks/ticktick.py`)
- **Remote LLM Fallback**: Optional cloud LLM for complex queries
- **Multi-language Support**: Additional Vosk models
- **Speaker Diarization**: Identify different speakers
- **Wake Word**: Trigger on specific phrase

## 🙏 Credits

- **Vosk**: Offline speech recognition
- **Silero VAD**: Voice activity detection
- **Sentence Transformers**: Intent classification
- **Adafruit CircuitPython**: E-ink display drivers
- **Particle Tachyon**: SBC hardware platform

## 📄 License

MIT License - See repository for details

---

**Built with privacy, efficiency, and local-first principles** 🔒
