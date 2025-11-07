import asyncio, logging, os
from dotenv import load_dotenv
from .config import Cfg
from .logging_setup import setup_logger
from .audio import AudioCapture
from .vad import VADGate
from .asr import ASRWorker
from .intent import IntentRouter
from .events import EventProcessor
from location.gps_tachyon import TachyonGPS
from .display import Display
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading, json, time

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"status":"ok","ts":time.time()}).encode())
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *args, **kwargs): pass

def start_health():
    srv = HTTPServer(("0.0.0.0", 8088), Health)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()

async def main():
    load_dotenv()
    cfg = Cfg()
    setup_logger(cfg.log_dir, cfg.log_level)
    log = logging.getLogger("main")
    log.info("boot: earshot starting")

    frame_q = asyncio.Queue(maxsize=8)
    voiced_q = asyncio.Queue(maxsize=4)
    asr_q = asyncio.Queue(maxsize=16)
    event_q = asyncio.Queue(maxsize=8)

    gps = TachyonGPS(simulation=cfg.simulation_mode)
    display = Display(cfg)

    ac = AudioCapture(cfg, frame_q)
    vad = VADGate(cfg, frame_q, voiced_q)
    asr = ASRWorker(cfg, voiced_q, asr_q)
    ir  = IntentRouter(cfg, asr_q, event_q)
    ep  = EventProcessor(cfg, event_q, gps, display)

    start_health()
    await display.init()
    await ac.start()

    try:
        await asyncio.gather(
            gps.run(cfg.gps_poll_sec),
            vad.run(),
            asr.run(),
            ir.run(),
            ep.run()
        )
    finally:
        log.info("boot: shutting down, clearing display")
        await display.clear_and_sleep()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass