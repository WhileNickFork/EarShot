"""LLM interaction for summaries and question answering."""
import logging

import httpx

from core2.config import Config

log = logging.getLogger("llm")


# System prompts for different LLM tasks
SYSTEM_PROMPTS = {
    "memory": "Summarize the note into one short sentence, first-person neutral, no fluff.",
    "todo": "Extract one actionable to-do, imperative verb, <=12 words.",
    "question": "Answer VERY concisely (<=180 chars). If unknown, say 'Not sure.'"
}


class LLMClient:
    """Client for OpenAI-compatible LLM endpoint."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.base_url = cfg.llm_base_url
        self.model = cfg.llm_model
        self.timeout = cfg.llm_timeout_sec
    
    async def _chat(self, system: str, user: str) -> str:
        """Send chat completion request to LLM."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    "temperature": 0.2,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    
    async def summarize_memory(self, text: str) -> str:
        """Summarize text as a memory note."""
        return await self._chat(SYSTEM_PROMPTS["memory"], text)
    
    async def summarize_todo(self, text: str) -> str:
        """Extract actionable to-do from text."""
        return await self._chat(SYSTEM_PROMPTS["todo"], text)
    
    async def answer_question(self, text: str) -> str:
        """Answer a question from text."""
        return await self._chat(SYSTEM_PROMPTS["question"], text)
