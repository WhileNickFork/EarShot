"""Voice Activity Detection (VAD) to filter speech from silence."""
import asyncio
import logging
import time
import os
import numpy as np
import onnxruntime as ort

from core2.config import Config

log = logging.getLogger("vad")


class VADProcessor:
    """Detects voice activity and gates audio to only pass speech segments."""
    
    def __init__(self, cfg: Config, frame_queue: asyncio.Queue, speech_queue: asyncio.Queue):
        self.cfg = cfg
        self.frame_queue = frame_queue
        self.speech_queue = speech_queue
        self.sample_rate = cfg.sample_rate
        self.frame_sec = cfg.frame_ms / 1000.0
        self.min_speech = cfg.vad_min_speech_ms / 1000.0
        self.max_silence = cfg.vad_max_silence_ms / 1000.0
        
        # Try to load Silero VAD model
        self.silero = None
        self.silero_state = None
        model_path = os.path.expanduser(cfg.silero_model_path)
        
        if os.path.isfile(model_path):
            try:
                self.silero = ort.InferenceSession(
                    model_path, 
                    providers=["CPUExecutionProvider"]
                )
                self.silero_state = np.zeros((2, 1, 128), dtype=np.float32)
                log.info("vad: using Silero ONNX model")
            except Exception as e:
                log.warning(f"vad: Silero load failed, using energy-based fallback: {e}")
        else:
            log.info("vad: Silero model not found, using energy-based VAD")
    
    def _is_speech(self, frame: np.ndarray) -> bool:
        """Check if audio frame contains speech."""
        if self.silero is not None:
            # Normalize to float32 [-1, 1]
            y = frame.astype(np.float32) / 32768.0
            
            # Silero expects 16kHz - resample if needed
            if self.sample_rate == 48000:
                y = y[::3]  # 48k -> 16k decimation
                vad_sr = 16000
            elif self.sample_rate == 44100:
                y = y[::3]  # 44k -> ~15k approximation
                vad_sr = 16000
            else:
                vad_sr = self.sample_rate
            
            # Run Silero VAD
            inputs = {
                "input": y[np.newaxis, :],
                "state": self.silero_state,
                "sr": np.array(vad_sr, dtype=np.int64)
            }
            out, self.silero_state = self.silero.run(None, inputs)
            prob = float(out[0][0])
            return prob > 0.5
        
        # Fallback: simple energy-based VAD
        energy = np.sqrt(np.mean(frame.astype(np.float32) ** 2))
        return energy > 1000
    
    async def run(self):
        """Main VAD processing loop."""
        speech_buffer = []
        in_speech = False
        last_speech_time = 0.0
        
        log.info("vad: started")
        
        while True:
            frame = await self.frame_queue.get()
            frame = frame.reshape(-1)
            
            is_speech = self._is_speech(frame)
            now = time.monotonic()
            
            if is_speech:
                # Resample to 16kHz for ASR if needed
                if self.sample_rate == 48000:
                    resampled = frame[::3].astype(np.int16)
                elif self.sample_rate == 44100:
                    resampled = frame[::3].astype(np.int16)
                else:
                    resampled = frame
                
                speech_buffer.append(resampled)
                in_speech = True
                last_speech_time = now
                
            else:
                if in_speech:
                    silence_duration = now - last_speech_time
                    
                    if silence_duration < self.max_silence:
                        # Keep buffering during short pauses
                        if self.sample_rate == 48000:
                            resampled = frame[::3].astype(np.int16)
                        elif self.sample_rate == 44100:
                            resampled = frame[::3].astype(np.int16)
                        else:
                            resampled = frame
                        speech_buffer.append(resampled)
                    else:
                        # End of speech segment
                        in_speech = False
                        duration = len(speech_buffer) * self.frame_sec
                        
                        if duration >= self.min_speech and speech_buffer:
                            audio = np.concatenate(speech_buffer)
                            await self.speech_queue.put(audio)
                            log.debug(f"vad: speech segment {duration:.2f}s")
                        
                        speech_buffer = []
