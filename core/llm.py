import asyncio, httpx
from core.config import Cfg

SYSTEMS = {
 "memory_summarize": "Summarize the note into one short sentence, first-person neutral, no fluff.",
 "todo_summarize":   "Extract one actionable to-do, imperative verb, <=12 words.",
 "qa":               "Answer VERY concisely (<=180 chars). If unknown, say 'Not sure.'"
}

class LLM:
    def __init__(self, cfg: Cfg):
        self.cfg = cfg

    async def _chat(self, base, model, messages, timeout_ms):
        async with httpx.AsyncClient(timeout=timeout_ms/1000.0) as cx:
            r = await cx.post(f"{base}/chat/completions", json={
                "model": model, "messages": messages, "temperature": 0.2, "stream": False
            })
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()

    async def summarize_memory(self, text:str)->str:
        return await self._chat(self.cfg.llm_local_base, self.cfg.llm_local_model,
            [{"role":"system","content":SYSTEMS["memory_summarize"]},
             {"role":"user","content":text}],
            self.cfg.llm_timeout_ms)

    async def summarize_todo(self, text:str)->str:
        return await self._chat(self.cfg.llm_local_base, self.cfg.llm_local_model,
            [{"role":"system","content":SYSTEMS["todo_summarize"]},
             {"role":"user","content":text}],
            self.cfg.llm_timeout_ms)

    async def qa_dual(self, question:str):
        local = asyncio.create_task(self._chat(
            self.cfg.llm_local_base, self.cfg.llm_local_model,
            [{"role":"system","content":SYSTEMS["qa"]},{"role":"user","content":question}],
            self.cfg.llm_timeout_ms))
        better = None
        if self.cfg.llm_remote_enabled and self.cfg.llm_remote_base:
            try:
                better = asyncio.create_task(self._chat(
                    self.cfg.llm_remote_base, "gpt-remote",
                    [{"role":"system","content":SYSTEMS["qa"]},{"role":"user","content":question}],
                    self.cfg.llm_remote_timeout_ms))
            except Exception:
                better = None
        local_ans = await local
        if better:
            try:
                return local_ans, await better
            except Exception:
                return local_ans, None
        return local_ans, None