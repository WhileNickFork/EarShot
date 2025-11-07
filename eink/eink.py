from __future__ import annotations

"""High-level helper for driving a UC8179-based eInk panel in landscape."""
import time
from pathlib import Path
from typing import Optional, Sequence, Tuple
import board
import busio
import digitalio
from adafruit_epd.epd import Adafruit_EPD
from adafruit_epd.uc8179 import Adafruit_UC8179
from PIL import Image, ImageDraw, ImageFont
# Toggle this constant to flip the landscape orientation (rotation 1 vs 3).
LANDSCAPE_UPSIDE_DOWN: bool = False

DEFAULT_FONT_PATHS: Sequence[Path] = (
	Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
	Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
)
DEFAULT_FONT_SIZE: int = 16


class EInkDisplay:
	"""Controller for the 800x480 UC8179-based eInk display.

	Parameters
	----------
	upside_down:
		When ``True`` the content is rendered rotated 180° (landscape upside-down).
	font_path:
		Optional custom font file path for text rendering.
	font_size:
		Font size in points used for the default font.
	"""

	WIDTH: int = 800
	HEIGHT: int = 480

	def __init__(
		self,
		*,
		upside_down: bool = LANDSCAPE_UPSIDE_DOWN,
		font_path: Optional[str] = None,
		font_size: int = DEFAULT_FONT_SIZE,
	) -> None:
		self._upside_down = upside_down
		self._font_path: Optional[str] = font_path
		self._font_size: int = font_size

		self._spi = self._init_spi()
		self._cs = digitalio.DigitalInOut(board.D8)
		self._dc = digitalio.DigitalInOut(board.D25)
		self._rst = digitalio.DigitalInOut(board.D17)
		self._busy = digitalio.DigitalInOut(board.D24)

		self._pwr = digitalio.DigitalInOut(board.D18)
		self._pwr.direction = digitalio.Direction.OUTPUT
		self._power_on()

		self._display = Adafruit_UC8179(
			self.WIDTH,
			self.HEIGHT,
			self._spi,
			cs_pin=self._cs,
			dc_pin=self._dc,
			sramcs_pin=None,
			rst_pin=self._rst,
			busy_pin=self._busy,
		)

		# Required for UC8179 5.83"/7.5" monochrome panels.
		self._display.set_black_buffer(1, False)
		self._display.set_color_buffer(1, False)

		self._rotation = 2 if self._upside_down else 0
		self._display.rotation = self._rotation
		self._display.fill(Adafruit_EPD.WHITE)

		self._image = Image.new("L", (self._display.width, self._display.height), 255)
		self._draw = ImageDraw.Draw(self._image)
		self._font = self._load_font(font_path, font_size, record=True)

	@staticmethod
	def _init_spi() -> busio.SPI:
		spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
		while not spi.try_lock():
			time.sleep(0.001)
		spi.configure(baudrate=20_000_000)
		spi.unlock()
		return spi

	def _power_on(self) -> None:
		self._pwr.value = True
		time.sleep(0.05)

	def _power_off(self) -> None:
		self._pwr.value = False

	def _load_font(
		self,
		font_path: Optional[str],
		font_size: int,
		*,
		record: bool = False,
	) -> ImageFont.ImageFont:
		candidates: list[Path] = []
		if font_path:
			candidates.append(Path(font_path).expanduser())
		else:
			candidates.extend(DEFAULT_FONT_PATHS)

		for candidate in candidates:
			try:
				font = ImageFont.truetype(str(candidate), font_size)
			except (OSError, IOError):
				continue
			if record:
				self._font_path = str(candidate)
				self._font_size = font_size
			return font

		font = ImageFont.load_default()
		if record:
			self._font_path = None
			self._font_size = font_size
		return font

	@staticmethod
	def _text_width(text: str, font: ImageFont.ImageFont) -> int:
		if not text:
			return 0
		if hasattr(font, "getlength"):
			return int(font.getlength(text))
		bbox = font.getbbox(text)
		return bbox[2] - bbox[0]

	@staticmethod
	def _line_height(font: ImageFont.ImageFont) -> int:
		try:
			ascent, descent = font.getmetrics()
			return ascent + descent
		except AttributeError:
			bbox = font.getbbox("Ay")
			return bbox[3] - bbox[1]

	def _break_word(self, word: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
		if max_width <= 0:
			return [word]
		segments: list[str] = []
		current = ""
		for char in word:
			candidate = current + char
			if not current or self._text_width(candidate, font) <= max_width:
				current = candidate
			else:
				segments.append(current)
				current = char
		if current:
			segments.append(current)
		return segments or [word]

	def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
		if max_width <= 0:
			return [text]
		lines: list[str] = []
		paragraphs = text.split("\n")
		for paragraph in paragraphs:
			words = paragraph.split()
			if not words:
				lines.append("")
				continue
			current = ""
			for word in words:
				segments = [word]
				if self._text_width(word, font) > max_width:
					segments = self._break_word(word, font, max_width)
				for segment in segments:
					if not current:
						current = segment
						continue
					candidate = f"{current} {segment}"
					if self._text_width(candidate, font) <= max_width:
						current = candidate
					else:
						lines.append(current)
						current = segment
			if current:
				lines.append(current)
		if not lines:
			lines.append("")
		return lines

	@property
	def image(self) -> Image.Image:
		"""Current backing image used for drawing."""

		return self._image

	@property
	def draw(self) -> ImageDraw.ImageDraw:
		"""Pillow drawing context bound to the backing image."""

		return self._draw

	@property
	def font(self) -> ImageFont.ImageFont:
		return self._font

	def set_font(self, font_path: Optional[str], font_size: int = DEFAULT_FONT_SIZE) -> None:
		self._font = self._load_font(font_path, font_size, record=True)

	def clear(self, color: int = 255) -> None:
		self._draw.rectangle((0, 0, self._display.width, self._display.height), fill=color)

	def draw_text(
		self,
		position: Tuple[int, int],
		text: str,
		*,
		fill: int = 0,
		font: Optional[ImageFont.ImageFont] = None,
	) -> None:
		self._draw.text(position, text, font=font or self._font, fill=fill)

	def draw_rectangle(
		self,
		box: Tuple[int, int, int, int],
		*,
		outline: int = 0,
		width: int = 1,
		fill: Optional[int] = None,
	) -> None:
		self._draw.rectangle(box, outline=outline, width=width, fill=fill)

	def draw_line(
		self,
		points: Sequence[Tuple[int, int]] | Tuple[int, int, int, int],
		*,
		fill: int = 0,
		width: int = 1,
	) -> None:
		self._draw.line(points, fill=fill, width=width)

	def draw_slide(
		self,
		title: str,
		body: str,
		*,
		title_font_size: int = 36,
		body_font_size: int = DEFAULT_FONT_SIZE,
		title_font_path: Optional[str] = None,
		body_font_path: Optional[str] = None,
		title_fill: int = 0,
		body_fill: int = 0,
		body_line_spacing: int = 6,
		clear_before: bool = True,
	) -> None:
		"""Render a title/body slide layout onto the backing image."""

		if clear_before:
			self.clear()

		title_font = self._load_font(title_font_path or self._font_path, title_font_size)
		if body_font_path is None and body_font_size == self._font_size:
			body_font = self._font
		else:
			body_font = self._load_font(body_font_path or self._font_path, body_font_size)

		margin_x = 32
		margin_top = 24
		margin_bottom = 24
		title_body_gap = 18
		body_line_spacing = max(body_line_spacing, 0)

		max_width = max(self._display.width - (margin_x * 2), 1)
		title_lines = self._wrap_text(title, title_font, max_width)
		body_lines = self._wrap_text(body, body_font, max_width)
		if all(not line for line in title_lines):
			title_lines = []

		title_line_height = self._line_height(title_font)
		body_line_height = self._line_height(body_font)
		title_line_spacing = max(body_line_spacing, 6)

		y = margin_top
		max_y = self._display.height - margin_bottom

		for idx, line in enumerate(title_lines):
			if y + title_line_height > max_y:
				break
			if line:
				self._draw.text((margin_x, y), line, font=title_font, fill=title_fill)
			y += title_line_height
			if idx < len(title_lines) - 1:
				y += title_line_spacing

		if y < max_y:
			y += title_body_gap
		y = min(y, max_y)

		for idx, line in enumerate(body_lines):
			if y + body_line_height > max_y:
				break
			if line:
				self._draw.text((margin_x, y), line, font=body_font, fill=body_fill)
			y += body_line_height
			if idx < len(body_lines) - 1:
				y += body_line_spacing

	def refresh(self) -> None:
		self._display.image(self._image)
		self._display.display()

	def shutdown(self) -> None:
		try:
			self._display.sleep()
		finally:
			self._power_off()


__all__ = ["EInkDisplay", "LANDSCAPE_UPSIDE_DOWN"]
