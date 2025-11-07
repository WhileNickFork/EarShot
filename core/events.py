import asyncio, json, time, logging
from pathlib import Path
from llm import LLM
from config import Cfg
try:
    from tasks.ticktick import TickTick
except ImportError:  # pragma: no cover - optional dependency
    TickTick = None
log = logging.getLogger("events")

class EventProcessor:
    def __init__(self, cfg: Cfg, event_q: asyncio.Queue, gps, display):
        self.cfg = cfg; self.event_q = event_q; self.gps = gps; self.display = display
        self.llm = LLM(cfg)
        self.dir = Path(cfg.data_dir).expanduser() / "events"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.tt = None
        if TickTick and cfg.tt_client_id and cfg.tt_access:
            self.tt = TickTick(cfg.tt_base, cfg.tt_client_id, cfg.tt_client_secret,
                               cfg.tt_access, cfg.tt_refresh)
        elif cfg.tt_client_id or cfg.tt_access:
            log.warning("ticktick: credentials configured but integration unavailable (import failed)")

    def _append(self, name, obj):
        path = self.dir / name
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    async def _push_ticktick(self, task_title:str):
        if not self.tt: return
        try:
            j = await self.tt.create_task(task_title)
            log.info(f"ticktick: task created id={j.get('id','?')} title='{task_title}'")
        except Exception as e:
            log.warning(f"ticktick: create failed: {e}")

    async def run(self):
        while True:
            ev = await self.event_q.get()
            gps = self.gps.current()
            ts  = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ev["center_ts"]))
            try:
                if ev["label"] == "memory":
                    s = await self.llm.summarize_memory(ev["window"])
                    rec = {"type":"memory","summary":s,"ts":ts,"gps":gps}
                    self._append("memory.min.jsonl", rec)
                    await self.display.show_text("Memory", s)
                    log.info(f"event: memory summary='{s}'")

                elif ev["label"] == "todo":
                    t = await self.llm.summarize_todo(ev["window"])
                    rec = {"type":"todo","task":t,"ts":ts,"gps":gps}
                    self._append("todos.min.jsonl", rec)
                    await self.display.show_text("To-Do", t)
                    log.info(f"event: todo task='{t}'")
                    asyncio.create_task(self._push_ticktick(t))

                elif ev["label"] == "question":
                    local, remote = await self.llm.qa_dual(ev["window"])
                    shown = remote or local
                    await self.display.show_text("Answer", shown)
                    rec = {"type":"qa","q":ev["window"],"a":shown,"ts":ts,"gps":gps}
                    self._append("q_and_a.min.jsonl", rec)
                    log.info(f"event: question answer='{shown}'")
            except Exception as e:
                log.error(f"event error: {e}", exc_info=True)