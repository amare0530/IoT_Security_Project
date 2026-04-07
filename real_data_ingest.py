"""
IoT PUF 專題的開源/真實資料匯入與驗證工具。

用法：
    python real_data_ingest.py --input data.csv --dataset-name my_open_dataset
    python real_data_ingest.py --input data.csv --validate-only

必要 CSV 欄位：
    device_id, challenge, response, timestamp, temperature_c, supply_proxy, session_id, source

選填欄位：
    dataset_name, metadata_json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
from typing import Dict, List, Tuple

DB_PATH = "authentication_history.db"

REQUIRED_COLUMNS = {
    "device_id",
    "challenge",
    "response",
    "timestamp",
    "temperature_c",
    "supply_proxy",
    "session_id",
    "source",
}

OPTIONAL_COLUMNS = {"dataset_name", "metadata_json"}
ALLOWED_SOURCES = {"real", "simulated"}


def _normalize_hex(value: str) -> str:
    value = (value or "").strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value


def _is_hex(value: str) -> bool:
    if not value:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _normalize_source(value: str) -> str:
    raw = (value or "").strip().lower()
    if raw in {"open", "open_dataset", "opensource", "public"}:
        return "real"
    return raw


def validate_row(row: Dict[str, str], row_no: int) -> List[str]:
    errors: List[str] = []

    challenge = _normalize_hex(row.get("challenge", ""))
    response = _normalize_hex(row.get("response", ""))
    source = _normalize_source(row.get("source", ""))

    if not row.get("device_id", "").strip():
        errors.append(f"row {row_no}: device_id is empty")

    if not _is_hex(challenge):
        errors.append(f"row {row_no}: challenge must be hex")
    if not _is_hex(response):
        errors.append(f"row {row_no}: response must be hex")

    if source not in ALLOWED_SOURCES:
        errors.append(
            f"row {row_no}: source must be one of {sorted(ALLOWED_SOURCES)}"
        )

    if not row.get("timestamp", "").strip():
        errors.append(f"row {row_no}: timestamp is empty")

    if not row.get("session_id", "").strip():
        errors.append(f"row {row_no}: session_id is empty")

    if not row.get("supply_proxy", "").strip():
        errors.append(f"row {row_no}: supply_proxy is empty")

    temp_raw = (row.get("temperature_c", "") or "").strip()
    try:
        float(temp_raw)
    except ValueError:
        errors.append(f"row {row_no}: temperature_c must be numeric")

    metadata_json = (row.get("metadata_json", "") or "").strip()
    if metadata_json:
        try:
            json.loads(metadata_json)
        except json.JSONDecodeError:
            errors.append(f"row {row_no}: metadata_json must be valid JSON")

    return errors


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS crp_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            challenge TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            temperature_c REAL,
            supply_proxy TEXT,
            session_id TEXT NOT NULL,
            source TEXT NOT NULL,
            dataset_name TEXT,
            metadata_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_crp_device ON crp_records(device_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crp_session ON crp_records(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crp_source ON crp_records(source)")

    conn.commit()


def load_csv(path: str) -> Tuple[List[Dict[str, str]], List[str]]:
    rows: List[Dict[str, str]] = []
    errors: List[str] = []

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])

        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            errors.append(f"missing required columns: {sorted(missing)}")
            return rows, errors

        unknown = fieldnames - REQUIRED_COLUMNS - OPTIONAL_COLUMNS
        if unknown:
            errors.append(f"unknown columns found: {sorted(unknown)}")

        for i, row in enumerate(reader, start=2):
            rows.append(row)
            errors.extend(validate_row(row, i))

    return rows, errors


def ingest_rows(
    conn: sqlite3.Connection,
    rows: List[Dict[str, str]],
    dataset_name_override: str | None = None,
) -> int:
    cur = conn.cursor()
    inserted = 0

    for row in rows:
        source = _normalize_source(row.get("source", ""))
        dataset_name = dataset_name_override or row.get("dataset_name") or None
        challenge = _normalize_hex(row.get("challenge", ""))
        response = _normalize_hex(row.get("response", ""))

        cur.execute(
            """
            INSERT INTO crp_records
            (device_id, challenge, response, timestamp, temperature_c, supply_proxy, session_id, source, dataset_name, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (row.get("device_id") or "").strip(),
                challenge,
                response,
                (row.get("timestamp") or "").strip(),
                float((row.get("temperature_c") or "0").strip()),
                (row.get("supply_proxy") or "").strip(),
                (row.get("session_id") or "").strip(),
                source,
                dataset_name,
                (row.get("metadata_json") or "").strip() or None,
            ),
        )
        inserted += 1

    conn.commit()
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="驗證並匯入開源/真實 PUF 資料 CSV")
    parser.add_argument("--input", required=True, help="CSV 檔案路徑")
    parser.add_argument("--db", default=DB_PATH, help="SQLite 資料庫路徑")
    parser.add_argument("--dataset-name", default=None, help="覆蓋 dataset 名稱")
    parser.add_argument("--validate-only", action="store_true", help="只驗證，不寫入資料庫")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"錯誤：找不到輸入檔案：{args.input}")
        return 1

    rows, errors = load_csv(args.input)
    if errors:
        print("驗證失敗")
        for e in errors:
            print(f"- {e}")
        return 2

    print(f"驗證通過：共 {len(rows)} 筆")

    if args.validate_only:
        return 0

    conn = sqlite3.connect(args.db)
    try:
        ensure_schema(conn)
        inserted = ingest_rows(conn, rows, dataset_name_override=args.dataset_name)
        print(f"匯入完成：已寫入 {inserted} 筆到 crp_records")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())



