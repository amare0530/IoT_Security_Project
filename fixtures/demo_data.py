"""Generate a tiny synthetic SRAM-like dataset without using private captures."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

BITS_PER_RESPONSE = 256 * 11
BYTES_PER_RESPONSE = BITS_PER_RESPONSE // 8
DEMO_UIDS = ("demo-device-a", "demo-device-b")


def _response_bytes(uid_index: int, capture_index: int) -> list[int]:
    """Return a repeatable response with one harmless correctable bit flip."""
    values = [((index * 37) + (uid_index * 91) + 13) % 256 for index in range(BYTES_PER_RESPONSE)]
    if capture_index == 1:
        values[17] ^= 1
    if capture_index == 2:
        values[193] ^= 4
    return values


def rows() -> Iterable[dict[str, str | int]]:
    """Yield rows matching ``analysis.stability_analysis.load_dataset`` input."""
    start = datetime(2026, 1, 1, 9, 0, 0)
    for uid_index, uid in enumerate(DEMO_UIDS):
        for capture_index in range(12):
            yield {
                "board_type": "synthetic",
                "uid": uid,
                "pic": capture_index,
                "address": "0x20000000",
                "data": ",".join(str(value) for value in _response_bytes(uid_index, capture_index)),
                "created_at": (start + timedelta(minutes=capture_index)).isoformat(sep=" "),
            }
