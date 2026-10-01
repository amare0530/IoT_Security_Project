from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from puf.fuzzy_extractor import FuzzyExtractor


DEFAULT_KEY_REGISTRY = Path("artifacts/fuzzy_extractor_results.csv")
KEY_BYTES = 16


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
    try:
        key = bytes.fromhex(key_hex)
    except ValueError as exc:
        raise ValueError(f"Invalid hexadecimal key for uid={uid}") from exc
    if len(key) != KEY_BYTES:
        raise ValueError(
            f"Invalid key length for uid={uid}: expected {KEY_BYTES} bytes, got {len(key)}"
        )
    return key


def _load_uid_record(path: Path, uid: str) -> object:
    if not path.exists():
        raise FileNotFoundError(f"PUF registry not found: {path}")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        if uid in payload:
            return payload[uid]
        records = payload.get("records")
    else:
        records = payload

    if isinstance(records, list):
        for record in records:
            if isinstance(record, dict) and record.get("uid") == uid:
                return record
    raise KeyError(f"uid not found in PUF registry: {uid}")


def resolve_reconstructed_key(
    uid: str,
    response_registry: Path,
    helper_registry: Path,
) -> bytes:
    """Reconstruct a device key from response bits and public helper data."""
    response_record = _load_uid_record(response_registry, uid)
    helper_record = _load_uid_record(helper_registry, uid)

    if isinstance(response_record, dict):
        response_record = response_record.get("response_bits")
    if not isinstance(response_record, list):
        raise ValueError("response registry record must contain response_bits")
    if not isinstance(helper_record, dict):
        raise ValueError("helper registry record must be an object")

    response_bits = np.asarray(response_record, dtype=np.uint8)
    extractor = FuzzyExtractor(
        bits_needed=helper_record["bits_needed"],
        repetition=helper_record["repetition"],
    )
    return extractor.rep(response_bits, helper_record)
