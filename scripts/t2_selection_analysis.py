from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.stability_analysis import (  # noqa: E402
    _split_train_holdout,
    compute_stability_per_uid,
    load_dataset,
)
from puf.fuzzy_extractor import FuzzyExtractor  # noqa: E402

TOTAL_BITS = 655_360
ROWS = 160
BITS_PER_ROW = 4_096
SELECTED_BITS = 2_816
REPETITION = 11


def deterministic_row_distances(goldens: np.ndarray, bits_per_row: int) -> pd.DataFrame:
    if goldens.ndim != 2 or goldens.shape[1] % bits_per_row:
        raise ValueError("goldens must be a 2-D matrix divisible by bits_per_row")
    rows = goldens.reshape(goldens.shape[0], -1, bits_per_row)
    records = []
    for row in range(rows.shape[1]):
        distances = []
        for left in range(rows.shape[0]):
            for right in range(left + 1, rows.shape[0]):
                distances.append(np.count_nonzero(rows[left, row] != rows[right, row]) / bits_per_row)
        records.append(
            {
                "row": row,
                "mean_distance": float(np.mean(distances)),
                "min_distance": float(np.min(distances)),
                "max_distance": float(np.max(distances)),
            }
        )
    return pd.DataFrame(records)


def find_deterministic_rows(row_distances: pd.DataFrame, threshold: float) -> set[int]:
    return set(
        row_distances.loc[
            row_distances["mean_distance"] <= threshold, "row"
        ].astype(int)
    )


def leave_one_out_p1(goldens: np.ndarray, device: int) -> np.ndarray:
    if not 0 <= device < len(goldens):
        raise IndexError("device index out of range")
    others = np.delete(goldens, device, axis=0)
    return others.mean(axis=0)


def select_positions(
    stable_mask: np.ndarray,
    p1_others: np.ndarray,
    deterministic_rows: set[int],
    bits_per_row: int,
    count: int,
    per_row_cap: int | None = None,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    if len(stable_mask) != len(p1_others):
        raise ValueError("stable mask and p1_others must have the same length")
    candidate = np.flatnonzero(stable_mask == 1)
    candidate = candidate[
        np.array([index // bits_per_row not in deterministic_rows for index in candidate])
    ]
    if per_row_cap is not None and per_row_cap <= 0:
        raise ValueError("per_row_cap must be positive")
    rng = rng or np.random.default_rng(0)
    tie_break = rng.random(len(candidate))
    order = np.lexsort((tie_break, np.abs(p1_others[candidate] - 0.5)))
    selected: list[int] = []
    row_counts: dict[int, int] = {}
    for index in candidate[order]:
        row = int(index // bits_per_row)
        if per_row_cap is not None and row_counts.get(row, 0) >= per_row_cap:
            continue
        selected.append(int(index))
        row_counts[row] = row_counts.get(row, 0) + 1
        if len(selected) == count:
            return np.asarray(sorted(selected), dtype=np.int64)
    raise ValueError(
        f"only {len(selected)} positions available after row exclusion/cap; need {count}"
    )


def _majority(bits: np.ndarray) -> np.ndarray:
    return (bits.reshape(-1, REPETITION).sum(axis=1) > REPETITION / 2).astype(np.uint8)


def _group_consistency(p1: np.ndarray, positions: np.ndarray) -> float:
    directions = p1[positions].reshape(-1, REPETITION) >= 0.5
    return float(np.mean(np.maximum(directions.mean(axis=1), 1 - directions.mean(axis=1))))


def _markdown_table(frame: pd.DataFrame, index: bool = False) -> str:
    table = frame.reset_index() if index else frame
    columns = [str(column) for column in table.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in table.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _method_metrics(
    name: str,
    positions_by_device: list[np.ndarray],
    goldens: np.ndarray,
    holdouts: list[np.ndarray],
    extractor: FuzzyExtractor,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    holdout_rows = []
    for device, positions in enumerate(positions_by_device):
        p1 = leave_one_out_p1(goldens, device)
        rng = np.random.default_rng(seed + device)
        mask = np.zeros(goldens.shape[1], dtype=np.uint8)
        mask[positions] = 1
        key, helper = extractor.gen(goldens[device], mask, uid=str(device), rng=rng)
        true_bits = _majority(
            np.asarray(helper["W"], dtype=np.uint8) ^ goldens[device][positions]
        )
        guessed_response = (p1[positions] >= 0.5).astype(np.uint8)
        guessed_bits = _majority(
            np.asarray(helper["W"], dtype=np.uint8) ^ guessed_response
        )
        rows.append(
            {
                "device": device,
                "method": name,
                "per_position_accuracy": float(np.mean(guessed_response == goldens[device][positions])),
                "key_bit_errors": int(np.count_nonzero(guessed_bits != true_bits)),
                "group_direction_consistency": _group_consistency(p1, positions),
            }
        )
        for holdout_number, response in enumerate(holdouts[device], start=1):
            differing = response[positions] != goldens[device][positions]
            group_errors = differing.reshape(-1, REPETITION).sum(axis=1)
            reconstructed = extractor.rep(response, helper)
            holdout_rows.append(
                {
                    "device": device,
                    "method": name,
                    "holdout": holdout_number,
                    "selected_bit_differences": int(differing.sum()),
                    "error_groups": int(np.count_nonzero(group_errors)),
                    "failed_groups": int(np.count_nonzero(group_errors >= 6)),
                    "key_reconstructed": reconstructed == key,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(holdout_rows)


def _write_report(
    out: Path,
    row_distances: pd.DataFrame,
    deterministic: set[int],
    stable_counts: pd.DataFrame,
    summaries: pd.DataFrame,
    holdouts: pd.DataFrame,
    split_description: str,
    threshold: float,
    per_row_cap: int | None,
) -> None:
    lines = [
        "# T2 selection analysis",
        "",
        f"- Training/holdout split: {split_description}",
        f"- Deterministic-row threshold: mean cross-device normalized Hamming distance <= {threshold}",
        f"- Deterministic rows found: {sorted(deterministic)}",
        "- This holdout checks execution and reconstruction on 168 samples; it is not a reliability proof.",
        "",
        "## Row distances",
        "",
        _markdown_table(row_distances, index=False),
        "",
        "## Stable-bit impact",
        "",
        _markdown_table(stable_counts, index=False),
        "",
        "## Selection and attacker metrics",
        "",
        f"Per-row cap for B in this run: {per_row_cap if per_row_cap is not None else 'none'}",
        "",
        summaries.groupby("method")[["per_position_accuracy", "key_bit_errors", "group_direction_consistency"]]
        .agg(["mean", "min", "max"])
        .pipe(_markdown_table, index=True),
        "",
        "## Holdout reconstruction",
        "",
        holdouts.groupby("method")[["selected_bit_differences", "error_groups", "failed_groups", "key_reconstructed"]]
        .agg(["mean", "min", "max"])
        .pipe(_markdown_table, index=True),
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(input_path: Path, out: Path, row_threshold: float, per_row_cap: int | None, seed: int) -> None:
    df = load_dataset(input_path)
    matrices: dict[str, np.ndarray] = {}
    for uid, group in df.groupby("uid", observed=True):
        dates = sorted(group["created_at"].unique())
        bitstreams = []
        for date in dates:
            boot = group[group["created_at"] == date].sort_values("address")
            if len(boot) != ROWS or boot["address"].duplicated().any():
                raise ValueError(f"uid={uid} has invalid rows or addresses at {date}")
            bitstreams.append("".join(boot["bitstream"]))
        if len(bitstreams) != 9 or any(len(bits) != TOTAL_BITS for bits in bitstreams):
            raise ValueError(f"uid={uid} must have 9 complete boots")
        matrices[str(uid)] = (
            np.frombuffer("".join(bitstreams).encode("ascii"), dtype=np.uint8).reshape(9, TOTAL_BITS)
            - ord("0")
        )
    if len(matrices) < 2:
        raise ValueError("at least two devices are required")

    uids = sorted(matrices)
    train, holdouts = [], []
    split_description = "analysis._split_train_holdout(matrix, holdout_ratio=0.2, rng=default_rng(42)); 7 shuffled training boots and 2 holdouts"
    split_rng = np.random.default_rng(42)
    for uid in uids:
        train_matrix, holdout_matrix = _split_train_holdout(
            matrices[uid], 0.2, split_rng
        )
        train.append(train_matrix)
        holdouts.append(holdout_matrix)
    goldens = np.asarray([(boots.mean(axis=0) >= 0.5).astype(np.uint8) for boots in train])
    row_distances = deterministic_row_distances(goldens, BITS_PER_ROW)
    deterministic = find_deterministic_rows(row_distances, row_threshold)
    row_distances.to_csv(out / "row_distance.csv", index=False)
    row_distances.sort_values("mean_distance").to_csv(
        out / "row_distance_sorted.csv", index=False
    )
    histogram, edges = np.histogram(row_distances["mean_distance"], bins=20)
    pd.DataFrame(
        {"bin_left": edges[:-1], "bin_right": edges[1:], "count": histogram}
    ).to_csv(out / "row_distance_histogram.csv", index=False)

    stable_masks = []
    for device, boots in enumerate(train):
        stability = compute_stability_per_uid(boots, uids[device])
        stable_masks.append(np.asarray([item.stability >= 0.90 for item in stability], dtype=np.uint8))
    stable_counts = pd.DataFrame(
        [
            {
                "uid": uid,
                "stable_bits": int(mask.sum()),
                "stable_in_deterministic_rows": int(sum(mask[row * BITS_PER_ROW : (row + 1) * BITS_PER_ROW].sum() for row in deterministic)),
                "stable_in_deterministic_ratio": float(sum(mask[row * BITS_PER_ROW : (row + 1) * BITS_PER_ROW].sum() for row in deterministic) / mask.sum()),
                "stable_after_exclusion": int(mask.sum() - sum(mask[row * BITS_PER_ROW : (row + 1) * BITS_PER_ROW].sum() for row in deterministic)),
            }
            for uid, mask in zip(uids, stable_masks)
        ]
    )
    stable_counts.to_csv(out / "stable_counts.csv", index=False)

    positions: dict[str, list[np.ndarray]] = {"A": [], "B": [], "C": []}
    for device, mask in enumerate(stable_masks):
        p1 = leave_one_out_p1(goldens, device)
        positions["A"].append(np.flatnonzero(mask)[:SELECTED_BITS])
        positions["B"].append(select_positions(mask, p1, deterministic, BITS_PER_ROW, SELECTED_BITS, per_row_cap, np.random.default_rng(seed + device)))
        positions["C"].append(select_positions(mask, p1, deterministic, BITS_PER_ROW, SELECTED_BITS, None, np.random.default_rng(seed + device)))

    extractor = FuzzyExtractor()
    metric_frames, holdout_frames = [], []
    for method in ("A", "B", "C"):
        metrics, holdout_metrics = _method_metrics(method, positions[method], goldens, holdouts, extractor, seed)
        metric_frames.append(metrics)
        holdout_frames.append(holdout_metrics)
    summaries = pd.concat(metric_frames, ignore_index=True)
    holdout_summary = pd.concat(holdout_frames, ignore_index=True)
    summaries.to_csv(out / "method_metrics.csv", index=False)
    holdout_summary.to_csv(out / "holdout_metrics.csv", index=False)
    _write_report(out, row_distances, deterministic, stable_counts, summaries, holdout_summary, split_description, row_threshold, per_row_cap)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only T2 selection analysis")
    parser.add_argument("--crps", required=True, type=Path)
    parser.add_argument("--out", default=Path("runs/t2"), type=Path)
    parser.add_argument("--row-threshold", default=0.01, type=float)
    parser.add_argument("--per-row-cap", type=int)
    parser.add_argument("--seed", default=20260506, type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        analyze(args.crps, args.out, args.row_threshold, args.per_row_cap, args.seed)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
