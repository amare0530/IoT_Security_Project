"""Write a SYNTHETIC demo bundle for rehearsal on a machine without the dataset.

Run:  python -m demo.make_synthetic_bundle --out demo_bundle_synthetic

The bits are random numbers, not SRAM measurements. Use the bundle exported
from the real dataset (scripts/export_demo_bundle.py) for the defense itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puf.fuzzy_extractor import FuzzyExtractor

TOTAL_BITS = 655_360
UID = "SYNTHETIC-DEVICE-001"
OTHER_UID = "SYNTHETIC-DEVICE-002"


def write_bundle(out_dir: Path, seed: int | None = None) -> bytes:
    rng = np.random.default_rng(seed)
    golden = rng.integers(0, 2, TOTAL_BITS, dtype=np.uint8)
    mask = np.zeros(TOTAL_BITS, dtype=np.uint8)
    mask[rng.choice(TOTAL_BITS, size=2816, replace=False)] = 1
    key, helper = FuzzyExtractor().gen(golden, mask, uid=UID)

    boot = golden.copy()
    noisy = rng.choice(np.flatnonzero(mask), size=28, replace=False)  # about 1 %
    boot[noisy] ^= 1
    other = rng.integers(0, 2, TOTAL_BITS, dtype=np.uint8)

    for name in ("server", "device", "attacker"):
        (out_dir / name).mkdir(parents=True, exist_ok=True)
    with (out_dir / "server" / "key_registry.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["uid", "key_hex"])
        writer.writeheader()
        writer.writerow({"uid": UID, "key_hex": key.hex()})
    (out_dir / "device" / "helper_data.json").write_text(
        json.dumps({UID: helper}), encoding="utf-8")
    (out_dir / "device" / "response.json").write_text(
        json.dumps({UID: {"response_bits": boot.tolist()}}), encoding="utf-8")
    (out_dir / "attacker" / "response.json").write_text(
        json.dumps({OTHER_UID: {"response_bits": other.tolist()}}), encoding="utf-8")
    (out_dir / "README.txt").write_text(
        "SYNTHETIC rehearsal bundle: random bits, not SRAM measurements.\n", encoding="utf-8")
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a synthetic rehearsal bundle")
    parser.add_argument("--out", type=Path, default=Path("demo_bundle_synthetic"))
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    write_bundle(args.out, args.seed)
    print(f"synthetic bundle written to {args.out} (rehearsal only)")


if __name__ == "__main__":
    main()
