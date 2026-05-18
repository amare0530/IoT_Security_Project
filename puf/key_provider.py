from __future__ import annotations

import csv
from pathlib import Path


DEFAULT_KEY_REGISTRY = Path("artifacts/fuzzy_extractor_results.csv")


def load_key_hex_for_uid(uid: str, registry_path: Path = DEFAULT_KEY_REGISTRY) -> str:
    if not registry_path.exists():
        raise FileNotFoundError(f"PUF key registry not found: {registry_path}")

    with registry_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("uid") == uid:
                key_hex = row.get("key_hex", "")
                if not key_hex:
                    raise ValueError(f"Missing key_hex for uid={uid}")
                return key_hex

    raise KeyError(f"uid not found in PUF key registry: {uid}")


def resolve_key_bytes(
    uid: str,
    manual_key_hex: str | None = None,
    registry_path: Path = DEFAULT_KEY_REGISTRY,
) -> bytes:
    key_hex = manual_key_hex or load_key_hex_for_uid(uid, registry_path)
    return bytes.fromhex(key_hex)
