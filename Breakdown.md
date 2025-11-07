# EarShot Core & Location Breakdown

This document captures the current state of the `core/` and `location/` modules after the move away from the Docker deployment. Each subsection covers the role of the file, whether it is expected to work as-is, notable issues or risks, and recommendations for next steps.

## Highlights at a Glance

- Most pipeline components (audio → VAD → ASR → intent → events) still reflect the original Docker assumptions but can run locally with proper dependencies (`sounddevice`, `webrtcvad`, `onnxruntime`, `vosk`, `httpx`, `transformers`).
- File-system paths were hard-coded to `/opt/...`; these are now routed through configurable, user-writable directories (`~/.earshot`, project `models/`, and `~/.cache/earshot`).
- GPS utilities remain functional for Tachyon hardware via `particle-tachyon-ril-ctl`; D-Bus fallback is stubbed.
- Display integration now uses an async wrapper around the `eink` module and degrades gracefully when the hardware stack is absent.
- Several modules still require follow-up work (e.g., display UX, richer GNSS data, broader intent prototypes, health endpoints beyond `/health`).

---

## Module-by-Module Details

### `core/__init__.py`
- **Purpose:** Package marker; no runtime logic.
- **Operational state:** ✅ Works (empty file).
- **Notes:** None.

### `core/audio.py`
- **Purpose:** Capture audio frames from a USB microphone (or generate silence in simulation mode) and place them on an asyncio queue.
- **Expected to work?** ✅ With caveats.
- **Current state:**
  - Automatically searches for USB input devices and probes a preferred sample rate (starting at 16 kHz and falling back to 48 kHz/44.1 kHz/etc.).
  - Streams 16-bit mono audio to the `frame_q` queue; simulation mode injects silent frames.
- **Risks / Follow-ups:**
  - If no USB device name contains "usb", the default system microphone is used; consider exposing device selection via config.
  - No resampling occurs here—VAD handles down-sampling; that coupling should be documented.

### `core/asr.py`
- **Purpose:** Consume voiced audio chunks and transcribe them with Vosk.
- **Expected to work?** ⚠️ Needs dependencies and first-run model download.
- **Current state:**
  - Downloads the small English Vosk model into the configurable cache directory (default `~/.cache/earshot/vosk/en-us-0.22`).
  - Uses a single `KaldiRecognizer` with `FinalResult()` per voiced chunk; this suits utterance-sized buffers produced by the VAD gate.
- **Risks / Follow-ups:**
  - Requires network access on first run to fetch the Vosk zip. If offline deployment is required, stage the model manually in the cache and set `VOSK_MODEL_CACHE`.
  - Dependency on `vosk` Python wheel; ensure it is present in `requirements.txt`.
  - Consider handling partial hypotheses (via `PartialResult`) if you need streaming UI feedback.

### `core/config.py`
- **Purpose:** Declarative configuration using environment variables.
- **Expected to work?** ✅
- **Current state:**
  - Introduces `data_dir`, `models_dir`, `cache_dir`, `vosk_model_cache`, and `silero_model_path` so runtime assets default to user-writable locations instead of `/opt/...`.
  - Existing settings (audio/VAD/intent/LLM/TickTick/display/logging) continue to use the `env` helper for overrides.
- **Risks / Follow-ups:**
  - Verify that any deployment scripts set the new environment variables if a non-default layout is required.
  - Consider migrating to `pydantic.BaseSettings` for richer validation and `.env` loading.

### `core/display.py`
- **Purpose:** Async wrapper around the `eink` hardware helper with graceful degradation when hardware is absent.
- **Expected to work?** ⚠️ Depends on hardware and Adafruit stack.
- **Current state:**
  - Lazily spins up the `EInkDisplay` inside a single-thread executor during `init()`.
  - `show_text()` truncates the body to `display_max_chars`, renders a slide, and refreshes the panel.
  - `clear_and_sleep()` wipes the panel and calls `shutdown()` before tearing down the executor.
  - When the display is disabled or initialisation fails, all methods turn into no-ops to keep the pipeline alive.
- **Risks / Follow-ups:**
  - Hardware init errors are logged but swallowed; consider surfacing them via health metrics if visibility is needed.
  - A future enhancement could reuse the existing image buffer between updates to avoid flicker.

### `core/events.py`
- **Purpose:** Orchestrate downstream actions for classified utterances (memory/todo/question).
- **Expected to work?** ⚠️ Requires LLM endpoints and optional TickTick credentials.
- **Current state:**
  - Persists summaries into `~/.earshot/events/*.jsonl` using UTF-8 encoding.
  - Uses `LLM` helpers for summarisation/Q&A and sends responses to the display when available.
  - TickTick integration is optional; import failures or missing credentials now log a warning rather than crash.
- **Risks / Follow-ups:**
  - `gps.current()` only returns lat/lon; consider storing additional GNSS metadata for richer memories.
  - Errors from downstream components are caught and logged, but no retry/backoff strategy is in place.
  - Health/metrics around queue depth or processing latency would be useful.

### `core/intent.py`
- **Purpose:** Classify ASR text into intent labels and emit structured events with surrounding context.
- **Expected to work?** ✅ Assuming embeddings model is present.
- **Current state:**
  - Uses a semaphore to limit concurrent LLM workloads.
  - `RollingBuffer` captures context surrounding detected utterances (`rolling_pre_sec`, `rolling_post_sec`).
- **Risks / Follow-ups:**
  - `IntentClassifier` is invoked for every ASR text; consider debouncing extremely short transcriptions.
  - Add metrics to monitor score distributions and threshold calibration.

### `core/llm.py`
- **Purpose:** Thin async client for local and remote LLM endpoints.
- **Expected to work?** ⚠️ Requires HTTP endpoints (`/chat/completions`) following the OpenAI-compatible schema.
- **Current state:**
  - Summary and Q&A prompts are maintained in the `SYSTEMS` dict.
  - Dual-mode Q&A requests the remote model in parallel when enabled.
- **Risks / Follow-ups:**
  - Remote model name is hard-coded as `gpt-remote`; expose as config if different providers are used.
  - No guard against runaway latency; consider wrapping requests in `asyncio.wait_for` for stricter control.

### `core/logging_setup.py`
- **Purpose:** Configure root logging to stdout and a rotating file.
- **Expected to work?** ✅
- **Current state:**
  - Ensures the custom log directory exists and attaches stream/file handlers with ISO timestamps.
- **Risks / Follow-ups:**
  - No log rotation; long-running deployments may want `RotatingFileHandler`.

### `core/main.py`
- **Purpose:** Bootstrap the entire assistant pipeline and expose a basic `/health` endpoint.
- **Expected to work?** ⚠️ Integration-heavy.
- **Current state:**
  - Loads `.env`, builds queues, instantiates GPS/display/audio/VAD/ASR/intent/event components, then gathers them under `asyncio.run`.
  - Health server runs on port 8088 in a background thread.
  - On exit, clears the display before sleeping the panel.
- **Risks / Follow-ups:**
  - Missing structured shutdown for other components (audio stream, GPS poller); consider cancellation handling.
  - If GPS or display initialisation fails, the pipeline continues but logs warnings; decide whether to treat these as fatal.

### `core/nlp_intent.py`
- **Purpose:** Load MiniLM embeddings and classify text via cosine similarity against prototypes.
- **Expected to work?** ⚠️ Requires ONNX model + tokenizer available locally.
- **Current state:**
  - Handles the absence of `token_type_ids` gracefully by creating zero arrays.
  - Default prototypes cover `memory`, `todo`, `question`, and `ignore` intents.
- **Risks / Follow-ups:**
  - Extend or fine-tune prototypes to better capture your speech patterns.
  - Warm-up of ONNX session can take ~100 ms on first run; consider pre-loading during startup.

### `core/rolling.py`
- **Purpose:** Maintain a time-windowed buffer of ASR text for contextual summaries.
- **Expected to work?** ✅
- **Current state:**
  - Uses a deque to purge entries older than `pre+post+60` seconds when new text arrives.
- **Risks / Follow-ups:**
  - If ASR produces timestamps far apart, you may want to trim more aggressively.

### `core/vad.py`
- **Purpose:** Gate audio frames based on speech activity, optionally using Silero VAD.
- **Expected to work?** ⚠️ Requires `onnxruntime`/`webrtcvad` and tuned thresholds.
- **Current state:**
  - Prefers Silero ONNX when the model is present; falls back to RMS-based heuristic otherwise.
  - Down-samples 48 kHz / 44.1 kHz audio to ~16 kHz for ASR.
- **Risks / Follow-ups:**
  - Consider a higher-quality resampler for 44.1 kHz input (current `x[::3]` approximation yields ~14.7 kHz).
  - Track energy thresholds per environment to limit false positives.

### `location/gnss_utils.py`
- **Purpose:** Helper functions for querying GNSS data via `particle-tachyon-ril-ctl` with a D-Bus fallback.
- **Expected to work?** ⚠️ Primary method works on hardware; fallback is intentionally unimplemented.
- **Current state:**
  - `query_gnss_ril_ctl()` parses colon-delimited output into a dict with numeric coercion.
  - `query_gnss_dbus()` currently raises `GNSSQueryError("D-Bus parser not implemented")`.
  - `query_gnss_with_fallback()` logs warnings and returns `None` if both methods fail.
- **Risks / Follow-ups:**
  - Implement proper D-Bus parsing or remove the placeholder to avoid confusion.
  - Add unit tests with fixture outputs to lock down parsing logic.

### `location/gps_tachyon.py`
- **Purpose:** Async GPS poller that maintains the latest fix for downstream consumers.
- **Expected to work?** ⚠️ Works on hardware; simulation mode returns Madison, WI jitter.
- **Current state:**
  - `_query_ril()` wraps the `particle-tachyon-ril-ctl gnss` command and normalises output.
  - `run()` loops forever, updating `self.last` when a valid fix is present; `current()` returns the last lat/lon dict.
- **Risks / Follow-ups:**
  - Surface more fields (altitude, speed, fix type) for richer context.
  - Introduce exponential backoff if the subprocess fails repeatedly.
  - Consider graceful cancellation via an `asyncio.Event` on shutdown.

---

## Outstanding Actions & Recommendations

1. **Dependencies audit:** Ensure `requirements.txt` (or equivalent) includes `vosk`, `onnxruntime`, `webrtcvad`, `sounddevice`, `transformers`, `httpx`, and `pydantic` so local installs succeed.
2. **Model staging:** Document how to place ONNX models locally when the device is offline; defaults now point to `models/` in the repo or `~/.cache/earshot`.
3. **Display UX:** Validate the new async wrapper on-device and confirm the truncation logic matches readability expectations on the 7.5" display.
4. **GNSS fallback:** Decide whether to implement or remove the D-Bus stub to avoid misleading warnings.
5. **Graceful shutdown:** Expand shutdown handling (audio/GPS tasks) so Ctrl+C leads to a clean exit without hanging coroutines.
6. **Monitoring:** Add metrics (queue depth, inference latency, success/failure counters) to aid regression tracking during the ongoing refactor.

This breakdown should serve as the starting point for prioritising remaining work as you stabilise the non-Docker deployment. Let me know when you want to dive deeper into any specific component.
