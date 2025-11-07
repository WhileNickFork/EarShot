"""Audio capture from USB microphone."""
import asyncio
import logging
import numpy as np
import sounddevice as sd

from core2.config import Config

log = logging.getLogger("audio")


class AudioCapture:
    """Captures audio frames from USB microphone and pushes to queue."""
    
    def __init__(self, cfg: Config, frame_queue: asyncio.Queue):
        self.cfg = cfg
        self.frame_queue = frame_queue
        self.blocksize = int(cfg.sample_rate * (cfg.frame_ms / 1000.0))
        self.stream = None
        self.actual_sample_rate = cfg.sample_rate
    
    async def start(self):
        """Start audio capture (simulation mode or real USB device)."""
        if self.cfg.simulation_mode:
            log.info("audio: simulation mode - generating silence")
            asyncio.create_task(self._simulate_audio())
            return
        
        # Find USB audio device on Tachyon
        devices = sd.query_devices()
        usb_device = None
        
        for i, device in enumerate(devices):
            if device['name'] and 'usb' in device['name'].lower() and device['max_input_channels'] > 0:
                usb_device = i
                log.info(f"audio: found USB device: {device['name']}")
                
                # Try different sample rates (Tachyon may not support 16kHz)
                for rate in [16000, 48000, 44100, 22050, 8000]:
                    try:
                        sd.check_input_settings(device=usb_device, samplerate=rate, channels=1, dtype='int16')
                        self.actual_sample_rate = rate
                        log.info(f"audio: using sample rate {rate} Hz")
                        break
                    except Exception:
                        continue
                break
        
        if usb_device is None:
            log.warning("audio: no USB device found, using default")
        
        # Adjust blocksize for actual sample rate
        if self.actual_sample_rate != self.cfg.sample_rate:
            self.blocksize = int(self.actual_sample_rate * (self.cfg.frame_ms / 1000.0))
        
        # Setup callback to push frames to queue
        loop = asyncio.get_running_loop()
        
        def callback(indata, frames, time, status):
            if status:
                log.warning(f"audio: {status}")
            try:
                asyncio.run_coroutine_threadsafe(
                    self.frame_queue.put(indata.copy()), loop
                )
            except Exception as e:
                log.error(f"audio: callback error: {e}")
        
        # Start the audio stream
        self.stream = sd.InputStream(
            device=usb_device,
            samplerate=self.actual_sample_rate,
            channels=1,
            dtype='int16',
            blocksize=self.blocksize,
            callback=callback
        )
        self.stream.start()
        log.info("audio: stream started")
    
    async def _simulate_audio(self):
        """Generate silence frames in simulation mode."""
        while True:
            silence = np.zeros(self.blocksize, dtype='int16')
            await self.frame_queue.put(silence)
            await asyncio.sleep(self.cfg.frame_ms / 1000.0)
    
    async def stop(self):
        """Stop audio capture."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            log.info("audio: stream stopped")
