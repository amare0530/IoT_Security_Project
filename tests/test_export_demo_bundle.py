import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_demo_bundle.py"


def _write_dataset(path: Path, boots: int = 4) -> None:
    rows = []
    for boot in range(boots):
        created_at = f"2026-01-01T00:0{boot}:00"
        for address in range(160):
            rows.append(
                {
                    "uid": "demo-uid",
                    "address": f"{address:03d}",
                    "data": "170," * 511 + "170",
                    "created_at": created_at,
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)


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
    boot = np.load(out / "device" / "sram_boot.npy")
    assert boot.shape == (655_360,)
    assert boot.dtype == np.uint8
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
