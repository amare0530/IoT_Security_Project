from pathlib import Path

from puf.key_provider import load_key_hex_for_uid, resolve_key_bytes


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
