from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.stability_analysis import _split_train_holdout, compute_stability_per_uid, load_dataset  # noqa: E402
from puf.fuzzy_extractor import FuzzyExtractor  # noqa: E402
from puf.selection import reorder_helper_data, select_balanced_positions  # noqa: E402
from scripts.t2_diagnostics import load_matrices  # noqa: E402
from scripts.t2_selection_analysis import BITS_PER_ROW, REPETITION, SELECTED_BITS, deterministic_row_distances, find_deterministic_rows, leave_one_out_p1  # noqa: E402


def distribution(counts: np.ndarray) -> dict[str, int]:
    return {
        str(value): int(np.count_nonzero(counts == value))
        for value in range(6)
    } | {">=6": int(np.count_nonzero(counts >= 6))}


def expected_distribution(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for config, group in events.groupby("config"):
        total_groups = len(group) * 256
        p = group["selected_bit_differences"].sum() / (len(group) * SELECTED_BITS)
        for bucket in range(6):
            expected = total_groups * math.comb(11, bucket) * p**bucket * (1 - p) ** (11 - bucket)
            rows.append({"config": config, "bucket": str(bucket), "observed": group[f"group_{bucket}"].sum(), "binomial_expected": expected, "bit_error_rate": p})
        expected = total_groups * sum(math.comb(11, k) * p**k * (1 - p) ** (11 - k) for k in range(6, 12))
        rows.append({"config": config, "bucket": ">=6", "observed": group["group_ge6"].sum(), "binomial_expected": expected, "bit_error_rate": p})
    return pd.DataFrame(rows)


def _markdown(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in frame.itertuples(index=False, name=None))
    return "\n".join(lines)


def validate(input_path: Path, out: Path, seed: int, splits: int) -> None:
    started = time.perf_counter()
    uids, matrices = load_matrices(input_path)
    extractor = FuzzyExtractor()
    events: list[dict] = []
    attack_rows: list[dict] = []
    split_rng = np.random.default_rng(seed)
    for split in range(splits):
        trains, holdouts = [], []
        for uid in uids:
            train, holdout = _split_train_holdout(matrices[uid], 0.2, split_rng)
            trains.append(train)
            holdouts.append(holdout)
        goldens = np.asarray([(train.mean(axis=0) >= 0.5).astype(np.uint8) for train in trains])
        masks = [
            np.asarray([item.stability >= 0.90 for item in compute_stability_per_uid(train, uid)], dtype=np.uint8)
            for train, uid in zip(trains, uids)
        ]
        deterministic = find_deterministic_rows(
            deterministic_row_distances(goldens, BITS_PER_ROW), 0.01
        )
        configurations: dict[str, list[tuple[dict, np.ndarray, bytes]]] = {name: [] for name in ("legacy", "balanced_current", "balanced_round_robin", "balanced_random")}
        for device, (golden, mask) in enumerate(zip(goldens, masks)):
            p1 = leave_one_out_p1(goldens, device)
            legacy_positions = np.flatnonzero(mask)[:SELECTED_BITS]
            balanced_positions = select_balanced_positions(mask, p1, deterministic, BITS_PER_ROW, SELECTED_BITS, np.random.default_rng(seed + split * 1000 + device))
            for config, positions, reorder, reorder_rng in (
                ("legacy", legacy_positions, None, None),
                ("balanced_current", balanced_positions, None, None),
                ("balanced_round_robin", balanced_positions, "round_robin", None),
                ("balanced_random", balanced_positions, "random", np.random.default_rng(seed + split * 1000 + device)),
            ):
                enrollment_mask = np.zeros_like(mask)
                enrollment_mask[positions] = 1
                key, helper = extractor.gen(
                    golden, enrollment_mask, uid=str(device), rng=np.random.default_rng(seed + split * 1000 + device)
                )
                if reorder is not None:
                    helper = reorder_helper_data(golden, key, helper, reorder, reorder_rng)
                configurations[config].append((helper, golden, key))
                if config == "balanced_round_robin":
                    attack_rows.append(
                        {
                            "split": split,
                            "device": device,
                            "p1": p1,
                            "positions": np.asarray(helper["stable_indices"]),
                            "golden": golden,
                            "key": key,
                            "helper": helper,
                        }
                    )
        for config, records in configurations.items():
            for device, (helper, golden, key) in enumerate(records):
                for holdout_number, response in enumerate(holdouts[device], start=1):
                    positions = np.asarray(helper["stable_indices"], dtype=np.int64)
                    errors = response[positions] != golden[positions]
                    counts = errors.reshape(256, REPETITION).sum(axis=1)
                    event = {
                        "split": split,
                        "config": config,
                        "device": device,
                        "holdout": holdout_number,
                        "selected_bit_differences": int(errors.sum()),
                        "failed_groups": int(np.count_nonzero(counts >= 6)),
                        "key_reconstructed": extractor.rep(response, helper) == key,
                    }
                    event.update({f"group_{value}": int(np.count_nonzero(counts == value)) for value in range(6)})
                    event["group_ge6"] = int(np.count_nonzero(counts >= 6))
                    events.append(event)

    event_df = pd.DataFrame(events)
    event_df.to_csv(out / "events.csv", index=False)
    summary = event_df.groupby("config").agg(
        successes=("key_reconstructed", "sum"),
        total=("key_reconstructed", "size"),
        failed_groups=("failed_groups", "sum"),
        selected_bit_error_rate=("selected_bit_differences", lambda values: values.sum() / (len(values) * SELECTED_BITS)),
    ).reset_index()
    summary.to_csv(out / "summary.csv", index=False)
    expected = expected_distribution(event_df)
    expected.to_csv(out / "group_distribution.csv", index=False)

    attack_records = []
    final_attack = [row for row in attack_rows if row["split"] == splits - 1]
    for row in final_attack:
        device = row["device"]
        others = [index for index in range(len(goldens)) if index != device]
        in_p1 = goldens[others].mean(axis=0)
        guess = (in_p1[row["positions"]] >= 0.5).astype(np.uint8)
        helper = row["helper"]
        true_bits = (np.asarray(helper["W"], dtype=np.uint8) ^ row["golden"][row["positions"]]).reshape(256, 11).sum(axis=1) > 5
        guessed_bits = (np.asarray(helper["W"], dtype=np.uint8) ^ guess).reshape(256, 11).sum(axis=1) > 5
        shuffled = np.random.default_rng(seed + device).permutation(others)
        half = len(shuffled) // 2
        s, t = shuffled[:half], shuffled[half:]
        s_p1 = goldens[s].mean(axis=0)
        t_p1 = goldens[t].mean(axis=0)
        def key_errors(p1: np.ndarray) -> int:
            guessed = (
                np.asarray(helper["W"], dtype=np.uint8)
                ^ (p1[row["positions"]] >= 0.5).astype(np.uint8)
            )
            guessed_bits = guessed.reshape(256, 11).sum(axis=1) > 5
            return int(np.count_nonzero(guessed_bits != true_bits))

        attack_records.extend(
            [
                {"scope": "all_others", "device": device, "per_position_accuracy": float(np.mean(guess == row["golden"][row["positions"]])), "key_bit_errors": key_errors(in_p1)},
                {"scope": "sample_in", "device": device, "per_position_accuracy": float(np.mean((s_p1[row["positions"]] >= 0.5) == row["golden"][row["positions"]])), "key_bit_errors": key_errors(s_p1)},
                {"scope": "sample_out", "device": device, "per_position_accuracy": float(np.mean((t_p1[row["positions"]] >= 0.5) == row["golden"][row["positions"]])), "key_bit_errors": key_errors(t_p1)},
            ]
        )
    attack_df = pd.DataFrame(attack_records)
    attack_df.to_csv(out / "attack_metrics.csv", index=False)
    attack_summary = attack_df.groupby("scope")[["per_position_accuracy", "key_bit_errors"]].agg(["mean", "min", "max"])

    report = [
        "# T2b balanced selection validation",
        "",
        f"- Splits: {splits}; seed: {seed}; elapsed seconds: {time.perf_counter() - started:.3f}",
        "- Balanced selection excludes deterministic rows, chooses the lowest leave-one-out bias, and uses round-robin groups for the final configuration.",
        "",
        "## Reconstruction",
        "",
        _markdown(summary),
        "",
        "## Group error distribution versus binomial expectation",
        "",
        _markdown(expected),
        "",
        "## Final round-robin attack metrics",
        "",
        _markdown(attack_summary.reset_index()),
    ]
    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate balanced selection and grouping")
    parser.add_argument("--crps", required=True, type=Path)
    parser.add_argument("--out", default=Path("runs/t2b"), type=Path)
    parser.add_argument("--seed", default=20260506, type=int)
    parser.add_argument("--splits", default=10, type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.splits <= 0:
            raise ValueError("--splits must be positive")
        args.out.mkdir(parents=True, exist_ok=True)
        validate(args.crps, args.out, args.seed, args.splits)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
