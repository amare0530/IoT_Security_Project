import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from puf.key_provider import resolve_reconstructed_key


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_demo_bundle.py"


def _write_dataset(path: Path, boots: int = 4) -> np.ndarray:
    rng = np.random.default_rng(20261022)
    base = rng.integers(0, 256, size=81_920, dtype=np.uint8)
    base_bits = np.unpackbits(base)
    boot_bits = []
    for boot in range(boots):
        bits = np.unpackbits(base.copy())
        if boot < 2:
            flip_indices = rng.choice(len(bits), size=3, replace=False)
            flip_indices = flip_indices[flip_indices >= 10_000]
        else:
            flip_indices = np.array([0, 11, 22], dtype=np.int64)
        bits[flip_indices] ^= 1
        boot_bits.append(np.packbits(bits))

    rows = []
    for boot in range(boots):
        created_at = f"2026-01-01T00:0{boot}:00"
        for address in range(160):
            start = address * 4096
            data = ",".join(str(value) for value in boot_bits[boot][start // 8 : (start + 4096) // 8])
            rows.append(
                {
                    "uid": "demo-uid",
                    "address": f"{address:03d}",
                    "data": data,
                    "created_at": created_at,
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)
    return base_bits


def _run(crps: Path, out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--uid", "demo-uid", "--crps", str(crps),
         "--out", str(out), "--train-boots", "2", *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def test_export_bundle_has_device_only_public_data_and_expected_boot(tmp_path: Path) -> None:
    crps = tmp_path / "crps.csv"
    out = tmp_path / "bundle"
    _write_dataset(crps)

    result = _run(crps, out, "--seed", "7")

    assert result.returncode == 0, result.stderr
    response = json.loads((out / "device" / "response.json").read_text())
    boot = np.asarray(response["demo-uid"]["response_bits"], dtype=np.uint8)
    assert boot.shape == (655_360,)
    assert set(np.unique(boot)) <= {0, 1}
    device_text = b"\n".join(path.read_bytes() for path in (out / "device").iterdir())
    assert b"key_hex" not in device_text
    assert b"key_bits" not in device_text


def test_same_seed_reproduces_key_and_helper(tmp_path: Path) -> None:
    crps = tmp_path / "crps.csv"
    _write_dataset(crps)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"

    assert _run(crps, out_a, "--seed", "123").returncode == 0
    assert _run(crps, out_b, "--seed", "123").returncode == 0
    assert (out_a / "server" / "key_registry.csv").read_text() == (
        out_b / "server" / "key_registry.csv"
    ).read_text()
    assert json.loads((out_a / "device" / "helper_data.json").read_text()) == json.loads(
        (out_b / "device" / "helper_data.json").read_text()
    )


def test_missing_uid_and_insufficient_boots_fail(tmp_path: Path) -> None:
    crps = tmp_path / "crps.csv"
    _write_dataset(crps, boots=2)
    missing_uid = subprocess.run(
        [sys.executable, str(SCRIPT), "--uid", "missing", "--crps", str(crps)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    insufficient = _run(crps, tmp_path / "bundle")

    assert missing_uid.returncode != 0
    assert "uid not found" in missing_uid.stderr
    assert insufficient.returncode != 0
    assert "need at least" in insufficient.stderr


def test_export_without_seed_succeeds(tmp_path: Path) -> None:
    crps = tmp_path / "crps.csv"
    _write_dataset(crps)

    result = _run(crps, tmp_path / "bundle")

    assert result.returncode == 0, result.stderr


def test_device_files_reconstruct_registered_key_with_noise(tmp_path: Path) -> None:
    crps = tmp_path / "crps.csv"
    out = tmp_path / "bundle"
    golden_bits = _write_dataset(crps)

    result = _run(crps, out, "--seed", "7")

    assert result.returncode == 0, result.stderr
    registry = pd.read_csv(out / "server" / "key_registry.csv")
    assert list(registry.columns) == ["uid", "key_hex"]
    key_hex = registry.loc[0, "key_hex"]
    assert len(key_hex) == 32
    assert key_hex == key_hex.lower()
    int(key_hex, 16)

    helper = json.loads((out / "device" / "helper_data.json").read_text())
    response = json.loads((out / "device" / "response.json").read_text())
    reconstructed = resolve_reconstructed_key(
        "demo-uid", out / "device" / "response.json", out / "device" / "helper_data.json"
    )
    assert reconstructed.hex() == key_hex

    selected = np.asarray(helper["demo-uid"]["stable_indices"])
    response_bits = np.asarray(response["demo-uid"]["response_bits"])
    # The first held-out boot flips three separate 11-bit groups.
    differing_groups = sum(
        np.any(response_bits[selected][start : start + 11] != golden_bits[selected][start : start + 11])
        for start in range(0, len(selected), 11)
    )
    assert differing_groups > 0
