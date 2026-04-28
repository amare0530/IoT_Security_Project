from __future__ import annotations

from pathlib import Path

import pandas as pd


def summarize_thresholds(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    summary = (
        df.groupby("threshold", as_index=False)
        .agg(
            avg_selected_bits=("selected_bits_count", "mean"),
            avg_estimated_ber=("estimated_ber_holdout", "mean"),
        )
        .sort_values("threshold")
    )
    return summary


if __name__ == "__main__":
    result = summarize_thresholds(Path("artifacts/threshold_comparison.csv"))
    print(result.to_string(index=False))
