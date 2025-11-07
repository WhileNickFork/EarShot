from pydantic import BaseModel
import os
from pathlib import Path

def env(name, default=None, cast=str):
    v = os.getenv(name, default)
    if cast is bool:
        return str(v).lower() in ("1","true","yes","on")
    return cast(v) if v is not None else v

_HOME_DIR = Path(os.getenv("EARSHOT_HOME", Path.home() / ".earshot")).expanduser()
_MODELS_DIR = Path(os.getenv("EARSHOT_MODELS_DIR", Path.cwd() / "models")).expanduser()
_CACHE_DIR = Path(os.getenv("EARSHOT_CACHE_DIR", Path.home() / ".cache" / "earshot")).expanduser()

class Cfg(BaseModel):
    # filesystem/layout
    data_dir: str = env("EARSHOT_HOME", str(_HOME_DIR))
    models_dir: str = env("EARSHOT_MODELS_DIR", str(_MODELS_DIR))
    cache_dir: str = env("EARSHOT_CACHE_DIR", str(_CACHE_DIR))
    vosk_model_cache: str = env("VOSK_MODEL_CACHE", str(_CACHE_DIR / "vosk"))
    silero_model_path: str = env("SILERO_MODEL_PATH", str(_MODELS_DIR / "silero_vad.onnx"))

    # audio / vad
    sample_rate: int = env("SAMPLE_RATE", 16000, int)
    frame_ms: int = env("FRAME_MS", 20, int)
    vad_min_speech_ms: int = env("VAD_MIN_SPEECH_MS", 250, int)
    vad_max_silence_ms: int = env("VAD_MAX_SILENCE_MS", 400, int)
    vad_aggr: int = env("VAD_AGGRESSIVENESS", 2, int)

    # rolling buffer
    rolling_pre_sec: int = env("ROLLING_PRE_SEC", 10, int)
    rolling_post_sec: int = env("ROLLING_POST_SEC", 15, int)
    max_parallel_intent: int = env("MAX_PARALLEL_INTENT", 2, int)

    # asr/llms
    asr_engine: str = env("ASR_ENGINE", "vosk")
    vosk_model: str = env("VOSK_MODEL", "en-us-0.22")
    llm_local_base: str = env("LLM_LOCAL_BASE_URL", "http://ollama:11434/v1")
    llm_local_model: str = env("LLM_LOCAL_MODEL", "gemma3:270m")
    llm_timeout_ms: int = env("LLM_TIMEOUT_MS", 1200, int)
    llm_remote_enabled: bool = env("LLM_REMOTE_ENABLED", False, bool)
    llm_remote_base: str = env("LLM_REMOTE_BASE_URL", "")
    llm_remote_timeout_ms: int = env("LLM_REMOTE_TIMEOUT_MS", 8000, int)

    # display
    display_enabled: bool = env("DISPLAY_ENABLED", True, bool)
    epd_driver: str = env("EPD_DRIVER", "epd7in5_V2")
    display_max_chars: int = env("DISPLAY_MAX_CHARS", 220, int)

    # gnss/tachyon
    gps_backend: str = env("GPS_BACKEND", "tachyon-ril")
    gps_poll_sec: int = env("GPS_POLL_SEC", 2, int)
    simulation_mode: bool = env("SIMULATION_MODE", False, bool)
    timezone: str = env("TIMEZONE", "America/New_York")

    # intent
    intent_model_path: str = env("INTENT_MODEL_PATH", str(_MODELS_DIR / "all-MiniLM-L6-v2"))
    intent_threshold: float = env("INTENT_THRESHOLD", 0.28, float)

    # ticktick
    tt_base: str = env("TICKTICK_BASE", "https://api.ticktick.com")
    tt_client_id: str = env("TICKTICK_CLIENT_ID", "")
    tt_client_secret: str = env("TICKTICK_CLIENT_SECRET", "")
    tt_access: str = env("TICKTICK_ACCESS_TOKEN", "")
    tt_refresh: str = env("TICKTICK_REFRESH_TOKEN", "")
    tt_project_name: str = env("TICKTICK_PROJECT_NAME", "Inbox")

    # logging
    log_level: str = env("LOG_LEVEL", "INFO")
    log_dir: str = env("LOG_DIR", str(_HOME_DIR / "logs"))