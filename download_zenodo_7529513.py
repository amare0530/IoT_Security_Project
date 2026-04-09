#!/usr/bin/env python3
"""
Download the real Zenodo 7529513 dataset.

This record contains the real SRAM readouts (crps.csv) and sensor data
(sensors.csv) used by the TIMA Laboratory dataset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


RECORD_ID = "7529513"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
DEFAULT_OUTPUT_DIR = Path("artifacts") / "zenodo_7529513"


def fetch_record() -> dict:
    response = requests.get(API_URL, timeout=120)
    response.raise_for_status()
    return response.json()


def pick_files(record: dict) -> list[dict]:
    files = record.get("files", [])
    wanted = []
    for file_info in files:
        key = file_info.get("key", "")
        if key in {"crps.csv", "sensors.csv"}:
            wanted.append(file_info)
    return wanted


def download_file(file_info: dict, output_dir: Path) -> Path:
    key = file_info["key"]
    url = file_info["links"]["self"]
    destination = output_dir / key

    print(f"[*] Downloading {key}")
    print(f"    URL: {url}")
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)

    print(f"[OK] Saved {destination} ({destination.stat().st_size} bytes)")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Zenodo 7529513 real PUF data")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to store downloaded files")
    parser.add_argument("--manifest", default=str(DEFAULT_OUTPUT_DIR / "manifest.json"), help="Path for the record manifest")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Fetching Zenodo record {RECORD_ID}")
    record = fetch_record()
    files = pick_files(record)

    if not files:
        print("[ERROR] No matching files found in record")
        return 2

    downloaded = []
    for file_info in files:
        downloaded.append(download_file(file_info, output_dir))

    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "record_id": RECORD_ID,
        "title": record.get("metadata", {}).get("title"),
        "doi": record.get("doi"),
        "files": [
            {
                "key": file_info.get("key"),
                "size": file_info.get("size"),
                "checksum": file_info.get("checksum"),
                "download_url": file_info.get("links", {}).get("self"),
            }
            for file_info in files
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] Wrote manifest {manifest_path}")
    print("[*] Download complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())