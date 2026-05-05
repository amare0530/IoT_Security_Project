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

    df["uid"] = df["uid"].astype("category")
    df["address"] = df["address"].astype(str)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    if df["created_at"].isna().any():
        raise ValueError("created_at contains invalid datetime values")

    def row_to_bitstream(data_str: str) -> str:
        return "".join(format(int(b), "08b") for b in data_str.split(","))

    print("正在轉換 bitstream（row-level，無 explode）...")
    df["bitstream"] = df["data"].apply(row_to_bitstream)

    # 檢查同一個 (uid, address) 底下每列的 bitstream 長度必須一致
    bit_lengths = df.groupby(["uid", "address"], observed=True)["bitstream"].apply(
        lambda s: s.str.len().unique()
    )
    for (uid, addr), lengths in bit_lengths.items():
        if len(lengths) != 1:
            raise ValueError(
                f"Inconsistent bitstream length for uid={uid}, address={addr}: {lengths}"
            )

    df = df.drop(columns=["data"])
    return df.sort_values(["uid", "created_at", "address"]).reset_index(drop=True)


def sample_level_bit_matrix(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    正確做法：
    - 每個 (uid, created_at) = 一次完整的開機量測
    - 把該次量測的所有 address 依位址排序後串接成一條長 bitstream
    - 跨多個 created_at（多次開機）計算每個 bit 的穩定度

    之前的錯誤是把「不同 address（不同物理記憶體位置）」誤當成
    「同一位置的不同次量測」，導致穩定度嚴重失真。
    """
    matrices: Dict[str, np.ndarray] = {}

    for uid, uid_group in df.groupby("uid", observed=True):
        date_bitstreams: List[str] = []

        for _date, date_group in uid_group.groupby("created_at", sort=True):
            # 每次開機：把所有 address 依位址排序後串接
            combined = "".join(
                date_group.sort_values("address")["bitstream"].tolist()
            )
            date_bitstreams.append(combined)

        if len(date_bitstreams) < 2:
            # 少於 2 次開機量測，無法計算穩定度，跳過
            print(f"  [skip] uid={uid} 只有 {len(date_bitstreams)} 次量測，需要至少 2 次")
            continue

        bit_len = len(date_bitstreams[0])
        inconsistent = [i for i, b in enumerate(date_bitstreams) if len(b) != bit_len]
        if inconsistent:
            print(
                f"  [skip] uid={uid} 第 {inconsistent} 次量測的 bitstream 長度不一致，跳過"
            )
            continue

        matrices[str(uid)] = (
            np.frombuffer("".join(date_bitstreams).encode(), dtype=np.uint8).reshape(
                len(date_bitstreams), bit_len
            )
            - ord("0")
        )

    print(f"成功建立 {len(matrices)} 個裝置的 bit matrix")
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


def stability_table(matrices: Dict[str, np.ndarray], output_path: Path) -> pd.DataFrame:
    """
    串流寫入：每個裝置算完就直接寫進 CSV，不把 4500 萬行全堆在記憶體裡。
    同時回傳一個輕量的「每裝置摘要」DataFrame 供 build_masks 使用。
    """
    first = True
    summary_rows: List[dict] = []  # 只保留裝置等級的摘要（不是每個 bit）

    for uid, matrix in matrices.items():
        results = compute_stability_per_uid(matrix, uid)
        chunk = pd.DataFrame([r.__dict__ for r in results])

        # 串流寫入 CSV
        chunk.to_csv(
            output_path,
            mode="w" if first else "a",
            header=first,
            index=False,
        )
        first = False

        # 保留裝置等級摘要給 build_masks 用
        summary_rows.append({
            "uid": uid,
            "total_bits": len(results),
            "mean_stability": float(chunk["stability"].mean()),
            "bits_gt_090": int((chunk["stability"] >= 0.90).sum()),
            "bits_gt_095": int((chunk["stability"] >= 0.95).sum()),
            "bits_gt_098": int((chunk["stability"] >= 0.98).sum()),
        })
        print(f"  [{uid[:20]}] bits={len(results):,}  mean_stab={chunk['stability'].mean():.4f}  >0.9={int((chunk['stability']>=0.9).sum())}")

    return pd.DataFrame(summary_rows)


def build_masks(stability_csv_path: Path, thresholds: Iterable[float]) -> List[dict]:
    """
    從已寫好的 stability_summary.csv 分批讀取，避免一次載入 4500 萬行。
    """
    result: List[dict] = []
    thresholds = list(thresholds)

    for uid, group in pd.read_csv(stability_csv_path).groupby("uid"):
        for threshold in thresholds:
            mask = (
                group.sort_values("bit_position")["stability"] >= threshold
            ).astype(int)
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
        raise ValueError(
            "At least 2 samples per UID are required for holdout BER estimation"
        )
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

    stability_csv = args.output_dir / "stability_summary.csv"

    print("載入資料集...")
    df = load_dataset(args.input)
    print(f"  共 {len(df)} 筆，{df['uid'].nunique()} 個裝置")

    print("建立 bit matrix（正確分組：uid × date）...")
    matrices = sample_level_bit_matrix(df)

    if not matrices:
        print("錯誤：沒有任何裝置有足夠的量測次數（需要至少 2 個不同日期）")
        print("請確認 crps.csv 包含多個日期的資料（完整版，非 4500 筆樣本）")
        return

    print(f"計算穩定度（串流寫入 {stability_csv}）...")
    device_summary = stability_table(matrices, stability_csv)
    device_summary.to_csv(args.output_dir / "device_summary.csv", index=False)

    print("建立遮罩（從 CSV 分批讀取）...")
    masks = build_masks(stability_csv, args.thresholds)
    with (args.output_dir / "masks.json").open("w", encoding="utf-8") as f:
        json.dump(masks, f, indent=2)

    print("計算 BER 與門檻比較...")
    comparison = threshold_comparison(
        matrices=matrices,
        thresholds=args.thresholds,
        holdout_ratio=args.holdout_ratio,
        seed=args.seed,
    )
    comparison.to_csv(args.output_dir / "threshold_comparison.csv", index=False)

    print("\n=== 裝置摘要 ===")
    print(device_summary.to_string(index=False))

    print("\nSaved:")
    print(f"  {stability_csv}")
    print(f"  {args.output_dir / 'device_summary.csv'}")
    print(f"  {args.output_dir / 'masks.json'}")
    print(f"  {args.output_dir / 'threshold_comparison.csv'}")


if __name__ == "__main__":
    main()