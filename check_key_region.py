"""check_key_region.py -- 檢查 FE 金鑰素材區(第一列 address 的前 2816 位元)是否特殊。

背景:check_dataset.py 顯示,84 台設備的前 2816 個位置全部都是穩定位元。
一般 SRAM 約有一成位元會跳動,連續 2816 個位置全穩定不太可能是巧合。
這支腳本回答三件事:
  1. 這一段和其他 address 列相比,穩定度是否明顯不同?
  2. 這一段的 golden(多數值)在不同設備之間有多相似?
  3. 只拿公開的 helper data W 加上「其他設備的多數值」去猜,能猜對多少個 key bit?
     (W = repeat(key_bits, 11) XOR R;若 R 在設備間高度相似,key_bits 就能被猜出來)

放在專案根目錄,直接執行:
    python check_key_region.py
結果會印在螢幕並存成 check_key_region_report.txt,把內容貼回來即可。
讀取全部 120,960 列並解碼,約需 1 到 3 分鐘。只讀檔,不修改任何資料。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

KEY_BITS = 256 * 11
REPETITION = 11
lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def decode_row(data: str) -> np.ndarray:
    return np.array([int(v) for v in data.split(",")], dtype=np.uint8)


def load_boots(csv_path: Path) -> dict[tuple[str, str], list[np.ndarray]]:
    boots: dict[tuple[str, str], list[np.ndarray]] = {}
    reader = pd.read_csv(csv_path, usecols=["uid", "address", "data"], chunksize=5000, dtype=str)
    done = 0
    for chunk in reader:
        for uid, address, data in zip(chunk["uid"], chunk["address"], chunk["data"]):
            boots.setdefault((uid, address), []).append(decode_row(data))
        done += len(chunk)
        print(f"  已讀 {done:,} 列", end="\r")
    print()
    return boots


def region_report(name: str, golden: np.ndarray) -> None:
    """golden: [設備數, 位元數],值為 0/1。"""
    n_dev, n_bits = golden.shape
    patterns = len({row.tobytes() for row in golden})
    g = golden.astype(np.float64)
    agree = g @ g.T + (1 - g) @ (1 - g).T
    hd = 1.0 - agree / n_bits
    pairs = hd[np.triu_indices(n_dev, k=1)]
    ones = golden.sum(axis=0)
    shared = np.maximum(ones, n_dev - ones) / n_dev
    shared95 = float((shared >= 0.95).mean())

    # 攻擊估計:用「其他設備的多數值」猜這台設備的 R,再對 helper data 解碼
    others_ones = ones[None, :] - golden
    guess = (others_ones * 2 > (n_dev - 1)).astype(np.uint8)
    mismatch = (golden != guess)[:, : (n_bits // REPETITION) * REPETITION]
    per_group = mismatch.reshape(n_dev, -1, REPETITION).sum(axis=2)
    wrong = (per_group >= REPETITION // 2 + 1).sum(axis=1)
    groups = per_group.shape[1]

    say(f"[{name}]  位元數 {n_bits},設備數 {n_dev}")
    say(f"  不同的 golden 樣式數: {patterns}/{n_dev}")
    say(f"  設備間 Hamming 距離(比例): 平均 {pairs.mean():.4f} / 最小 {pairs.min():.4f} / 最大 {pairs.max():.4f}")
    say(f"  golden 中 1 的比例: {golden.mean():.4f}")
    say(f"  至少 95% 設備值相同的位置占比: {shared95:.4f}")
    say(f"  以群體偏差猜 key bit 猜錯的個數(共 {groups} 個): 平均 {wrong.mean():.1f} / 最少 {wrong.min()} / 最多 {wrong.max()}")
    say("")


def main() -> None:
    parser = argparse.ArgumentParser(description="檢查 FE 金鑰素材區")
    parser.add_argument("--csv", type=Path, default=Path("data/crps.csv"))
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--report", type=Path, default=Path("check_key_region_report.txt"))
    args = parser.parse_args()

    print("讀取並解碼 crps.csv ...")
    boots = load_boots(args.csv)
    uids = sorted({uid for uid, _ in boots})
    addresses = sorted({addr for _, addr in boots}, key=lambda a: int(a, 0))
    n_rows = len(addresses)
    say("=== 檢查 4:金鑰素材區診斷 ===")
    say(f"設備數 {len(uids)},address 列數 {n_rows},第一列 address = {addresses[0]}")
    say("")

    row_bits = 512 * 8
    golden_all = np.zeros((len(uids), n_rows, row_bits), dtype=np.uint8)
    stable_frac = np.zeros((len(uids), n_rows))
    for ui, uid in enumerate(uids):
        for ai, addr in enumerate(addresses):
            matrix = np.stack(boots[(uid, addr)])
            bits = np.unpackbits(matrix, axis=1)
            p1 = bits.mean(axis=0)
            stability = np.maximum(p1, 1 - p1)
            golden_all[ui, ai] = (p1 >= 0.5).astype(np.uint8)
            stable_frac[ui, ai] = float((stability >= args.threshold).mean())

    by_row = stable_frac.mean(axis=0)
    say("--- 每列 address 的穩定位元比例(各設備平均) ---")
    say(f"全部 {n_rows} 列: 最小 {by_row.min():.4f} / 中位數 {np.median(by_row):.4f} / 最大 {by_row.max():.4f}")
    say("前 6 列: " + ", ".join(f"{v:.4f}" for v in by_row[:6]))
    top = np.argsort(by_row)[::-1][:5]
    say("最穩定的 5 列: " + ", ".join(f"{addresses[i]}={by_row[i]:.4f}" for i in top))
    first_key_rows = stable_frac[:, 0]
    say(f"第一列內,每台設備的穩定位元比例: 最小 {first_key_rows.min():.4f} / 最大 {first_key_rows.max():.4f}")
    say("")

    flat = golden_all.reshape(len(uids), -1)
    middle = n_rows // 2
    say("--- golden 跨設備比較 ---")
    region_report("金鑰素材區 = 第一列前 2816 位元", flat[:, :KEY_BITS])
    start = middle * row_bits
    region_report(f"對照區 = 第 {middle} 列前 2816 位元", flat[:, start : start + KEY_BITS])
    region_report("對照區 = 最後一列前 2816 位元", flat[:, (n_rows - 1) * row_bits : (n_rows - 1) * row_bits + KEY_BITS])

    key_bytes = np.packbits(flat[:, :KEY_BITS], axis=1)
    say("--- 金鑰素材區的前 16 個 byte(十進位),前 3 台設備 ---")
    for ui in range(min(3, len(uids))):
        say(f"  {uids[ui][:16]}: {key_bytes[ui, :16].tolist()}")
    distinct = len(np.unique(key_bytes))
    say(f"金鑰素材區出現過的不同 byte 值種類: {distinct}/256")

    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n報告已存到 {args.report}")


if __name__ == "__main__":
    main()