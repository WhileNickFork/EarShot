"""Configuration management for EarShot."""
import os
from pathlib import Path
from pydantic import BaseModel


def env(name: str, default=None, cast=str):
    """Helper to read and cast environment variables."""
    v = os.getenv(name, default)
    if cast is bool:
        return str(v).lower() in ("1", "true", "yes", "on")
    return cast(v) if v is not None else v


_HOME_DIR = Path(os.getenv("EARSHOT_HOME", Path.home() / ".earshot")).expanduser()
_MODELS_DIR = Path(os.getenv("EARSHOT_MODELS_DIR", Path.cwd() / "models")).expanduser()


class Config(BaseModel):
    """Core configuration for EarShot application."""
    
    # Directories
    data_dir: str = env("EARSHOT_HOME", str(_HOME_DIR))
    models_dir: str = env("EARSHOT_MODELS_DIR", str(_MODELS_DIR))
    log_dir: str = env("LOG_DIR", str(_HOME_DIR / "logs"))
    
    # Audio settings
    sample_rate: int = env("SAMPLE_RATE", 16000, int)
    frame_ms: int = env("FRAME_MS", 20, int)
    
    # VAD (Voice Activity Detection) settings
    vad_min_speech_ms: int = env("VAD_MIN_SPEECH_MS", 250, int)
    vad_max_silence_ms: int = env("VAD_MAX_SILENCE_MS", 400, int)
    silero_model_path: str = env("SILERO_MODEL_PATH", str(_MODELS_DIR / "silero_vad.onnx"))
    
    # ASR (Automatic Speech Recognition) settings
    vosk_model_cache: str = env("VOSK_MODEL_CACHE", str(_HOME_DIR / ".cache" / "vosk"))
    vosk_model_name: str = env("VOSK_MODEL", "vosk-model-small-en-us-0.15")
    
    # Rolling buffer (for context window)
    context_pre_sec: int = env("CONTEXT_PRE_SEC", 10, int)
    context_post_sec: int = env("CONTEXT_POST_SEC", 15, int)
    
    # Intent classification
    intent_model_path: str = env("INTENT_MODEL_PATH", str(_MODELS_DIR / "all-MiniLM-L6-v2"))
    intent_threshold: float = env("INTENT_THRESHOLD", 0.28, float)
    
    # LLM settings (OpenAI-compatible endpoint)
    llm_base_url: str = env("LLM_BASE_URL", "http://localhost:11434/v1")
    llm_model: str = env("LLM_MODEL", "gemma2:2b")
    llm_timeout_sec: int = env("LLM_TIMEOUT_SEC", 10, int)
    
    # Display settings
    display_enabled: bool = env("DISPLAY_ENABLED", True, bool)
    display_max_chars: int = env("DISPLAY_MAX_CHARS", 220, int)
    
    # GPS/Location settings
    gps_poll_sec: int = env("GPS_POLL_SEC", 2, int)
    simulation_mode: bool = env("SIMULATION_MODE", False, bool)
    
    # Logging
    log_level: str = env("LOG_LEVEL", "INFO")
