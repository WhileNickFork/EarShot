import asyncio, time, logging
from .rolling import RollingBuffer
from .config import Cfg
from .nlp_intent import IntentClassifier
log = logging.getLogger("router")

class IntentRouter:
    def __init__(self, cfg: Cfg, asr_q: asyncio.Queue, event_q: asyncio.Queue):
        self.cfg = cfg; self.asr_q = asr_q; self.event_q = event_q
        self.roll = RollingBuffer(cfg.rolling_pre_sec, cfg.rolling_post_sec)
        self.clf = IntentClassifier(cfg.intent_model_path, cfg.intent_threshold)
        self.sema = asyncio.Semaphore(cfg.max_parallel_intent)

    async def run(self):
        while True:
            text = await self.asr_q.get()
            self.roll.add(text)
            asyncio.create_task(self._classify(text))

    async def _classify(self, text: str):
        async with self.sema:
            label, score, scores = self.clf.classify(text)
            log.info(f"intent: label={label} score={score:.3f} scores={scores}")
            if label in ("memory","todo","question"):
                center = time.time()
                window = self.roll.window_text(center)
                await self.event_q.put({"label":label, "center_ts":center, "window":window})