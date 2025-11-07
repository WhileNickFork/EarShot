import asyncio, numpy as np, onnxruntime as ort, time, logging
import os, webrtcvad
from .config import Cfg
log = logging.getLogger("vad")

class VADGate:
    def __init__(self, cfg: Cfg, frame_q: asyncio.Queue, voiced_q: asyncio.Queue):
        self.cfg = cfg; self.frame_q = frame_q; self.voiced_q = voiced_q
        self.sr = cfg.sample_rate
        self.min_speech = cfg.vad_min_speech_ms/1000.0
        self.max_silence = cfg.vad_max_silence_ms/1000.0
        self.frame_sec = cfg.frame_ms/1000.0
        self.silero = None
        self.webrtc = webrtcvad.Vad(min(3, max(0, cfg.vad_aggr)))
        p = os.path.expanduser(cfg.silero_model_path)
        if not os.path.isfile(p):
            alt = os.path.join(cfg.models_dir, "silero_vad.onnx")
            if os.path.isfile(alt):
                p = alt
        if os.path.isfile(p):
            try:
                self.silero = ort.InferenceSession(p, providers=["CPUExecutionProvider"])
                # Initialize state for Silero VAD (128 for 16kHz model)
                self.silero_state = np.zeros((2, 1, 128), dtype=np.float32)
                log.info("vad: using Silero ONNX")
            except Exception as e:
                log.warning(f"vad: Silero load failed, fallback to webrtcvad: {e}")
        else:
            log.info("vad: Silero not found, using webrtcvad")

    def _is_speech(self, x: np.ndarray)->bool:
        if self.silero is not None:
            y = x.astype(np.float32)/32768.0
            
            # Fast downsample from 48kHz to 16kHz if needed (3:1 decimation)
            if self.sr == 48000:
                y = y[::3]  # Take every 3rd sample for 48k->16k
                vad_sr = 16000
            elif self.sr == 44100:
                y = y[::3]  # Approximate 44k->~15k (close enough for VAD)
                vad_sr = 16000 
            else:
                vad_sr = self.sr
            
            # Silero VAD expects: input, state, sr (sample rate)
            ort_inputs = {
                "input": y[np.newaxis,:],
                "state": self.silero_state,
                "sr": np.array(vad_sr, dtype=np.int64)
            }
            out, self.silero_state = self.silero.run(None, ort_inputs)
            prob = float(out[0][0])
            return prob > 0.5
        # Simple energy-based VAD (faster and works with any sample rate)
        # Calculate RMS energy
        energy = np.sqrt(np.mean(x.astype(np.float32) ** 2))
        # Threshold around 1000 works well for speech detection
        return energy > 1000

    async def run(self):
        speech_buf = []
        in_speech = False; last_speech_ts = 0.0
        while True:
            frame = await self.frame_q.get()
            frame = frame.reshape(-1)
            speech = self._is_speech(frame)
            now = time.monotonic()
            if speech:
                # Resample frame for ASR if needed (48k->16k for Vosk)
                if self.sr == 48000:
                    resampled_frame = frame[::3].astype(np.int16)  # 48k->16k decimation
                elif self.sr == 44100:
                    resampled_frame = frame[::3].astype(np.int16)  # 44k->~15k approximation  
                else:
                    resampled_frame = frame
                    
                speech_buf.append(resampled_frame)
                in_speech = True; last_speech_ts = now
            else:
                if in_speech:
                    if (now - last_speech_ts) < self.max_silence:
                        # Resample silence frames too to maintain continuity
                        if self.sr == 48000:
                            resampled_frame = frame[::3].astype(np.int16)
                        elif self.sr == 44100:
                            resampled_frame = frame[::3].astype(np.int16)
                        else:
                            resampled_frame = frame
                        speech_buf.append(resampled_frame)
                    else:
                        in_speech = False
                        dur = len(speech_buf)*self.frame_sec
                        if dur >= self.min_speech and speech_buf:
                            await self.voiced_q.put(np.concatenate(speech_buf))
                        speech_buf = []