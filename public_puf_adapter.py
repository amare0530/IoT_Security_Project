"""
公開 PUF 資料集轉接器。

用途：
- 讀取常見的公開 SRAM PUF 或 RO PUF CSV/TSV 資料
- 正規化成本專案使用的 crp_records 格式
- 可直接輸出成 CSV，或寫入 authentication_history.db

這個轉接器假設外部資料集至少能提供下列資訊中的一部分：
- device_id 或 device
- challenge
- response
- session_id
- timestamp
- temperature_c
- supply_proxy

若缺少 session_id 或 timestamp，會用資料集名稱與列號補上，確保資料可以匯入且可追蹤。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from real_data_ingest import ensure_schema, ingest_rows

DEFAULT_DATASET_NAME = "public_puf_dataset"
DEFAULT_SOURCE = "real"

FIELD_ALIASES = {
    "device_id": ["device_id", "device", "chip_id", "board_id", "sensor_id", "uid"],
    "challenge": ["challenge", "crp_challenge", "c", "query", "address"],
    "response": ["response", "crp_response", "r", "reply", "measurement", "data"],
    "session_id": ["session_id", "session", "run_id", "trial_id", "capture_id", "pic"],
    "timestamp": ["timestamp", "time", "datetime", "capture_time", "created_at"],
    "temperature_c": ["temperature_c", "temperature", "temp_c", "temp"],
    "supply_proxy": ["supply_proxy", "voltage", "vdd", "power_state", "load_state"],
    "metadata_json": ["metadata_json", "metadata", "extra_json"],
}


def _strip_cell(value: Optional[str]) -> str:
    return (value or "").strip()


def _first_non_empty(row: Dict[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = _strip_cell(row.get(name))
        if value:
            return value
    return ""


def _looks_like_binary(value: str) -> bool:
    return bool(value) and set(value) <= {"0", "1"}


def _looks_like_hex(value: str) -> bool:
    if not value:
        return False
    cleaned = value.strip().lower()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    return all(ch in "0123456789abcdef" for ch in cleaned)


def _binary_to_hex(value: str, bit_length: Optional[int] = None) -> str:
    cleaned = value.strip().replace(" ", "")
    if not _looks_like_binary(cleaned):
        raise ValueError("value is not binary")
    if bit_length is None:
        bit_length = len(cleaned)
    padded = cleaned.zfill(bit_length)
    return f"{int(padded, 2):0{max(1, (bit_length + 3) // 4)}x}"


def _decimal_array_to_hex(value: str) -> str:
    """Convert comma-separated decimal array (e.g., '202,203,204') to hex string."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("empty decimal array")
    
    # Try to parse as comma-separated decimals
    try:
        parts = [int(x.strip()) for x in cleaned.split(',')]
        # Convert each byte to hex and concatenate
        hex_str = ''.join(f'{b:02x}' for b in parts)
        return hex_str
    except (ValueError, OverflowError) as e:
        raise ValueError(f"invalid decimal array format: {e}")


def _normalize_hex_like(value: str, bit_length: Optional[int] = None) -> str:
    cleaned = value.strip().lower().replace("0x", "", 1)
    
    # First, try decimal array format (e.g., "202,203,204,205")
    if ',' in cleaned:
        try:
            return _decimal_array_to_hex(cleaned)
        except ValueError:
            pass  # Fall through to next format
    
    # Then, try binary format
    if _looks_like_binary(cleaned):
        return _binary_to_hex(cleaned, bit_length=bit_length)
    
    # Finally, try hex format
    if _looks_like_hex(cleaned):
        if bit_length:
            width = max(1, (bit_length + 3) // 4)
            return cleaned.zfill(width)
        return cleaned
    
    raise ValueError(f"unsupported challenge/response format: {value[:32]}")


def _load_csv_rows(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    errors: List[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames:
            return [], ["input file has no header row"]
        rows = [row for row in reader]
    return rows, errors


def _build_metadata(row: Dict[str, str], row_number: int, source_file: str, extra_columns: Iterable[str]) -> str:
    metadata: Dict[str, str] = {
        "source_file": source_file,
        "row_number": str(row_number),
    }
    for key in extra_columns:
        value = _strip_cell(row.get(key))
        if value:
            metadata[key] = value
    return json.dumps(metadata, ensure_ascii=False)


def normalize_rows(
    rows: List[Dict[str, str]],
    dataset_name: str,
    source_file: str,
    default_source: str = DEFAULT_SOURCE,
) -> List[Dict[str, str]]:
    normalized_rows: List[Dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        device_id = _first_non_empty(row, FIELD_ALIASES["device_id"])
        challenge_raw = _first_non_empty(row, FIELD_ALIASES["challenge"])
        response_raw = _first_non_empty(row, FIELD_ALIASES["response"])

        if not device_id:
            device_id = f"{dataset_name}_device_{index - 1}"

        if not challenge_raw:
            raise ValueError(f"row {index}: missing challenge")
        if not response_raw:
            raise ValueError(f"row {index}: missing response")

        challenge = _normalize_hex_like(challenge_raw)
        response = _normalize_hex_like(response_raw)

        timestamp = _first_non_empty(row, FIELD_ALIASES["timestamp"])
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        session_id = _first_non_empty(row, FIELD_ALIASES["session_id"])
        if not session_id:
            session_id = f"{dataset_name}_session_{index - 1}"

        temperature_c = _first_non_empty(row, FIELD_ALIASES["temperature_c"])
        if not temperature_c:
            temperature_c = ""

        supply_proxy = _first_non_empty(row, FIELD_ALIASES["supply_proxy"])
        if not supply_proxy:
            supply_proxy = "unknown"

        metadata_json = _first_non_empty(row, FIELD_ALIASES["metadata_json"])
        if not metadata_json:
            extra_columns = [
                key
                for key in row.keys()
                if key not in {
                    *FIELD_ALIASES["device_id"],
                    *FIELD_ALIASES["challenge"],
                    *FIELD_ALIASES["response"],
                    *FIELD_ALIASES["session_id"],
                    *FIELD_ALIASES["timestamp"],
                    *FIELD_ALIASES["temperature_c"],
                    *FIELD_ALIASES["supply_proxy"],
                    *FIELD_ALIASES["metadata_json"],
                }
            ]
            metadata_json = _build_metadata(row, index, source_file, extra_columns)

        normalized_rows.append(
            {
                "device_id": device_id,
                "challenge": challenge,
                "response": response,
                "timestamp": timestamp,
                "temperature_c": temperature_c or "0",
                "supply_proxy": supply_proxy,
                "session_id": session_id,
                "source": default_source,
                "dataset_name": dataset_name,
                "metadata_json": metadata_json,
            }
        )

    return normalized_rows


def write_csv(rows: List[Dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "device_id",
        "challenge",
        "response",
        "timestamp",
        "temperature_c",
        "supply_proxy",
        "session_id",
        "source",
        "dataset_name",
        "metadata_json",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_sqlite(rows: List[Dict[str, str]], db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)
        return ingest_rows(conn, rows, dataset_name_override=None)
    finally:
        conn.close()


def compute_manifest(rows: List[Dict[str, str]], source_file: Path, dataset_name: str) -> Dict[str, str]:
    digest = hashlib.sha256(source_file.read_bytes()).hexdigest()
    return {
        "dataset_name": dataset_name,
        "source_file": str(source_file),
        "file_sha256": digest,
        "row_count": str(len(rows)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_manifest(manifest: Dict[str, str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="公開 PUF 資料集轉接器")
    parser.add_argument("--input", required=True, help="公開 PUF 資料集 CSV/TSV 檔案")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME, help="資料集名稱")
    parser.add_argument("--output-csv", default=None, help="輸出正規化 CSV 路徑")
    parser.add_argument("--output-db", default=None, help="寫入 SQLite 資料庫路徑")
    parser.add_argument("--manifest", default=None, help="輸出 provenance manifest 路徑")
    parser.add_argument("--source", default=DEFAULT_SOURCE, choices=["real", "simulated"], help="資料來源標記")
    parser.add_argument("--preview", action="store_true", help="只顯示前幾筆，不輸出檔案")
    parser.add_argument("--limit", type=int, default=5, help="preview 模式顯示筆數")
    args = parser.parse_args()

    source_file = Path(args.input)
    if not source_file.exists():
        print(f"找不到輸入檔案：{source_file}")
        return 1

    raw_rows, load_errors = _load_csv_rows(source_file)
    if load_errors:
        print("資料載入失敗")
        for error in load_errors:
            print(f"- {error}")
        return 2

    try:
        normalized_rows = normalize_rows(
            raw_rows,
            dataset_name=args.dataset_name,
            source_file=str(source_file),
            default_source=args.source,
        )
    except Exception as exc:
        print("資料轉接失敗")
        print(f"- {exc}")
        return 3

    if args.preview:
        preview_rows = normalized_rows[: args.limit]
        print(f"預覽前 {len(preview_rows)} 筆")
        for row in preview_rows:
            print(row)
        return 0

    if args.output_csv:
        write_csv(normalized_rows, Path(args.output_csv))
        print(f"已輸出正規化 CSV：{args.output_csv}")

    if args.output_db:
        inserted = write_sqlite(normalized_rows, Path(args.output_db))
        print(f"已寫入 SQLite：{inserted} 筆")

    if args.manifest:
        manifest = compute_manifest(normalized_rows, source_file, args.dataset_name)
        save_manifest(manifest, Path(args.manifest))
        print(f"已輸出 provenance manifest：{args.manifest}")

    if not args.output_csv and not args.output_db and not args.manifest:
        default_output = source_file.with_name(f"{source_file.stem}_normalized.csv")
        write_csv(normalized_rows, default_output)
        print(f"已輸出正規化 CSV：{default_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
