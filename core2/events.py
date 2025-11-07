"""Event processing for handling classified intents."""
import asyncio
import json
import logging
import time
from pathlib import Path

from core2.config import Config
from core2.llm import LLMClient

log = logging.getLogger("events")


class EventProcessor:
    """Processes intent events using LLM and displays results."""
    
    def __init__(self, cfg: Config, event_queue: asyncio.Queue, gps, display):
        self.cfg = cfg
        self.event_queue = event_queue
        self.gps = gps
        self.display = display
        self.llm = LLMClient(cfg)
        
        # Create storage directory for events
        self.data_dir = Path(cfg.data_dir).expanduser() / "events"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _save_event(self, filename: str, data: dict):
        """Append event to JSONL file (privacy: in-memory only, minimal logging)."""
        filepath = self.data_dir / filename
        with filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    
    async def run(self):
        """Main event processing loop."""
        log.info("events: started")
        
        while True:
            event = await self.event_queue.get()
            
            event_type = event["type"]
            context = event["context"]
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(event["timestamp"]))
            location = self.gps.current()
            
            try:
                if event_type == "memory":
                    # Summarize memory note
                    summary = await self.llm.summarize_memory(context)
                    log.info(f"events: memory -> '{summary}'")
                    
                    await self.display.show_message("Memory", summary)
                    
                    self._save_event("memory.jsonl", {
                        "type": "memory",
                        "summary": summary,
                        "timestamp": timestamp,
                        "location": location
                    })
                
                elif event_type == "todo":
                    # Extract to-do item
                    todo = await self.llm.summarize_todo(context)
                    log.info(f"events: todo -> '{todo}'")
                    
                    await self.display.show_message("To-Do", todo)
                    
                    self._save_event("todos.jsonl", {
                        "type": "todo",
                        "task": todo,
                        "timestamp": timestamp,
                        "location": location
                    })
                    
                    # Future: integrate with TickTick here
                
                elif event_type == "question":
                    # Answer question
                    answer = await self.llm.answer_question(context)
                    log.info(f"events: question -> '{answer}'")
                    
                    await self.display.show_message("Answer", answer)
                    
                    self._save_event("questions.jsonl", {
                        "type": "question",
                        "question": context,
                        "answer": answer,
                        "timestamp": timestamp,
                        "location": location
                    })
            
            except Exception as e:
                log.error(f"events: error processing {event_type}: {e}", exc_info=True)
