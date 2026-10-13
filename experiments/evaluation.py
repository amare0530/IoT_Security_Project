"""Create traceable summaries and charts from an evaluation run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def summarize_thresholds(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return (df.groupby("threshold", as_index=False).agg(devices=("uid", "nunique"), avg_selected_bits=("selected_bits_count", "mean"), avg_estimated_ber=("estimated_ber_holdout", "mean")).sort_values("threshold"))


def build_manifest(output_dir: Path, threshold_path: Path, fuzzy_path: Path | None, cohort_file: Path | None, seed: int) -> dict[str, object]:
    cohort = [] if cohort_file is None else [line.strip() for line in cohort_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": seed,
        "inputs": {
            "threshold_comparison": str(threshold_path),
            "threshold_comparison_bytes": threshold_path.stat().st_size,
            "fuzzy_results": str(fuzzy_path) if fuzzy_path else None,
            "fuzzy_results_bytes": fuzzy_path.stat().st_size if fuzzy_path else None,
        },
        "cohort": cohort,
        "cohort_size": len(cohort) if cohort_file else None,
        "output_dir": str(output_dir),
    }


def write_evaluation(output_dir: Path, threshold_path: Path, fuzzy_path: Path | None, cohort_file: Path | None, seed: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_thresholds(threshold_path)
    summary.to_csv(output_dir / "threshold_summary.csv", index=False)
    plt.figure(figsize=(7, 4))
    plt.plot(summary["threshold"], summary["avg_estimated_ber"], marker="o")
    plt.xlabel("Stability threshold")
    plt.ylabel("Mean holdout BER")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "threshold_vs_ber.png", dpi=160)
    plt.close()
    manifest = build_manifest(output_dir, threshold_path, fuzzy_path, cohort_file, seed)
    manifest["thresholds"] = summary["threshold"].tolist()
    (output_dir / "evaluation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a reproducible evaluation run")
    parser.add_argument("--threshold-comparison", type=Path, required=True)
    parser.add_argument("--fuzzy-results", type=Path)
    parser.add_argument("--cohort-file", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    write_evaluation(args.output_dir, args.threshold_comparison, args.fuzzy_results, args.cohort_file, args.seed)


if __name__ == "__main__":
    main()
