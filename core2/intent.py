"""Intent classification and rolling context buffer."""
import asyncio
import collections
import logging
import os
import time
from typing import Dict, List, Tuple

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from core2.config import Config

log = logging.getLogger("intent")


# Default prototype sentences for intent classification
INTENT_PROTOTYPES = {
    "memory": [
        "This is a personal note to remember later.",
        "A brief diary memory to keep."
    ],
    "todo": [
        "This is an actionable task to do.",
        "A short to-do item to complete."
    ],
    "question": [
        "This is a direct question asking for an answer.",
        "A short factual query."
    ],
    "ignore": [
        "Small talk or irrelevant chatter.",
        "No action or answer is needed."
    ]
}


class RollingBuffer:
    """Maintains a rolling time window of transcribed text for context."""
    
    def __init__(self, pre_sec: int, post_sec: int):
        self.pre_sec = pre_sec
        self.post_sec = post_sec
        self.buffer = collections.deque()  # (timestamp, text)
    
    def add(self, text: str):
        """Add text with current timestamp to buffer."""
        now = time.time()
        self.buffer.append((now, text))
        
        # Clean up old entries (keep some extra buffer)
        cutoff = now - (self.pre_sec + self.post_sec + 60)
        while self.buffer and self.buffer[0][0] < cutoff:
            self.buffer.popleft()
    
    def get_window(self, center_ts: float) -> str:
        """Get text within time window around center timestamp."""
        start = center_ts - self.pre_sec
        end = center_ts + self.post_sec
        return " ".join(t for ts, t in self.buffer if start <= ts <= end)


class IntentClassifier:
    """Classifies text intent using sentence embeddings."""
    
    def __init__(self, model_dir: str, threshold: float):
        self.threshold = threshold
        
        # Load ONNX model and tokenizer
        model_path = os.path.join(model_dir, "model.onnx")
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        
        # Compute prototype embeddings
        self.prototypes = INTENT_PROTOTYPES
        self.prototype_vectors = {}
        for label, examples in self.prototypes.items():
            embeddings = self._encode(examples)
            self.prototype_vectors[label] = embeddings.mean(axis=0)
        
        log.info("intent: classifier initialized")
    
    def _encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="np"
        )
        
        # Build model inputs
        model_inputs = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        }
        
        # Add token_type_ids if needed
        if "token_type_ids" in inputs:
            model_inputs["token_type_ids"] = inputs["token_type_ids"]
        else:
            model_inputs["token_type_ids"] = np.zeros_like(inputs["input_ids"])
        
        # Run model
        output = self.session.run(None, model_inputs)[0]
        return output.astype(np.float32)
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between vectors."""
        return float(
            np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        )
    
    def classify(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """Classify text intent. Returns (label, score, all_scores)."""
        embedding = self._encode([text])[0]
        
        # Compute similarities to all prototypes
        scores = {
            label: self._cosine_similarity(embedding, proto)
            for label, proto in self.prototype_vectors.items()
        }
        
        # Get best match
        label, score = max(scores.items(), key=lambda x: x[1])
        
        # Apply threshold
        if score < self.threshold:
            label = "ignore"
        
        return label, float(score), {k: float(v) for k, v in scores.items()}


class IntentRouter:
    """Routes transcribed text through intent classification and generates events."""
    
    def __init__(self, cfg: Config, text_queue: asyncio.Queue, event_queue: asyncio.Queue):
        self.cfg = cfg
        self.text_queue = text_queue
        self.event_queue = event_queue
        
        self.buffer = RollingBuffer(cfg.context_pre_sec, cfg.context_post_sec)
        self.classifier = IntentClassifier(cfg.intent_model_path, cfg.intent_threshold)
    
    async def run(self):
        """Main intent routing loop."""
        log.info("intent: started")
        
        while True:
            text = await self.text_queue.get()
            
            # Add to rolling buffer
            self.buffer.add(text)
            
            # Classify intent
            label, score, scores = self.classifier.classify(text)
            log.info(f"intent: '{text}' -> {label} ({score:.3f})")
            
            # Generate event if actionable
            if label in ("memory", "todo", "question"):
                center_ts = time.time()
                context = self.buffer.get_window(center_ts)
                
                event = {
                    "type": label,
                    "text": text,
                    "context": context,
                    "timestamp": center_ts
                }
                
                await self.event_queue.put(event)
