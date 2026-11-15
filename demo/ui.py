"""Small ANSI helpers shared by the demo terminals (standard library only)."""

from __future__ import annotations

import os
import sys
import time

_CODES = {
    "reset": "0", "bold": "1", "dim": "2",
    "red": "91", "green": "92", "yellow": "93", "blue": "94", "cyan": "96",
    "bg_red": "41", "bg_green": "42", "bg_yellow": "43",
}
_state = {"color": False, "speed": 1.0}


def setup(fast: bool = False) -> None:
    """Prepare the terminal: UTF-8 output, ANSI colours, animation speed."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if os.name == "nt":
        os.system("")  # turns on ANSI escape handling in Windows consoles
    _state["color"] = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    _state["speed"] = 0.0 if fast or not sys.stdout.isatty() else 1.0


def paint(text: str, *styles: str) -> str:
    if not _state["color"] or not styles:
        return text
    prefix = "".join(f"\033[{_CODES[style]}m" for style in styles)
    return f"{prefix}{text}\033[0m"


def pause(seconds: float) -> None:
    if _state["speed"]:
        time.sleep(seconds * _state["speed"])


def say(text: str = "", *styles: str, end: str = "\n") -> None:
    print(paint(text, *styles), end=end, flush=True)


def rule(title: str = "") -> None:
    line = "─" * 62
    say(f"{line}\n {title}" if title else line, "dim")


def banner(text: str, ok: bool) -> None:
    """Three-line coloured block that can be read from the back of a room."""
    width = 62
    style = "bg_green" if ok else "bg_red"
    blank = " " * width
    say(blank, style)
    say(text.center(width - _wide(text)), style, "bold")
    say(blank, style)


def _wide(text: str) -> int:
    """Extra columns taken by full-width (CJK) characters."""
    return sum(1 for ch in text if ord(ch) > 0x2E7F)


def short(value: object, keep: int = 10) -> str:
    text = str(value)
    return text if len(text) <= keep * 2 + 1 else f"{text[:keep]}…{text[-4:]}"
