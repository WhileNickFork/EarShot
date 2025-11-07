import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional

from .config import Cfg

log = logging.getLogger("display")


class Display:
    """Async wrapper around the optional e-ink display.

    If the display is disabled in the configuration or the hardware stack
    cannot be initialised (for example on development hosts), the public
    methods become no-ops to keep the pipeline running.
    """

    def __init__(self, cfg: Cfg):
        self.cfg = cfg
        self._enabled = bool(cfg.display_enabled)
        self._device = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = asyncio.Lock()
        self._init_failed: Optional[Exception] = None

    async def init(self) -> None:
        if not self._enabled:
            log.info("display: disabled via configuration")
            return
        loop = asyncio.get_running_loop()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eink")
        try:
            await loop.run_in_executor(self._executor, self._create_device)
            log.info("display: initialised")
        except Exception as exc:  # pragma: no cover - hardware specific
            self._init_failed = exc
            self._enabled = False
            log.warning("display: init failed, running headless (%s)", exc)
            await self._shutdown_executor()

    async def show_text(self, title: str, body: str) -> None:
        if not self._enabled or not self._device:
            return
        # Trim overly long bodies to keep the slide readable.
        max_chars = max(0, int(self.cfg.display_max_chars))
        if max_chars and len(body) > max_chars:
            body = body[: max_chars - 1].rstrip() + "\u2026"
        async with self._lock:
            await self._run_in_executor(self._render_slide, title, body)

    async def clear_and_sleep(self) -> None:
        if not self._enabled or not self._device:
            await self._shutdown_executor()
            return
        async with self._lock:
            await self._run_in_executor(self._clear_display)
            await self._run_in_executor(self._sleep_device)
        await self._shutdown_executor()

    async def _run_in_executor(self, func, *args) -> None:
        if not self._executor:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, partial(func, *args))

    def _create_device(self) -> None:  # pragma: no cover - hardware specific
        from eink.eink import EInkDisplay

        self._device = EInkDisplay()

    def _render_slide(self, title: str, body: str) -> None:  # pragma: no cover
        if not self._device:
            return
        self._device.draw_slide(title, body)
        self._device.refresh()

    def _clear_display(self) -> None:  # pragma: no cover
        if not self._device:
            return
        self._device.clear()
        self._device.refresh()

    def _sleep_device(self) -> None:  # pragma: no cover
        if not self._device:
            return
        self._device.shutdown()

    async def _shutdown_executor(self) -> None:
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    @property
    def is_available(self) -> bool:
        return self._enabled and self._device is not None and self._init_failed is None
