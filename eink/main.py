"""Example usage for the `EInkDisplay` helper."""

from __future__ import annotations

from typing import NoReturn

from eink import EInkDisplay


def main() -> NoReturn:
	display = EInkDisplay()
	display.draw_slide(
		"Project Update",
		"This slide layout demonstrates the title and body text rendering with automatic word wrapping so content stays within the display bounds.",
		
	)
	display.refresh()


if __name__ == "__main__":
	main()
