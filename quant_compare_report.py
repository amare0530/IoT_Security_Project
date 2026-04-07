"""
產生論文對照用的量化摘要報告。

用途：
1. 從 SQLite 抓目前專題的 FRR/HD 統計
2. 輸出可直接貼到報告的 Markdown
3. 統一留下可追蹤的比較紀錄

使用方式：
  python quant_compare_report.py
  python quant_compare_report.py --db authentication_history.db --output docs/reports/QUANT_COMPARISON_2026-04-07.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
from pathlib import Path
from statistics import mean


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def fetch_batch_summary(conn: sqlite3.Connection):
    if not table_exists(conn, "batch_experiments"):
        return []

    rows = conn.execute(
        """
        SELECT batch_id, noise_level, threshold, total_tests, passed_tests, failed_tests,
               frr, pass_rate, avg_distance, hd_std, hd_p10, hd_p90, timestamp
        FROM batch_experiments
        ORDER BY timestamp DESC
        LIMIT 10
        """
    ).fetchall()
    return rows


def fetch_auth_source_summary(conn: sqlite3.Connection):
    if not table_exists(conn, "auth_history"):
        return []

    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(auth_history)").fetchall()
    }

    if "source" not in cols:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS n,
                SUM(CASE WHEN result='pass' THEN 1 ELSE 0 END) AS pass_n,
                SUM(CASE WHEN result='fail' THEN 1 ELSE 0 END) AS fail_n,
                AVG(hamming_distance) AS avg_hd
            FROM auth_history
            """
        ).fetchone()
        if not row:
            return []
        return [("unknown", row[0], row[1], row[2], row[3])]

    rows = conn.execute(
        """
        SELECT source,
               COUNT(*) AS n,
               SUM(CASE WHEN result='pass' THEN 1 ELSE 0 END) AS pass_n,
               SUM(CASE WHEN result='fail' THEN 1 ELSE 0 END) AS fail_n,
               AVG(hamming_distance) AS avg_hd
        FROM auth_history
        GROUP BY source
        ORDER BY n DESC
        """
    ).fetchall()
    return rows


def build_markdown(batch_rows, source_rows) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("# 量化對照摘要")
    lines.append("")
    lines.append(f"產生時間：{now}")
    lines.append("")
    lines.append("## 指標定義")
    lines.append("")
    lines.append(r"- $FRR = \frac{N_{fail}}{N_{total}} \times 100\%$")
    lines.append(r"- $PassRate = \frac{N_{pass}}{N_{total}} \times 100\%$")
    lines.append(r"- $HD_{avg} = \frac{1}{N}\sum_{i=1}^{N}HD_i$")
    lines.append("")

    lines.append("## 最近批量實驗")
    lines.append("")
    if not batch_rows:
        lines.append("目前找不到 batch_experiments 紀錄。")
    else:
        lines.append("| batch_id | noise | threshold | total | pass | fail | FRR | PassRate | AvgHD | HD std | P10 | P90 |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in batch_rows:
            lines.append(
                f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {float(r[6] or 0):.2f}% | {float(r[7] or 0):.2f}% | {float(r[8] or 0):.2f} | {float(r[9] or 0):.2f} | {float(r[10] or 0):.2f} | {float(r[11] or 0):.2f} |"
            )

        frr_values = [float(r[6] or 0) for r in batch_rows]
        lines.append("")
        lines.append(f"最近 10 筆批量 FRR 平均：{mean(frr_values):.2f}%")

    lines.append("")
    lines.append("## 認證資料來源分佈")
    lines.append("")
    if not source_rows:
        lines.append("目前找不到 auth_history 紀錄。")
    else:
        lines.append("| source | 樣本數 | pass | fail | 平均 HD |")
        lines.append("|---|---:|---:|---:|---:|")
        for r in source_rows:
            source = r[0] or "unknown"
            n = int(r[1] or 0)
            pass_n = int(r[2] or 0)
            fail_n = int(r[3] or 0)
            avg_hd = float(r[4] or 0)
            lines.append(f"| {source} | {n} | {pass_n} | {fail_n} | {avg_hd:.2f} |")

    lines.append("")
    lines.append("## 論文基準參考")
    lines.append("")
    lines.append("- pypuf：https://github.com/nils-wisiol/pypuf")
    lines.append("- Neural-network modeling attacks：https://eprint.iacr.org/2021/555")
    lines.append("- LP-PUF：https://eprint.iacr.org/2021/1004")
    lines.append("")
    lines.append("## 說明")
    lines.append("")
    lines.append("本檔為專題內部對照摘要，目的是固定產出格式，方便每週和老師同步。")
    lines.append("若要做正式論文比較，仍需補上同資料條件與同評估流程的公平實驗。")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="產生論文對照量化摘要")
    parser.add_argument("--db", default="authentication_history.db", help="SQLite 資料庫路徑")
    parser.add_argument("--output", default=None, help="輸出 Markdown 路徑")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"錯誤：找不到資料庫 {db_path}")
        return 1

    if args.output:
        output_path = Path(args.output)
    else:
        today = dt.datetime.now().strftime("%Y-%m-%d")
        output_path = Path("docs/reports") / f"QUANT_COMPARISON_{today}.md"

    conn = sqlite3.connect(str(db_path))
    try:
        batch_rows = fetch_batch_summary(conn)
        source_rows = fetch_auth_source_summary(conn)
    finally:
        conn.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = build_markdown(batch_rows, source_rows)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"已輸出：{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



