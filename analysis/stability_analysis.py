from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"uid", "address", "data", "created_at"}


@dataclass(frozen=True)
class StabilityResult:
    uid: str
    bit_position: int
    p_zero: float
    p_one: float
    stability: float
    dominant_bit: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute reliability-aware bit masks from SRAM-PUF CSV data."
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to crps.csv")
    parser.add_argument(
        "--output-dir",
        default=Path("artifacts"),
        type=Path,
        help="Directory for outputs",
    )
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=[0.90, 0.95, 0.98, 0.99],
        help="Stability thresholds",
    )
    parser.add_argument(
        "--holdout-ratio",
        type=float,
        default=0.2,
        help="Per-UID holdout ratio for BER estimation",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df["uid"] = df["uid"].astype("category")  # 節省 RAM
    df["address"] = df["address"].astype(str)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    if df["created_at"].isna().any():
        raise ValueError("created_at contains invalid datetime values")

    # 直接在 row level 把逗號字串轉成 256-bit 二進位字串，不 explode
    def row_to_bitstream(data_str: str) -> str:
        return "".join(format(int(b), "08b") for b in data_str.split(","))

    print("正在轉換 bitstream（row-level，無 explode）...")
    df["bitstream"] = df["data"].apply(row_to_bitstream)

    # 完整性檢查：每列的 bitstream 長度必須一致（依 uid 分組）
    bit_lengths = df.groupby("uid", observed=True)["bitstream"].apply(
        lambda s: s.str.len().unique()
    )
    for uid, lengths in bit_lengths.items():
        if len(lengths) != 1:
            raise ValueError(f"Inconsistent bitstream length for uid={uid}: {lengths}")

    # data 欄位已不需要，釋放記憶體
    df = df.drop(columns=["data"])

    return df.sort_values(["uid", "created_at", "address"]).reset_index(drop=True)


def add_bitstream_columns(df: pd.DataFrame) -> pd.DataFrame:
    # bitstream 已在 load_dataset 建立，這裡只補 sample_index
    out = df.copy()
    out["sample_index"] = out.groupby("uid", observed=True).cumcount()
    return out


def sample_level_bit_matrix(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    matrices: Dict[str, np.ndarray] = {}

    samples = (
        df.groupby(["uid", "sample_index"], observed=True)["bitstream"]
        .first()
        .reset_index()
        .sort_values(["uid", "sample_index"])
    )

    for uid, group in samples.groupby("uid", observed=True):
        bitstreams = group["bitstream"].tolist()
        if not bitstreams:
            continue

        bit_len = len(bitstreams[0])
        if any(len(b) != bit_len for b in bitstreams):
            raise ValueError(f"Inconsistent bitstream length for uid={uid}")

        # frombuffer 比 list comprehension 快 3-5 倍
        matrices[str(uid)] = np.frombuffer(
            "".join(bitstreams).encode(), dtype=np.uint8
        ).reshape(len(bitstreams), bit_len) - ord("0")

    return matrices


def compute_stability_per_uid(matrix: np.ndarray, uid: str) -> List[StabilityResult]:
    p_one = matrix.mean(axis=0)
    p_zero = 1.0 - p_one
    stability = np.maximum(p_zero, p_one)
    dominant = (p_one >= 0.5).astype(int)

    results: List[StabilityResult] = []
    for idx in range(matrix.shape[1]):
        results.append(
            StabilityResult(
                uid=uid,
                bit_position=idx,
                p_zero=float(p_zero[idx]),
                p_one=float(p_one[idx]),
                stability=float(stability[idx]),
                dominant_bit=int(dominant[idx]),
            )
        )
    return results


def stability_table(matrices: Dict[str, np.ndarray]) -> pd.DataFrame:
    rows: List[StabilityResult] = []
    for uid, matrix in matrices.items():
        rows.extend(compute_stability_per_uid(matrix, uid))
    return pd.DataFrame([r.__dict__ for r in rows])


def build_masks(summary: pd.DataFrame, thresholds: Iterable[float]) -> List[dict]:
    result: List[dict] = []
    for uid, group in summary.groupby("uid"):
        for threshold in thresholds:
            mask = (group.sort_values("bit_position")["stability"] >= threshold).astype(int)
            result.append(
                {
                    "uid": uid,
                    "threshold": float(threshold),
                    "mask": "".join(mask.astype(str).tolist()),
                    "selected_bits": int(mask.sum()),
                    "total_bits": int(mask.shape[0]),
                }
            )
    return result


def _split_train_holdout(
    matrix: np.ndarray, holdout_ratio: float, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    n = matrix.shape[0]
    if n < 2:
        raise ValueError("At least 2 samples per UID are required for holdout BER estimation")
    holdout_n = max(1, int(round(n * holdout_ratio)))
    holdout_n = min(holdout_n, n - 1)
    indices = np.arange(n)
    rng.shuffle(indices)
    holdout_idx = indices[:holdout_n]
    train_idx = indices[holdout_n:]
    return matrix[train_idx], matrix[holdout_idx]


def threshold_comparison(
    matrices: Dict[str, np.ndarray],
    thresholds: Iterable[float],
    holdout_ratio: float,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: List[dict] = []

    for uid, matrix in matrices.items():
        train, holdout = _split_train_holdout(matrix, holdout_ratio, rng)
        train_p1 = train.mean(axis=0)
        train_dom = (train_p1 >= 0.5).astype(np.uint8)
        train_stab = np.maximum(train_p1, 1.0 - train_p1)

        for threshold in thresholds:
            mask = train_stab >= threshold
            selected = int(mask.sum())
            if selected == 0:
                ber = np.nan
            else:
                selected_ref = train_dom[mask]
                selected_holdout = holdout[:, mask]
                ber = float(np.not_equal(selected_holdout, selected_ref).mean())

            rows.append(
                {
                    "uid": uid,
                    "threshold": float(threshold),
                    "selected_bits_count": selected,
                    "total_bits": int(mask.shape[0]),
                    "selection_ratio": float(selected / max(1, mask.shape[0])),
                    "estimated_ber_holdout": ber,
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(args.input)
    with_bits = add_bitstream_columns(df)
    matrices = sample_level_bit_matrix(with_bits)

    summary = stability_table(matrices)
    summary.to_csv(args.output_dir / "stability_summary.csv", index=False)

    masks = build_masks(summary, args.thresholds)
    with (args.output_dir / "masks.json").open("w", encoding="utf-8") as f:
        json.dump(masks, f, indent=2)

    comparison = threshold_comparison(
        matrices=matrices,
        thresholds=args.thresholds,
        holdout_ratio=args.holdout_ratio,
        seed=args.seed,
    )
    comparison.to_csv(args.output_dir / "threshold_comparison.csv", index=False)

    print("Saved:")
    print(f"  {args.output_dir / 'stability_summary.csv'}")
    print(f"  {args.output_dir / 'masks.json'}")
    print(f"  {args.output_dir / 'threshold_comparison.csv'}")


if __name__ == "__main__":
    main()