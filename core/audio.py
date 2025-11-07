import asyncio, sounddevice as sd, numpy as np, logging
from core.config import Cfg
log = logging.getLogger("audio")

class AudioCapture:
    def __init__(self, cfg: Cfg, frame_q: asyncio.Queue):
        self.cfg = cfg; self.frame_q = frame_q
        self.blocksize = int(cfg.sample_rate * (cfg.frame_ms/1000.0))
        self.stream = None

    async def start(self):
        if self.cfg.simulation_mode:
            log.info("audio: simulation mode - generating silence")
            asyncio.create_task(self._sim_audio())
            return
            
        loop = asyncio.get_running_loop()
        def cb(indata, frames, time, status):
            if status:
                log.warning(f"audio status: {status}")
            try:
                asyncio.run_coroutine_threadsafe(self.frame_q.put(indata.copy()), loop)
            except Exception as e:
                log.error(f"audio cb error: {e}")
        # Try to find USB audio device
        devices = sd.query_devices()
        usb_device = None
        sample_rate = self.cfg.sample_rate
        
        for i, device in enumerate(devices):
            if device['name'] and 'usb' in device['name'].lower() and device['max_input_channels'] > 0:
                usb_device = i
                log.info(f"audio: found USB device: {device['name']}")
                
                # Test different sample rates if 16kHz doesn't work
                supported_rates = [16000, 48000, 44100, 22050, 8000]
                for rate in supported_rates:
                    try:
                        sd.check_input_settings(device=usb_device, samplerate=rate, channels=1, dtype='int16')
                        sample_rate = rate
                        log.info(f"audio: using sample rate {rate} Hz")
                        break
                    except Exception as e:
                        continue
                break
        
        # Update blocksize based on actual sample rate
        if sample_rate != self.cfg.sample_rate:
            self.blocksize = int(sample_rate * (self.cfg.frame_ms/1000.0))
            log.info(f"audio: adjusted blocksize to {self.blocksize} for {sample_rate}Hz")
        
        self.stream = sd.InputStream(device=usb_device, samplerate=sample_rate, channels=1, dtype='int16',
                                     blocksize=self.blocksize, callback=cb)
        self.stream.start()
        log.info("audio: input stream started")
        
    async def _sim_audio(self):
        # Generate silence in simulation mode
        while True:
            silence = np.zeros(self.blocksize, dtype='int16')
            await self.frame_q.put(silence)
            await asyncio.sleep(self.cfg.frame_ms/1000.0)

    async def stop(self):
        if self.stream:
            self.stream.stop(); self.stream.close()
