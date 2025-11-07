"""E-ink display wrapper for showing messages."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from core2.config import Config

log = logging.getLogger("display")


class Display:
    """Async wrapper for e-ink display operations."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.enabled = cfg.display_enabled
        self.device = None
        self.executor = None
        self.lock = asyncio.Lock()
    
    async def init(self):
        """Initialize display hardware."""
        if not self.enabled:
            log.info("display: disabled")
            return
        
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eink")
        loop = asyncio.get_running_loop()
        
        try:
            await loop.run_in_executor(self.executor, self._create_device)
            log.info("display: initialized")
        except Exception as e:
            log.warning(f"display: init failed, running headless: {e}")
            self.enabled = False
            if self.executor:
                self.executor.shutdown(wait=False)
                self.executor = None
    
    async def show_message(self, title: str, body: str):
        """Display a message slide on e-ink screen."""
        if not self.enabled or not self.device:
            return
        
        # Trim body if too long
        max_chars = self.cfg.display_max_chars
        if max_chars > 0 and len(body) > max_chars:
            body = body[:max_chars - 1].rstrip() + "…"
        
        async with self.lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self.executor,
                self._render_slide,
                title,
                body
            )
    
    async def clear(self):
        """Clear display and put to sleep."""
        if not self.enabled or not self.device:
            return
        
        async with self.lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, self._clear_device)
            await loop.run_in_executor(self.executor, self._sleep_device)
        
        if self.executor:
            self.executor.shutdown(wait=False)
    
    def _create_device(self):
        """Create e-ink device (runs in thread)."""
        from eink.eink import EInkDisplay
        self.device = EInkDisplay()
    
    def _render_slide(self, title: str, body: str):
        """Render slide to display (runs in thread)."""
        if self.device:
            self.device.draw_slide(title, body)
            self.device.refresh()
    
    def _clear_device(self):
        """Clear display (runs in thread)."""
        if self.device:
            self.device.clear()
            self.device.refresh()
    
    def _sleep_device(self):
        """Put display to sleep (runs in thread)."""
        if self.device:
            self.device.shutdown()
