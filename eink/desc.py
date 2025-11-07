"""Detailed description slide for the EInkDisplay project."""

from __future__ import annotations

from typing import NoReturn

from eink import EInkDisplay


def main() -> NoReturn:
	display = EInkDisplay()
	display.draw_slide(
		"EInk Display Controller",
		"This Python library provides a high-level interface for controlling 800x480 UC8179-based e-ink displays. The controller handles SPI communication, power management, and provides sophisticated text rendering with automatic word wrapping. Features include landscape orientation support, configurable fonts, and a simple slide-based layout system for displaying title and body content. The library supports both hardware and software font loading with fallback to default fonts, making it ideal for creating readable content on e-ink panels commonly used in digital signage, e-readers, and low-power display applications.",
		
	)
	display.refresh()


if __name__ == "__main__":
	main()