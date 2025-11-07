# EarShot Quick Start Guide

## For Particle Tachyon SBC

### Prerequisites Check

```bash
# Verify you have:
# - USB microphone connected
# - Waveshare 7.5" e-Paper HAT connected
# - Local LLM running (Ollama recommended)
```

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libgpiod2 libgpiod-dev python3-libgpiod
```

### 2. Set Up Display Permissions

```bash
# Create groups
sudo groupadd -f spi
sudo groupadd -f gpio

# Add your user
sudo usermod -aG spi,gpio $USER

# Create udev rules
echo 'SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"' | sudo tee /etc/udev/rules.d/90-spi.rules
echo 'KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' | sudo tee /etc/udev/rules.d/90-gpio.rules

# Reload
sudo udevadm control --reload-rules
sudo modprobe -r spidev && sudo modprobe spidev

# LOG OUT AND BACK IN for group membership to take effect
```

### 3. Install Ollama (Local LLM)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (gemma2 2B recommended for Tachyon)
ollama pull gemma2:2b

# Verify it's running
curl http://localhost:11434/api/tags
```

### 4. Clone and Setup EarShot

```bash
cd ~/
git clone https://github.com/WhileNickFork/EarShot.git
cd EarShot
```

### 5. Create Python Environment

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env
```

Minimum required settings:
```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma2:2b
DISPLAY_ENABLED=true
SIMULATION_MODE=false
```

### 7. Download Models

Models will download automatically on first run, but you can pre-download:

```bash
# Vosk will auto-download (~40MB)
# Silero VAD - download manually if not present
mkdir -p models
# Place silero_vad.onnx in models/ directory

# Sentence transformer model
mkdir -p models/all-MiniLM-L6-v2
# Place model files in this directory
```

### 8. First Run

```bash
# Activate virtual environment
source .venv/bin/activate

# Run EarShot
python -m core2.main
```

**Expected output:**
```
2025-11-07T10:00:00Z INFO main :: earshot: starting...
2025-11-07T10:00:01Z INFO audio :: audio: found USB device: USB Audio Device
2025-11-07T10:00:01Z INFO audio :: audio: using sample rate 48000 Hz
2025-11-07T10:00:01Z INFO audio :: audio: stream started
2025-11-07T10:00:02Z INFO vad :: vad: using Silero ONNX model
2025-11-07T10:00:02Z INFO vad :: vad: started
2025-11-07T10:00:03Z INFO asr :: asr: loaded Vosk model from ...
2025-11-07T10:00:03Z INFO asr :: asr: started
2025-11-07T10:00:03Z INFO intent :: intent: classifier initialized
2025-11-07T10:00:03Z INFO intent :: intent: started
2025-11-07T10:00:03Z INFO display :: display: initialized
2025-11-07T10:00:04Z INFO gps :: gps: starting (simulation=False)
2025-11-07T10:00:04Z INFO main :: earshot: all components started
```

### 9. Test It

**Say something like:**
- "What is the capital of France?" (should get answer on display)
- "I need to remember to call mom tomorrow" (should get memory note)
- "I should clean the garage this weekend" (should get to-do item)

### 10. Stop

Press `Ctrl+C` - it will gracefully shut down and clear the display.

## Troubleshooting

### No audio input
```bash
# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Check if USB mic is detected
lsusb | grep -i audio
```

### Display not working
```bash
# Check permissions
ls -l /dev/spidev0.0
ls -l /dev/gpiochip*
groups  # Should include 'spi' and 'gpio'

# If not in groups, you need to log out and back in
```

### LLM connection failed
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check what models are available
ollama list

# Restart Ollama
sudo systemctl restart ollama
```

### Models not downloading
```bash
# Check internet connection
ping alphacephei.com

# Check disk space
df -h

# Manually download Vosk model
cd ~/.earshot/.cache/vosk
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

### Check logs
```bash
# View live logs
tail -f ~/.earshot/logs/earshot.log

# Search for errors
grep ERROR ~/.earshot/logs/earshot.log
```

## Development Mode

To test without hardware:

```bash
# Edit .env
SIMULATION_MODE=true
DISPLAY_ENABLED=false

# Run
python -m core2.main
```

This will generate silent audio and skip hardware initialization.

## Running as Service (Optional)

Create `/etc/systemd/system/earshot.service`:

```ini
[Unit]
Description=EarShot Ambient Speech Assistant
After=network.target ollama.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/EarShot
Environment="PATH=/home/your-username/EarShot/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/your-username/EarShot/.venv/bin/python -m core2.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable earshot
sudo systemctl start earshot
sudo systemctl status earshot
```

## Success Criteria

✅ Audio capture starts without errors
✅ VAD detects speech segments
✅ ASR transcribes your speech
✅ Intent classification identifies question/todo/memory
✅ LLM responds appropriately
✅ E-ink display shows the response

## Getting Help

Check logs, verify configuration, ensure all services running.

---

**You're all set! EarShot is now listening and ready to help.** 🎯
