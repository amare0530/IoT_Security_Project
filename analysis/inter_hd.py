"""Reproducible inter-device Hamming-distance evaluation."""

from __future__ import annotations

import argparse
import json
from itertools import permutations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_cohort(path: Path | None) -> list[str] | None:
    if path is None:
        return None
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compute_and_plot_inter_hd(masks_path: Path, stability_csv: Path, threshold: float = 0.9, cohort: list[str] | None = None, output_dir: Path | None = None) -> pd.DataFrame:
    """Calculate ordered-pair Inter-HD and optionally persist all evidence."""
    with masks_path.open(encoding="utf-8") as handle:
        masks_raw = json.load(handle)
    selected_bits = {
        str(item["uid"]): np.array(list(item["mask"]), dtype=np.uint8)
        for item in masks_raw
        if np.isclose(float(item["threshold"]), threshold)
    }
    if cohort is not None:
        requested = set(cohort)
        selected_bits = {uid: mask for uid, mask in selected_bits.items() if uid in requested}

    dominant: dict[str, np.ndarray] = {}
    for uid, group in pd.read_csv(stability_csv, usecols=["uid", "bit_position", "dominant_bit"], low_memory=False).groupby("uid"):
        uid = str(uid)
        if uid in selected_bits:
            dominant[uid] = group.sort_values("bit_position")["dominant_bit"].to_numpy(dtype=np.uint8)

    eligible = sorted(set(selected_bits) & set(dominant))
    rows: list[dict[str, object]] = []
    for target_a, attacker_b in permutations(eligible, 2):
        mask = selected_bits[target_a].astype(bool)
        if len(mask) != len(dominant[target_a]) or len(mask) != len(dominant[attacker_b]):
            raise ValueError(f"incompatible response length for {target_a} and {attacker_b}")
        rows.append({"target_a": target_a, "attacker_b": attacker_b, "inter_hd": float(np.mean(dominant[target_a][mask] != dominant[attacker_b][mask])), "mask_size": int(mask.sum())})

    result = pd.DataFrame(rows, columns=["target_a", "attacker_b", "inter_hd", "mask_size"])
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_dir / "inter_hd.csv", index=False)
        summary = {
            "threshold": threshold,
            "requested_cohort_size": len(cohort) if cohort is not None else None,
            "eligible_devices": eligible,
            "device_count": len(eligible),
            "ordered_pair_count": len(result),
            "mean_inter_hd": float(result["inter_hd"].mean()) if not result.empty else None,
            "std_inter_hd": float(result["inter_hd"].std(ddof=0)) if not result.empty else None,
        }
        (output_dir / "inter_hd_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if not result.empty:
            plt.figure(figsize=(10, 6))
            plt.hist(result["inter_hd"], bins=30, color="skyblue", edgecolor="white")
            plt.axvline(0.5, color="red", linestyle="--", label="Ideal (0.5)")
            plt.axvline(summary["mean_inter_hd"], color="green", label="Observed mean")
            plt.xlabel("Normalized Hamming distance")
            plt.ylabel("Ordered pair count")
            plt.legend()
            plt.tight_layout()
            plt.savefig(output_dir / "inter_hd_dist.png", dpi=160)
            plt.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create reproducible Inter-HD artifacts")
    parser.add_argument("--masks", type=Path, required=True)
    parser.add_argument("--stability-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.90)
    parser.add_argument("--cohort-file", type=Path)
    args = parser.parse_args()
    result = compute_and_plot_inter_hd(args.masks, args.stability_summary, args.threshold, load_cohort(args.cohort_file), args.output_dir)
    print(f"ordered pairs: {len(result)}")


if __name__ == "__main__":
    main()
