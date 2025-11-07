import asyncio, vosk, json, numpy as np, os, logging, pathlib, zipfile, tempfile, shutil, urllib.request
from .config import Cfg
log = logging.getLogger("asr")

def ensure_vosk_model(cache_dir: str, model_name: str)->str:
    cache_dir = os.path.expanduser(cache_dir)
    target = os.path.join(cache_dir, model_name)
    if os.path.isdir(target):
        return target
    os.makedirs(cache_dir, exist_ok=True)
    # small US English model (stable URL)
    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    log.info(f"asr: downloading model to {cache_dir} (first run only)")
    tmpd = tempfile.mkdtemp()
    zpath = os.path.join(tmpd, "model.zip")
    urllib.request.urlretrieve(url, zpath)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(tmpd)
    subdirs = [p for p in pathlib.Path(tmpd).iterdir() if p.is_dir()]
    shutil.move(str(subdirs[0]), target)
    shutil.rmtree(tmpd, ignore_errors=True)
    return target

class ASRWorker:
    def __init__(self, cfg: Cfg, voiced_q: asyncio.Queue, asr_q: asyncio.Queue):
        self.cfg = cfg; self.voiced_q = voiced_q; self.asr_q = asr_q
        self.model_dir = ensure_vosk_model(cfg.vosk_model_cache, cfg.vosk_model)
        self.model = vosk.Model(self.model_dir)
        self.current_sample_rate = cfg.sample_rate

    async def run(self):
        # ASR expects 16kHz audio (resampled by VAD pipeline)
        asr_sample_rate = 16000
        rec = vosk.KaldiRecognizer(self.model, asr_sample_rate)
        rec.SetWords(False)
        log.info(f"asr: using sample rate {asr_sample_rate} Hz")
        
        while True:
            chunk = await self.voiced_q.get()
            rec.AcceptWaveform(chunk.tobytes())
            res = json.loads(rec.FinalResult())
            text = (res.get("text") or "").strip()
            if text:
                await self.asr_q.put(text)