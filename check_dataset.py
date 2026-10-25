"""check_dataset.py -- 驗證 crps.csv 的結構假設,以及 FE 金鑰實際用到哪一段 SRAM。

放在專案根目錄,直接執行:
    python check_dataset.py
可指定路徑:
    python check_dataset.py --csv data/crps.csv --masks artifacts/masks.json \
        --threshold 0.9 --holdout artifacts/threshold_comparison.csv

只讀取檔案,不會修改任何資料。結果會印在螢幕,同時存成 check_dataset_report.txt,
把那個 txt 的內容貼回來即可。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

KEY_BITS_USED = 256 * 11  # Gen() 實際消耗的穩定位元數
lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def parse_address(value: str) -> int:
    return int(str(value), 0)  # 0x... 十六進位與十進位都能解析


def check_csv(csv_path: Path) -> int | None:
    """回傳每一列 data 的 bit 數(供第二項檢查換算用)。"""
    say("=== 檢查 1:crps.csv 結構 ===")
    all_cols = list(pd.read_csv(csv_path, nrows=0).columns)
    say(f"欄位: {all_cols}")
    wanted = [c for c in ("uid", "address", "created_at", "pic", "board_type") if c in all_cols]
    df = pd.read_csv(csv_path, usecols=wanted)
    say(f"總列數: {len(df):,}   uid 數: {df['uid'].nunique()}")

    per_boot = df.groupby(["uid", "created_at"]).size()
    say(f"開機次數(uid, created_at)總數: {len(per_boot):,}")
    say(f"每次開機的列數: 最少 {per_boot.min()} / 中位數 {int(per_boot.median())} / 最多 {per_boot.max()}")
    boots_per_uid = df.groupby("uid")["created_at"].nunique()
    say(f"每台設備的開機次數: 最少 {boots_per_uid.min()} / 中位數 {int(boots_per_uid.median())} / 最多 {boots_per_uid.max()}")

    dup = int(df.duplicated(["uid", "created_at", "address"]).sum())
    say(f"同一次開機內 address 重複的列數: {dup:,}  (應為 0;不為 0 代表同一位置被接了兩次)")

    if "pic" in df.columns:
        pic_per_uid = df.groupby("uid")["pic"].nunique()
        pic_per_boot = df.groupby(["uid", "created_at"])["pic"].nunique()
        say(f"pic 種類數 / 每台設備: 最少 {pic_per_uid.min()} / 最多 {pic_per_uid.max()}")
        say(f"pic 種類數 / 每次開機: 最少 {pic_per_boot.min()} / 最多 {pic_per_boot.max()}  (大於 1 代表一次開機混了多個 pic)")
    else:
        say("沒有 pic 欄位")
    if "board_type" in df.columns:
        say(f"board_type 種類: {sorted(df['board_type'].astype(str).unique())[:10]}")

    addrs = df["address"].astype(str).unique()
    say(f"不同的 address 數量: {len(addrs)}   範例: {list(addrs[:5])}")
    say(f"address 字串長度分佈: {pd.Series([len(a) for a in addrs]).value_counts().to_dict()}")
    try:
        by_string = sorted(addrs)
        by_number = sorted(addrs, key=parse_address)
        same = by_string == by_number
        say(f"字串排序與數值排序是否一致: {'一致' if same else '不一致 (程式用字串排序,拼接順序會錯)'}")
    except ValueError:
        say("address 無法解析成數字,無法比較排序(請看上面的範例值)")

    first = pd.read_csv(csv_path, usecols=["data"], nrows=1)["data"].iloc[0]
    values = len(str(first).split(","))
    say(f"第一列 data 有 {values} 個數字 = {values * 8} bits")
    bits = values * 8
    say(f"推算每次開機位元數 = 中位數列數 {int(per_boot.median())} x {bits} = {int(per_boot.median()) * bits:,}")
    return bits


def check_masks(masks_path: Path, threshold: float, row_bits: int | None) -> None:
    say("")
    say(f"=== 檢查 2:門檻 {threshold} 的前 {KEY_BITS_USED} 個穩定位元落在哪裡 ===")
    if not masks_path.exists():
        say(f"找不到 {masks_path},略過")
        return
    with masks_path.open(encoding="utf-8") as handle:
        records = json.load(handle)  # 檔案很大時需要一些時間
    last_positions: list[int] = []
    for record in records:
        if abs(float(record["threshold"]) - threshold) > 1e-9:
            continue
        flags = np.frombuffer(record["mask"].encode("ascii"), dtype=np.uint8) == ord("1")
        positions = np.flatnonzero(flags)
        if len(positions) >= KEY_BITS_USED:
            last_positions.append(int(positions[KEY_BITS_USED - 1]))
    if not last_positions:
        say("沒有任何設備符合條件(穩定位元不足或門檻不存在)")
        return
    arr = np.array(last_positions)
    say(f"設備數: {len(arr)}")
    say(f"第 {KEY_BITS_USED} 個穩定位元的 bit 位置: 最小 {arr.min():,} / 中位數 {int(np.median(arr)):,} / 最大 {arr.max():,}")
    if row_bits:
        in_first_row = int((arr < row_bits).sum())
        say(f"每列 {row_bits} bits;全部金鑰素材落在第一列內的設備: {in_first_row}/{len(arr)}")
        say(f"落在第幾列(從 0 起算): 最小 {arr.min() // row_bits} / 最大 {arr.max() // row_bits}")


def check_holdout(holdout_path: Path) -> None:
    say("")
    say("=== 檢查 3:holdout 實測 BER(真實的另一次開機 vs 訓練多數值) ===")
    if not holdout_path.exists():
        say(f"找不到 {holdout_path},略過")
        return
    table = pd.read_csv(holdout_path)
    summary = table.groupby("threshold").agg(
        設備數=("uid", "nunique"),
        平均BER=("estimated_ber_holdout", "mean"),
        最大BER=("estimated_ber_holdout", "max"),
        平均選取位元=("selected_bits_count", "mean"),
        最少選取位元=("selected_bits_count", "min"),
    )
    say(summary.to_string())


def main() -> None:
    parser = argparse.ArgumentParser(description="檢查 crps.csv 與 FE 金鑰素材位置")
    parser.add_argument("--csv", type=Path, default=Path("data/crps.csv"))
    parser.add_argument("--masks", type=Path, default=Path("artifacts/masks.json"))
    parser.add_argument("--holdout", type=Path, default=Path("artifacts/threshold_comparison.csv"))
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--report", type=Path, default=Path("check_dataset_report.txt"))
    args = parser.parse_args()

    row_bits = check_csv(args.csv) if args.csv.exists() else None
    if row_bits is None:
        say(f"找不到 {args.csv}")
    check_masks(args.masks, args.threshold, row_bits)
    check_holdout(args.holdout)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n報告已存到 {args.report}")


if __name__ == "__main__":
    main()