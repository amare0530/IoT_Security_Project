from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.stability_analysis import _split_train_holdout, compute_stability_per_uid, load_dataset  # noqa: E402
from puf.fuzzy_extractor import FuzzyExtractor  # noqa: E402
from scripts.t2_selection_analysis import (  # noqa: E402
    BITS_PER_ROW,
    REPETITION,
    SELECTED_BITS,
    deterministic_row_distances,
    find_deterministic_rows,
    leave_one_out_p1,
    select_positions,
)

TOTAL_BITS = 655_360
ROWS = 160
DEVICES = 84


def markdown_table(frame: pd.DataFrame, index: bool = False) -> str:
    table = frame.reset_index() if index else frame
    columns = [str(column) for column in table.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in table.itertuples(index=False, name=None))
    return "\n".join(lines)


def load_matrices(path: Path) -> tuple[list[str], dict[str, np.ndarray]]:
    df = load_dataset(path)
    matrices: dict[str, np.ndarray] = {}
    for uid, group in df.groupby("uid", observed=True):
        boots = []
        for created_at, boot in group.groupby("created_at", sort=True):
            if len(boot) != ROWS or boot["address"].duplicated().any():
                raise ValueError(f"uid={uid} has invalid rows or duplicate addresses at {created_at}")
            bits = "".join(boot.sort_values("address")["bitstream"].tolist())
            if len(bits) != TOTAL_BITS:
                raise ValueError(f"uid={uid} boot at {created_at} has {len(bits)} bits")
            boots.append(bits)
        if len(boots) != 9:
            raise ValueError(f"uid={uid} must have exactly 9 boots, got {len(boots)}")
        matrices[str(uid)] = (np.frombuffer("".join(boots).encode("ascii"), dtype=np.uint8).reshape(9, TOTAL_BITS) - ord("0"))
    uids = sorted(matrices)
    if len(uids) != DEVICES:
        raise ValueError(f"expected {DEVICES} devices, got {len(uids)}")
    return uids, matrices


def build_enrollment(matrices: dict[str, np.ndarray], uids: list[str]) -> tuple[np.ndarray, list[np.ndarray]]:
    goldens = np.asarray([(matrices[uid].mean(axis=0) >= 0.5).astype(np.uint8) for uid in uids])
    masks = [
        np.asarray([item.stability >= 0.90 for item in compute_stability_per_uid(matrices[uid], uid)], dtype=np.uint8)
        for uid in uids
    ]
    return goldens, masks


def selected_row_stats(positions: np.ndarray) -> dict[str, object]:
    counts = np.bincount(positions // BITS_PER_ROW, minlength=ROWS)
    top = sorted(enumerate(counts), key=lambda item: (-item[1], item[0]))[:10]
    groups = positions.reshape(-1, REPETITION)
    return {
        "rows_used": int(np.count_nonzero(counts)),
        "max_per_row": int(counts.max()),
        "top_10_rows": "; ".join(f"{row}:{count}" for row, count in top if count),
        "within_group_adjacent_gap_median": float(np.median(np.diff(groups, axis=1))),
        "groups_same_row": int(np.sum((groups // BITS_PER_ROW == (groups[:, :1] // BITS_PER_ROW)).all(axis=1))),
    }


def candidate_count(mask: np.ndarray, deterministic: set[int]) -> int:
    return int(sum(mask[row * BITS_PER_ROW : (row + 1) * BITS_PER_ROW].sum() for row in range(ROWS) if row not in deterministic))


def choose_methods(goldens: np.ndarray, masks: list[np.ndarray], deterministic: set[int], seed: int, cap: int | None) -> dict[str, list[np.ndarray]]:
    methods: dict[str, list[np.ndarray]] = {"B": [], "C": []}
    for device, mask in enumerate(masks):
        p1 = leave_one_out_p1(goldens, device)
        methods["B"].append(select_positions(mask, p1, deterministic, BITS_PER_ROW, SELECTED_BITS, cap, np.random.default_rng(seed + device)))
        methods["C"].append(select_positions(mask, p1, deterministic, BITS_PER_ROW, SELECTED_BITS, None, np.random.default_rng(seed + device)))
    return methods


def attack_metrics(goldens: np.ndarray, positions: list[np.ndarray], attacker_p1: list[np.ndarray], seed: int) -> pd.DataFrame:
    extractor = FuzzyExtractor()
    rows = []
    for device, selected in enumerate(positions):
        mask = np.zeros(goldens.shape[1], dtype=np.uint8)
        mask[selected] = 1
        key, helper = extractor.gen(goldens[device], mask, uid=str(device), rng=np.random.default_rng(seed + device))
        true_bits = (np.asarray(helper["W"], dtype=np.uint8) ^ goldens[device][selected]).reshape(-1, REPETITION).sum(axis=1) > REPETITION / 2
        guess = (attacker_p1[device][selected] >= 0.5).astype(np.uint8)
        guessed_bits = (np.asarray(helper["W"], dtype=np.uint8) ^ guess).reshape(-1, REPETITION).sum(axis=1) > REPETITION / 2
        rows.append({
            "device": device,
            "per_position_accuracy": float(np.mean(guess == goldens[device][selected])),
            "key_bit_errors": int(np.count_nonzero(guessed_bits != true_bits)),
        })
    return pd.DataFrame(rows)


def error_distribution(error_counts: np.ndarray) -> dict[str, int]:
    return {
        "0": int(np.count_nonzero(error_counts == 0)),
        "1": int(np.count_nonzero(error_counts == 1)),
        "2": int(np.count_nonzero(error_counts == 2)),
        "3": int(np.count_nonzero(error_counts == 3)),
        "4": int(np.count_nonzero(error_counts == 4)),
        "5": int(np.count_nonzero(error_counts == 5)),
        ">=6": int(np.count_nonzero(error_counts >= 6)),
    }


def distribution_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, group in events.groupby("method"):
        observed = {bucket: 0 for bucket in ("0", "1", "2", "3", "4", "5", ">=6")}
        total_errors = 0
        total_groups = 0
        for value in group["error_distribution"]:
            total_errors += sum(int(bucket) * count for bucket, count in value.items() if bucket != ">=6")
            total_errors += 6 * value[">=6"]
            total_groups += sum(value.values())
            for bucket, count in value.items():
                observed[bucket] += count
        p = total_errors / (total_groups * REPETITION)
        expected = {
            bucket: (
                total_groups * math.comb(REPETITION, int(bucket)) * p ** int(bucket) * (1 - p) ** (REPETITION - int(bucket))
                if bucket != ">=6"
                else total_groups * sum(math.comb(REPETITION, k) * p ** k * (1 - p) ** (REPETITION - k) for k in range(6, REPETITION + 1))
            )
            for bucket in observed
        }
        for bucket in observed:
            rows.append({"method": method, "bucket": bucket, "observed": observed[bucket], "binomial_expected": expected[bucket], "observed_bit_error_rate": p})
    return pd.DataFrame(rows)


def evaluate_assignments(
    error_masks: list[np.ndarray], positions: list[np.ndarray]
) -> pd.DataFrame:
    rows = []
    for sample, errors in enumerate(error_masks):
        device = sample // 2
        selected = positions[device]
        order = np.arange(SELECTED_BITS)
        assignments = {
            "current": order.reshape(256, 11),
            "round_robin": np.argsort(order % 256).reshape(256, 11),
            "random": np.random.default_rng(20260506 + device).permutation(order).reshape(256, 11),
        }
        for method, groups in assignments.items():
            counts = errors[groups].sum(axis=1)
            rows.append({
                "device": device,
                "sample": sample,
                "assignment": method,
                "failed_groups": int(np.count_nonzero(counts >= 6)),
                "groups_ge3": int(np.count_nonzero(counts >= 3)),
            })
    return pd.DataFrame(rows)


def run_split(
    goldens: np.ndarray,
    holdouts: np.ndarray,
    masks: list[np.ndarray],
    deterministic: set[int],
    seed: int,
    cap: int | None,
) -> tuple[pd.DataFrame, dict[str, list[np.ndarray]], dict[str, list[np.ndarray]]]:
    methods = choose_methods(goldens, masks, deterministic, seed, cap)
    methods["A"] = [np.flatnonzero(mask)[:SELECTED_BITS] for mask in masks]
    events = []
    error_masks: dict[str, list[np.ndarray]] = {name: [] for name in methods}
    extractor = FuzzyExtractor()
    for name, positions in methods.items():
        for device, selected in enumerate(positions):
            mask = np.zeros(TOTAL_BITS, dtype=np.uint8)
            mask[selected] = 1
            key, helper = extractor.gen(goldens[device], mask, uid=str(device), rng=np.random.default_rng(seed + device))
            for holdout_number, response in enumerate(holdouts[device], start=1):
                selected_errors = response[selected] != goldens[device][selected]
                counts = selected_errors.reshape(256, 11).sum(axis=1)
                error_masks[name].append(selected_errors)
                events.append({
                    "method": name,
                    "device": device,
                    "holdout": holdout_number,
                    "selected_bit_differences": int(selected_errors.sum()),
                    "failed_groups": int(np.count_nonzero(counts >= 6)),
                    "error_distribution": error_distribution(counts),
                    "key_reconstructed": extractor.rep(response, helper) == key,
                })
    return pd.DataFrame(events), methods, error_masks


def analyze(input_path: Path, out: Path, seed: int, splits: int) -> None:
    uids, matrices = load_matrices(input_path)
    all_goldens, all_masks = build_enrollment(matrices, uids)
    distances = deterministic_row_distances(all_goldens, BITS_PER_ROW)
    deterministic = find_deterministic_rows(distances, 0.01)
    distances.to_csv(out / "d1_row_distance.csv", index=False)
    stable = []
    for uid, mask in zip(uids, all_masks):
        inside = sum(mask[row * BITS_PER_ROW : (row + 1) * BITS_PER_ROW].sum() for row in deterministic)
        stable.append({"uid": uid, "stable_bits": int(mask.sum()), "deterministic_stable_bits": int(inside), "deterministic_ratio": float(inside / mask.sum()), "after_exclusion": int(mask.sum() - inside)})
    stable_df = pd.DataFrame(stable)
    stable_df.to_csv(out / "d1_stable_counts.csv", index=False)

    d2_rows = []
    for cap, label in [(None, "C"), (30, "B_cap30")]:
        methods = choose_methods(all_goldens, all_masks, deterministic, seed, cap)
        for device, positions in enumerate(methods["C" if cap is None else "B"]):
            p1 = leave_one_out_p1(all_goldens, device)
            stats = selected_row_stats(positions)
            stats.update({"uid": uids[device], "method": label, "candidate_count": candidate_count(all_masks[device], deterministic), "p1_bias_mean": float(np.mean(np.abs(p1[positions] - 0.5))), "p1_bias_median": float(np.median(np.abs(p1[positions] - 0.5))), "p1_bias_max": float(np.max(np.abs(p1[positions] - 0.5)))})
            d2_rows.append(stats)
    d2_df = pd.DataFrame(d2_rows)
    d2_df.to_csv(out / "d2_selection_stats.csv", index=False)

    other_count = len(uids) - 1
    d3_rows = []
    for device in range(len(uids)):
        others = [index for index in range(len(uids)) if index != device]
        split_rng = np.random.default_rng(seed + device)
        shuffled = split_rng.permutation(others)
        midpoint = other_count // 2
        s, t = shuffled[:midpoint], shuffled[midpoint:]
        s_p1 = all_goldens[s].mean(axis=0)
        t_p1 = all_goldens[t].mean(axis=0)
        selected_s = select_positions(all_masks[device], s_p1, deterministic, BITS_PER_ROW, SELECTED_BITS, None, np.random.default_rng(seed + device))
        d3_rows.append({"device": device, "sample_in_accuracy": float(np.mean((s_p1[selected_s] >= 0.5) == all_goldens[device][selected_s])), "sample_in_key_errors": int(attack_metrics(all_goldens, [selected_s], [s_p1], seed)["key_bit_errors"].iloc[0]), "sample_out_accuracy": float(np.mean((t_p1[selected_s] >= 0.5) == all_goldens[device][selected_s])), "sample_out_key_errors": int(attack_metrics(all_goldens, [selected_s], [t_p1], seed)["key_bit_errors"].iloc[0]), "s_devices": len(s), "t_devices": len(t), "self_in_s": device in s, "self_in_t": device in t})
    d3_df = pd.DataFrame(d3_rows)
    d3_df.to_csv(out / "d3_sample_out_attack.csv", index=False)

    split_rng = np.random.default_rng(seed)
    seven_train, two_holdout = [], []
    for uid in uids:
        seven, two = _split_train_holdout(matrices[uid], 0.2, split_rng)
        seven_train.append(seven)
        two_holdout.append(two)
    split_goldens = np.asarray([(boots.mean(axis=0) >= 0.5).astype(np.uint8) for boots in seven_train])
    split_masks = [np.asarray([item.stability >= 0.90 for item in compute_stability_per_uid(boots, uid)], dtype=np.uint8) for boots, uid in zip(seven_train, uids)]
    split_distances = deterministic_row_distances(split_goldens, BITS_PER_ROW)
    split_deterministic = find_deterministic_rows(split_distances, 0.01)
    events, split_positions, split_errors = run_split(
        split_goldens, np.asarray(two_holdout), split_masks, split_deterministic, seed, 30
    )
    event_rows = []
    event_indices = {method: 0 for method in split_positions}
    for event in events.to_dict("records"):
        method = event["method"]
        errors = split_errors[method][event_indices[method]]
        event_indices[method] += 1
        selected = split_positions[method][event["device"]]
        stable_positions = np.flatnonzero(split_masks[event["device"]])
        full_diffs = int(
            np.count_nonzero(
                two_holdout[event["device"]][event["holdout"] - 1][stable_positions]
                != split_goldens[event["device"]][stable_positions]
            )
        )
        error_indices = selected[np.flatnonzero(errors)]
        event.update(
            {
                "stable_position_differences": full_diffs,
                "error_positions": ",".join(map(str, error_indices.tolist())),
                "error_rows": ",".join(map(str, (error_indices // BITS_PER_ROW).tolist())),
                "error_offsets": ",".join(map(str, (error_indices % BITS_PER_ROW).tolist())),
                "error_gaps": ",".join(map(str, np.diff(error_indices).tolist())),
            }
        )
        event_rows.append(event)
    event_frame = pd.DataFrame(event_rows)
    event_frame[event_frame["failed_groups"] > 0].to_csv(out / "d4_failed_events.csv", index=False)
    events.to_csv(out / "d4_events.csv", index=False)
    distribution_summary(events).to_csv(out / "d4_group_distribution.csv", index=False)

    d5_rows = []
    d5_distribution_rows = []
    d6_frames = []
    split_times = []
    for split_number in range(splits):
        split_rng = np.random.default_rng(seed + split_number)
        trains, holds = [], []
        for uid in uids:
            train, hold = _split_train_holdout(matrices[uid], 0.2, split_rng)
            trains.append(train)
            holds.append(hold)
        gs = np.asarray([(train.mean(axis=0) >= 0.5).astype(np.uint8) for train in trains])
        ms = [np.asarray([item.stability >= 0.90 for item in compute_stability_per_uid(train, uid)], dtype=np.uint8) for train, uid in zip(trains, uids)]
        det = find_deterministic_rows(deterministic_row_distances(gs, BITS_PER_ROW), 0.01)
        ev, positions, errors = run_split(gs, np.asarray(holds), ms, det, seed + split_number, 30)
        for method in ("B", "C"):
            subset = ev[ev["method"] == method]
            d5_rows.append({"split": split_number, "method": method, "reconstruction_successes": int(subset["key_reconstructed"].sum()), "total": len(subset), "failed_groups": int(subset["failed_groups"].sum())})
            distribution = {bucket: 0 for bucket in ("0", "1", "2", "3", "4", "5", ">=6")}
            for value in subset["error_distribution"]:
                for bucket, count in value.items():
                    distribution[bucket] += count
            d5_distribution_rows.append({"split": split_number, "method": method, **distribution})
            d6_frames.append(
                evaluate_assignments(errors[method], positions[method]).assign(
                    method=method, split=split_number
                )
            )
    d5_df = pd.DataFrame(d5_rows)
    d5_df.to_csv(out / "d5_split_summary.csv", index=False)
    pd.DataFrame(d5_distribution_rows).to_csv(out / "d5_group_distribution.csv", index=False)
    d6_df = pd.concat(d6_frames, ignore_index=True)
    d6_df.to_csv(out / "d6_assignment_summary.csv", index=False)

    report = [
        "# T2a-2 diagnostics",
        "",
        f"- Devices: {len(uids)}; D5 splits: {splits}; seed: {seed}",
        f"- D1 all-9 deterministic rows: {sorted(deterministic)}",
        "- Holdout results are execution/reconstruction checks, not reliability proof.",
        "",
        "## D1 all-nine stability",
        "",
        markdown_table(stable_df[["stable_bits", "deterministic_stable_bits", "deterministic_ratio", "after_exclusion"]].agg(["mean", "min", "max"]), True),
        "",
        "## D2 selection statistics",
        "",
        markdown_table(d2_df.groupby("method")[["rows_used", "max_per_row", "p1_bias_mean", "p1_bias_median", "p1_bias_max", "groups_same_row", "candidate_count"]].agg(["mean", "min", "max"]), True),
        "",
        "## D3 sample-out attack",
        "",
        markdown_table(d3_df[["sample_in_accuracy", "sample_in_key_errors", "sample_out_accuracy", "sample_out_key_errors"]].agg(["mean", "min", "max"]), True),
        "",
        "## D4/D5/D6",
        "",
        "### D4 observed versus independent-error binomial expectation",
        "",
        markdown_table(distribution_summary(events), False),
        "",
        markdown_table(events.groupby("method")[["selected_bit_differences", "failed_groups", "key_reconstructed"]].agg(["mean", "sum", "min", "max"]), True),
        "",
        markdown_table(d5_df.groupby("method")[["reconstruction_successes", "total", "failed_groups"]].sum(), True),
        "",
        markdown_table(d6_df.groupby(["method", "assignment"])[["failed_groups", "groups_ge3"]].sum(), True),
        "",
        "## Expected values and limitations",
        "",
        "D4 includes per-event error distributions in d4_events.csv. Independent-error binomial expectations should be compared with those observed counts using the overall observed bit error rate; clustered failures are evidence against treating repetition errors as independent.",
    ]
    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T2a-2 diagnostic analysis")
    parser.add_argument("--crps", required=True, type=Path)
    parser.add_argument("--out", default=Path("runs/t2d"), type=Path)
    parser.add_argument("--seed", default=20260506, type=int)
    parser.add_argument("--splits", default=10, type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.splits <= 0:
            raise ValueError("--splits must be positive")
        args.out.mkdir(parents=True, exist_ok=True)
        analyze(args.crps, args.out, args.seed, args.splits)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
