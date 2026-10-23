from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from analysis.stability_analysis import (  # noqa: E402
    compute_stability_per_uid,
    load_dataset,
)
from puf.fuzzy_extractor import FuzzyExtractor  # noqa: E402
from puf.selection import reorder_helper_data, select_balanced_positions  # noqa: E402

TOTAL_BITS = 655_360
ROWS_PER_BOOT = 160
BITS_PER_GROUP = 11
BITS_PER_ROW = 4_096
GROUP_COUNT = 256
DEFAULT_THRESHOLD = 0.90


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a two-machine PUF demo bundle")
    parser.add_argument("--uid", required=True)
    parser.add_argument("--crps", required=True, type=Path)
    parser.add_argument("--out", default=Path("demo_bundle"), type=Path)
    parser.add_argument("--train-boots", default=7, type=int)
    parser.add_argument("--threshold", default=DEFAULT_THRESHOLD, type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--selection", choices=("balanced", "legacy"), default="balanced")
    parser.add_argument("--population-cache", type=Path)
    return parser.parse_args()


def _boot_matrix(df, uid: str) -> tuple[list[object], np.ndarray]:
    uid_df = df[df["uid"].astype(str) == uid]
    if uid_df.empty:
        raise ValueError(f"uid not found: {uid}")

    boots: list[object] = []
    bitstreams: list[str] = []
    for created_at, boot_df in uid_df.groupby("created_at", sort=True):
        if len(boot_df) != ROWS_PER_BOOT:
            raise ValueError(
                f"uid={uid}, created_at={created_at} has {len(boot_df)} rows; "
                f"expected {ROWS_PER_BOOT}"
            )
        if boot_df["address"].duplicated().any():
            raise ValueError(f"uid={uid}, created_at={created_at} has duplicate addresses")

        ordered = boot_df.sort_values("address")
        bitstream = "".join(ordered["bitstream"].tolist())
        if len(bitstream) != TOTAL_BITS:
            raise ValueError(
                f"uid={uid}, created_at={created_at} has {len(bitstream)} bits; "
                f"expected {TOTAL_BITS}"
            )
        boots.append(created_at)
        bitstreams.append(bitstream)

    matrix = (
        np.frombuffer("".join(bitstreams).encode("ascii"), dtype=np.uint8)
        .reshape(len(bitstreams), TOTAL_BITS)
        - ord("0")
    )
    return boots, matrix


def _population_training(
    df, train_boots: int, threshold: float, cache_path: Path | None
) -> tuple[np.ndarray, int, set[int]]:
    if cache_path is not None and cache_path.exists():
        with np.load(cache_path) as cached:
            return (
                np.asarray(cached["golden_sum"], dtype=np.uint64),
                int(cached["device_count"]),
                set(np.asarray(cached["deterministic_rows"], dtype=np.int64).tolist()),
            )
    training_goldens = []
    for uid in sorted(df["uid"].astype(str).unique()):
        boots, matrix = _boot_matrix(df, uid)
        if len(boots) < train_boots:
            raise ValueError(f"uid={uid} has fewer than {train_boots} training boots")
        training = matrix[:train_boots]
        training_goldens.append((training.mean(axis=0) >= 0.5).astype(np.uint8))
    goldens = np.asarray(training_goldens, dtype=np.uint8)
    distances = []
    for row in range(ROWS_PER_BOOT):
        row_bits = goldens[:, row * 4096 : (row + 1) * 4096]
        pairwise = [
            np.count_nonzero(row_bits[left] != row_bits[right]) / 4096
            for left in range(len(row_bits))
            for right in range(left + 1, len(row_bits))
        ]
        distances.append(float(np.mean(pairwise)))
    deterministic = {row for row, distance in enumerate(distances) if distance <= 0.01}
    golden_sum = goldens.sum(axis=0, dtype=np.uint64)
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            cache_path,
            golden_sum=golden_sum,
            device_count=np.asarray(len(goldens), dtype=np.int64),
            deterministic_rows=np.asarray(sorted(deterministic), dtype=np.int64),
        )
    return golden_sum, len(goldens), deterministic


def _write_bundle(
    out_dir: Path,
    uid: str,
    key: bytes,
    helper_data: dict,
    first_holdout: np.ndarray,
) -> None:
    server_dir = out_dir / "server"
    device_dir = out_dir / "device"
    server_dir.mkdir(parents=True, exist_ok=True)
    device_dir.mkdir(parents=True, exist_ok=True)

    with (server_dir / "key_registry.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["uid", "key_hex"])
        writer.writeheader()
        writer.writerow({"uid": uid, "key_hex": key.hex()})

    with (device_dir / "helper_data.json").open("w", encoding="utf-8") as handle:
        json.dump({uid: helper_data}, handle, indent=2)
        handle.write("\n")

    response_data = {uid: {"response_bits": first_holdout.tolist()}}
    with (device_dir / "response.json").open("w", encoding="utf-8") as handle:
        json.dump(response_data, handle)
        handle.write("\n")

    readme = f"""Demo bundle
===========

Copy server/key_registry.csv to the server. Copy the two files under
device/ to the device. Start the device with:

python -m mqtt.device --uid {uid} --response-registry demo_bundle/device/response.json --helper-registry demo_bundle/device/helper_data.json

The device directory contains public helper data and one SRAM boot response
only; it must not contain the registered key.
"""
    (out_dir / "README.txt").write_text(readme, encoding="utf-8")


def _print_verification(
    extractor: FuzzyExtractor,
    golden: np.ndarray,
    holdouts: np.ndarray,
    helper_data: dict,
    registered_key: bytes,
    p1_others: np.ndarray | None = None,
    excluded_stable_count: int = 0,
) -> None:
    indices = np.asarray(helper_data["stable_indices"], dtype=np.int64)
    for boot_number, response in enumerate(holdouts, start=1):
        stable_differences = int(np.count_nonzero(response[indices] != golden[indices]))
        selected_differences = response[indices] != golden[indices]
        group_errors = sum(
            bool(np.any(selected_differences[start : start + BITS_PER_GROUP]))
            for start in range(0, len(indices), BITS_PER_GROUP)
        )
        reconstructed = extractor.rep(response, helper_data)
        print(
            f"held-out boot {boot_number}: "
            f"stable-index bit differences={stable_differences}; "
            f"11-bit groups with errors={group_errors}/"
            f"{len(indices) // BITS_PER_GROUP}; "
            f"rep key matches registered={'yes' if reconstructed == registered_key else 'no'}"
        )
    if p1_others is not None:
        print(
            f"balanced selection: p1 bias mean={np.mean(np.abs(p1_others[indices] - 0.5)):.6f}; "
            f"rows used={len(set((indices // BITS_PER_ROW).tolist()))}; "
            f"stable bits excluded by deterministic rows={excluded_stable_count}"
        )


def export_bundle(args: argparse.Namespace) -> None:
    if args.train_boots < 2:
        raise ValueError("--train-boots must be at least 2")
    if not 0 < args.threshold <= 1:
        raise ValueError("--threshold must be greater than 0 and at most 1")
    if not args.crps.exists():
        raise FileNotFoundError(f"CRPS input not found: {args.crps}")

    df = load_dataset(args.crps)
    boots, matrix = _boot_matrix(df, args.uid)
    if len(boots) < args.train_boots + 1:
        raise ValueError(
            f"uid={args.uid} has {len(boots)} boots; "
            f"need at least {args.train_boots + 1}"
        )

    training = matrix[: args.train_boots]
    holdouts = matrix[args.train_boots :]
    stability = np.asarray(compute_stability_per_uid(training, args.uid))
    golden = (training.mean(axis=0) >= 0.5).astype(np.uint8)
    mask = np.array(
        [result.stability >= args.threshold for result in stability], dtype=np.uint8
    )
    p1_others = None
    excluded_stable_count = 0
    if args.selection == "balanced":
        golden_sum, device_count, deterministic_rows = _population_training(
            df, args.train_boots, args.threshold, args.population_cache
        )
        if device_count < 2:
            raise ValueError("balanced selection requires at least two UIDs")
        target_golden = golden
        p1_others = (
            golden_sum.astype(np.int64) - target_golden.astype(np.int64)
        ) / (device_count - 1)
        selected = select_balanced_positions(
            mask,
            p1_others,
            deterministic_rows,
            BITS_PER_ROW,
            GROUP_COUNT * BITS_PER_GROUP,
            np.random.default_rng(args.seed),
        )
        balanced_mask = np.zeros_like(mask)
        balanced_mask[selected] = 1
        excluded_stable_count = int(
            sum(
                mask[row * BITS_PER_ROW : (row + 1) * BITS_PER_ROW].sum()
                for row in deterministic_rows
            )
        )
        mask = balanced_mask

    extractor = FuzzyExtractor()
    rng = np.random.default_rng(args.seed) if args.seed is not None else None
    registered_key, helper_data = extractor.gen(
        golden, mask, uid=args.uid, rng=rng
    )
    if args.selection == "balanced":
        helper_data = reorder_helper_data(
            golden,
            registered_key,
            helper_data,
            "round_robin",
        )
    stable_indices = np.asarray(helper_data["stable_indices"], dtype=np.int64)
    if len(stable_indices) != GROUP_COUNT * BITS_PER_GROUP:
        raise ValueError(
            "selected stable bits must contain exactly "
            f"{GROUP_COUNT * BITS_PER_GROUP} bits, got {len(stable_indices)}"
        )
    first_holdout = np.asarray(holdouts[0], dtype=np.uint8)
    if first_holdout.shape != (TOTAL_BITS,) or first_holdout.dtype != np.uint8:
        raise ValueError("sram_boot must have shape (655360,) and dtype uint8")
    if np.any((first_holdout != 0) & (first_holdout != 1)):
        raise ValueError("sram_boot must contain only 0 and 1")

    _write_bundle(args.out, args.uid, registered_key, helper_data, first_holdout)
    _print_verification(
        extractor,
        golden,
        holdouts,
        helper_data,
        registered_key,
        p1_others,
        excluded_stable_count,
    )
    print(f"exported demo bundle: {args.out}")


def main() -> int:
    try:
        export_bundle(parse_args())
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
