"""Automatic Speech Recognition using Vosk."""
import asyncio
import json
import logging
import os
import pathlib
import shutil
import tempfile
import urllib.request
import zipfile

import numpy as np
import vosk

from core2.config import Config

log = logging.getLogger("asr")


def download_vosk_model(cache_dir: str, model_name: str) -> str:
    """Download and extract Vosk model if not already cached."""
    cache_dir = os.path.expanduser(cache_dir)
    target = os.path.join(cache_dir, model_name)
    
    if os.path.isdir(target):
        return target
    
    os.makedirs(cache_dir, exist_ok=True)
    
    # Download the small English model
    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    log.info(f"asr: downloading Vosk model (first run only)...")
    
    tmpd = tempfile.mkdtemp()
    try:
        zpath = os.path.join(tmpd, "model.zip")
        urllib.request.urlretrieve(url, zpath)
        
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(tmpd)
        
        subdirs = [p for p in pathlib.Path(tmpd).iterdir() if p.is_dir()]
        shutil.move(str(subdirs[0]), target)
        log.info(f"asr: model downloaded to {target}")
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    
    return target


class ASRWorker:
    """Transcribes speech audio using Vosk."""
    
    def __init__(self, cfg: Config, speech_queue: asyncio.Queue, text_queue: asyncio.Queue):
        self.cfg = cfg
        self.speech_queue = speech_queue
        self.text_queue = text_queue
        
        # Download and load Vosk model
        model_dir = download_vosk_model(cfg.vosk_model_cache, cfg.vosk_model_name)
        self.model = vosk.Model(model_dir)
        log.info(f"asr: loaded Vosk model from {model_dir}")
    
    async def run(self):
        """Main ASR processing loop."""
        # Vosk expects 16kHz audio (VAD already resamples to this)
        recognizer = vosk.KaldiRecognizer(self.model, 16000)
        recognizer.SetWords(False)
        
        log.info("asr: started")
        
        while True:
            audio = await self.speech_queue.get()
            
            # Process audio through recognizer
            recognizer.AcceptWaveform(audio.tobytes())
            result = json.loads(recognizer.FinalResult())
            
            text = (result.get("text") or "").strip()
            if text:
                await self.text_queue.put(text)
                log.info(f"asr: '{text}'")
