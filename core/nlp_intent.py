import os, numpy as np, logging, onnxruntime as ort
from typing import List, Dict, Tuple
from transformers import AutoTokenizer
log = logging.getLogger("intent")

_DEFAULT_PROTOS = {
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

def _cos(a,b): return float(np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b) + 1e-9))

class MiniLMEmbedder:
    def __init__(self, model_dir: str):
        self.sess = ort.InferenceSession(os.path.join(model_dir, "model.onnx"),
                                         providers=["CPUExecutionProvider"])
        self.tok = AutoTokenizer.from_pretrained(model_dir)  # uses local tokenizer files

    def encode(self, texts: List[str]) -> np.ndarray:
        inputs = self.tok(texts, padding=True, truncation=True, max_length=256, return_tensors="np")
        # Check what inputs the model expects
        model_inputs = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        }
        # Add token_type_ids if expected by the model
        if "token_type_ids" in inputs:
            model_inputs["token_type_ids"] = inputs["token_type_ids"]
        else:
            # Create token_type_ids filled with zeros if not provided
            model_inputs["token_type_ids"] = np.zeros_like(inputs["input_ids"])
        
        out = self.sess.run(None, model_inputs)[0]
        # L2-normalize rows for stable cosine later (optional)
        return out.astype(np.float32)

class IntentClassifier:
    def __init__(self, model_dir: str, threshold: float = 0.28, protos: Dict[str, List[str]]|None=None):
        self.emb = MiniLMEmbedder(model_dir)
        self.protos = protos or _DEFAULT_PROTOS
        self.threshold = threshold
        self.proto_vecs = {k: self.emb.encode(v).mean(axis=0) for k,v in self.protos.items()}

    def classify(self, text: str) -> Tuple[str,float,Dict[str,float]]:
        v = self.emb.encode([text])[0]
        scores = {k: _cos(v, p) for k,p in self.proto_vecs.items()}
        label, score = max(scores.items(), key=lambda kv: kv[1])
        if score < self.threshold:
            label = "ignore"
        return label, float(score), {k: float(s) for k,s in scores.items()}