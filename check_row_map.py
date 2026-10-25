"""check_row_map.py -- 逐列標出「確定性區」與「真 PUF 區」,並比較三種選位元的方式。

背景:check_key_region.py 顯示第一列和最後一列的 golden 在 84 台設備上完全相同,
代表那些位置是韌體寫入的固定內容,不是上電隨機值。這支腳本回答:
  1. 160 列 address 裡,哪些是確定性區(各設備相同)、哪些是真 PUF 區?
  2. 現行論文的 574,655 個穩定位元,有多少落在確定性區?
  3. 三種選法的比較(每種都取 2,816 個位元,和 gen() 一樣):
       A 現行:穩定位置中的前 2,816 個
       B 排除確定性列,且位置在「其他設備」間夠平衡(1 的比例在 0.5±balance 內),取前 2,816 個
       C 同 B 的候選位置,改取最平衡的 2,816 個
     每種選法都計算「用其他設備的多數值猜 key bit 會猜錯幾個」(越多越好,128 是理想值)。

放在專案根目錄,直接執行:
    python check_row_map.py
結果印在螢幕並存成 check_row_map_report.txt,逐列明細存成 row_map.csv(不用貼)。
把 check_row_map_report.txt 的內容貼回來即可。約需 2 到 4 分鐘,只讀檔,不修改資料。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

KEY_BITS = 256 * 11
REPETITION = 11
ROW_BITS = 512 * 8
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


def ranges(indices: list[int]) -> str:
    if not indices:
        return "(無)"
    out, start, prev = [], indices[0], indices[0]
    for i in indices[1:]:
        if i != prev + 1:
            out.append(f"{start}-{prev}" if start != prev else f"{start}")
            start = i
        prev = i
    out.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ", ".join(out)


def wrong_key_bits(golden: np.ndarray, ones: np.ndarray, chosen: list[np.ndarray]) -> np.ndarray:
    """golden: [U, N];ones: [N] 各位置的 1 的總數;chosen[u]: 該設備選中的位置。回傳每台設備猜錯的 key bit 數。"""
    n_dev = golden.shape[0]
    result = []
    for u in range(n_dev):
        pos = chosen[u]
        own = golden[u, pos].astype(np.int64)
        guess = ((ones[pos] - own) * 2 > (n_dev - 1)).astype(np.uint8)
        mismatch = (own.astype(np.uint8) != guess)[: (len(pos) // REPETITION) * REPETITION]
        per_group = mismatch.reshape(-1, REPETITION).sum(axis=1)
        result.append(int((per_group >= REPETITION // 2 + 1).sum()))
    return np.array(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="逐列標出確定性區與真 PUF 區")
    parser.add_argument("--csv", type=Path, default=Path("data/crps.csv"))
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--balance", type=float, default=0.2, help="B/C 選法:位置 1 的比例需在 0.5±balance 內")
    parser.add_argument("--det-hd", type=float, default=0.01, help="平均設備間 Hamming 距離低於此值視為確定性列")
    parser.add_argument("--report", type=Path, default=Path("check_row_map_report.txt"))
    parser.add_argument("--rowmap", type=Path, default=Path("row_map.csv"))
    args = parser.parse_args()

    print("讀取並解碼 crps.csv ...")
    boots = load_boots(args.csv)
    uids = sorted({u for u, _ in boots})
    addresses = sorted({a for _, a in boots}, key=lambda a: int(a, 0))
    n_dev, n_rows = len(uids), len(addresses)

    golden = np.zeros((n_dev, n_rows, ROW_BITS), dtype=np.uint8)
    stable = np.zeros((n_dev, n_rows, ROW_BITS), dtype=bool)
    for ui, uid in enumerate(uids):
        for ai, addr in enumerate(addresses):
            bits = np.unpackbits(np.stack(boots[(uid, addr)]), axis=1)
            p1 = bits.mean(axis=0)
            golden[ui, ai] = (p1 >= 0.5).astype(np.uint8)
            stable[ui, ai] = np.maximum(p1, 1 - p1) >= args.threshold

    say("=== 檢查 5:逐列地圖 ===")
    say(f"設備數 {n_dev},address 列數 {n_rows},{addresses[0]} 到 {addresses[-1]}")
    say("")

    rows = []
    for r in range(n_rows):
        g = golden[:, r].astype(np.float32)
        agree = g @ g.T + (1 - g) @ (1 - g).T
        hd = 1.0 - agree / ROW_BITS
        mean_hd = float(hd[np.triu_indices(n_dev, k=1)].mean())
        patterns = len({row.tobytes() for row in golden[:, r]})
        rows.append({
            "row": r, "address": addresses[r],
            "stable_frac": float(stable[:, r].mean()),
            "distinct_patterns": patterns,
            "mean_inter_hd": mean_hd,
            "ones_ratio": float(golden[:, r].mean()),
        })
    table = pd.DataFrame(rows)
    table.to_csv(args.rowmap, index=False)

    det_rows = table.index[table["mean_inter_hd"] < args.det_hd].tolist()
    puf_rows = [r for r in range(n_rows) if r not in set(det_rows)]
    say(f"--- 確定性列(設備間平均 Hamming 距離 < {args.det_hd}) ---")
    say(f"共 {len(det_rows)} 列: {ranges(det_rows)}")
    say(f"其餘 {len(puf_rows)} 列的設備間平均 Hamming 距離: "
        f"最小 {table.loc[puf_rows, 'mean_inter_hd'].min():.4f} / 中位數 {table.loc[puf_rows, 'mean_inter_hd'].median():.4f} / "
        f"最大 {table.loc[puf_rows, 'mean_inter_hd'].max():.4f}")
    say("")

    det_mask = np.zeros(n_rows, dtype=bool)
    det_mask[det_rows] = True
    sel_total = stable.reshape(n_dev, -1).sum(axis=1)
    sel_in_det = stable[:, det_mask].reshape(n_dev, -1).sum(axis=1)
    say("--- 門檻下的穩定位元(論文的 574,655 那個數字) ---")
    say(f"每台穩定位元: 平均 {sel_total.mean():,.0f} / 最少 {sel_total.min():,}")
    say(f"其中落在確定性列: 平均 {sel_in_det.mean():,.0f}(占 {sel_in_det.mean() / sel_total.mean():.2%})")
    say(f"排除確定性列後: 平均 {(sel_total - sel_in_det).mean():,.0f} / 最少 {(sel_total - sel_in_det).min():,}")
    say("")

    flat_g = golden.reshape(n_dev, -1)
    flat_s = stable.reshape(n_dev, -1)
    ones = flat_g.sum(axis=0).astype(np.int64)
    bit_is_det = np.repeat(det_mask, ROW_BITS)

    chosen_a, chosen_b, chosen_c = [], [], []
    avail_b = []
    for u in range(n_dev):
        stable_pos = np.flatnonzero(flat_s[u])
        chosen_a.append(stable_pos[:KEY_BITS])
        frac_others = (ones - flat_g[u]) / (n_dev - 1)  # 平衡度只看其他設備,避免把自己算進去造成偏差
        balanced_u = np.abs(frac_others - 0.5) <= args.balance
        good = np.flatnonzero(flat_s[u] & ~bit_is_det & balanced_u)
        avail_b.append(len(good))
        chosen_b.append(good[:KEY_BITS])
        order = np.argsort(np.abs(frac_others[good] - 0.5), kind="stable")
        chosen_c.append(np.sort(good[order[:KEY_BITS]]))

    say(f"--- 選位元方式比較(balance = {args.balance},每種取 {KEY_BITS} 個,理想的猜錯個數約 128) ---")
    say(f"B/C 的候選位置數(穩定、非確定性列、位置平衡): 平均 {np.mean(avail_b):,.0f} / 最少 {min(avail_b):,}")
    for name, chosen in (("A 現行(穩定位置的前 2,816 個)", chosen_a),
                         ("B 排除確定性列 + 位置平衡,取前 2,816 個", chosen_b),
                         ("C 同 B 的候選,取最平衡的 2,816 個", chosen_c)):
        if min(len(c) for c in chosen) < KEY_BITS:
            say(f"[{name}] 有設備候選位置不足 {KEY_BITS} 個,略過")
            continue
        wrong = wrong_key_bits(flat_g, ones, chosen)
        max_pos = int(np.max([c.max() for c in chosen]))
        say(f"[{name}]  猜錯的 key bit 數(共 256 個): 平均 {wrong.mean():.1f} / 最少 {wrong.min()} / 最多 {wrong.max()}"
            f";用到的最大位置 {max_pos:,}")
    say("")
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"報告已存到 {args.report},逐列明細在 {args.rowmap}")


if __name__ == "__main__":
    main()