from pathlib import Path

import json

import numpy as np

from puf.fuzzy_extractor import FuzzyExtractor
from puf.key_provider import (
    load_key_hex_for_uid,
    resolve_key_bytes,
    resolve_reconstructed_key,
)


def test_load_key_hex_for_uid(tmp_path: Path) -> None:
    registry = tmp_path / "keys.csv"
    registry.write_text(
        "uid,key_hex\n"
        "device-a,00112233445566778899aabbccddeeff\n"
        "device-b,ffeeddccbbaa99887766554433221100\n",
        encoding="utf-8",
    )

    assert (
        load_key_hex_for_uid("device-b", registry)
        == "ffeeddccbbaa99887766554433221100"
    )


def test_manual_key_overrides_registry(tmp_path: Path) -> None:
    registry = tmp_path / "keys.csv"
    registry.write_text("uid,key_hex\ndevice-a,00\n", encoding="utf-8")

    key = resolve_key_bytes(
        uid="missing-device",
        manual_key_hex="00112233445566778899aabbccddeeff",
        registry_path=registry,
    )

    assert key == bytes.fromhex("00112233445566778899aabbccddeeff")


def test_reconstruct_key_from_response_and_helper_registries(tmp_path: Path) -> None:
    extractor = FuzzyExtractor(bits_needed=8, repetition=3)
    response = np.tile(np.array([0, 1], dtype=np.uint8), 16)
    key, helper = extractor.gen(
        response, np.ones_like(response), uid="device-a", rng=np.random.default_rng(5)
    )
    response_registry = tmp_path / "responses.json"
    helper_registry = tmp_path / "helpers.json"
    response_registry.write_text(
        json.dumps({"device-a": response.tolist()}), encoding="utf-8"
    )
    helper_registry.write_text(
        json.dumps({"device-a": helper}), encoding="utf-8"
    )

    assert resolve_reconstructed_key("device-a", response_registry, helper_registry) == key


def test_key_registry_rejects_short_key(tmp_path: Path) -> None:
    registry = tmp_path / "keys.csv"
    registry.write_text("uid,key_hex\ndevice-a,00\n", encoding="utf-8")

    try:
        resolve_key_bytes("device-a", registry_path=registry)
    except ValueError as exc:
        assert "Invalid key length" in str(exc)
    else:
        raise AssertionError("short key was accepted")
