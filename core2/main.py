"""EarShot main application entry point."""
import asyncio
import logging

from dotenv import load_dotenv

from core2.config import Config
from core2.logging_setup import setup_logging
from core2.audio import AudioCapture
from core2.vad import VADProcessor
from core2.asr import ASRWorker
from core2.intent import IntentRouter
from core2.events import EventProcessor
from core2.display import Display
from location.gps_tachyon import TachyonGPS

log = logging.getLogger("main")


async def main():
    """Main application loop."""
    # Load environment variables
    load_dotenv()
    
    # Initialize configuration
    cfg = Config()
    setup_logging(cfg.log_dir, cfg.log_level)
    log.info("earshot: starting...")
    
    # Create async queues for pipeline
    frame_queue = asyncio.Queue(maxsize=8)
    speech_queue = asyncio.Queue(maxsize=4)
    text_queue = asyncio.Queue(maxsize=16)
    event_queue = asyncio.Queue(maxsize=8)
    
    # Initialize components
    gps = TachyonGPS(simulation=cfg.simulation_mode)
    display = Display(cfg)
    
    audio = AudioCapture(cfg, frame_queue)
    vad = VADProcessor(cfg, frame_queue, speech_queue)
    asr = ASRWorker(cfg, speech_queue, text_queue)
    router = IntentRouter(cfg, text_queue, event_queue)
    processor = EventProcessor(cfg, event_queue, gps, display)
    
    # Initialize display
    await display.init()
    
    # Start audio capture
    await audio.start()
    
    log.info("earshot: all components started")
    
    try:
        # Run all async workers
        await asyncio.gather(
            gps.run(cfg.gps_poll_sec),
            vad.run(),
            asr.run(),
            router.run(),
            processor.run()
        )
    finally:
        log.info("earshot: shutting down...")
        await display.clear()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("earshot: stopped by user")
