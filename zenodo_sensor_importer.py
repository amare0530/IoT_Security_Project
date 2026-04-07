#!/usr/bin/env python3
"""
Zenodo TIMA sensor data importer.

Converts sensor-only data (temperature, voltage, timestamp) into 
authentication_history for environmental characterization.

Unlike CRP data, sensors provide context for evaluating PUF stability,
not authentication pairs directly.
"""

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from real_data_ingest import ensure_schema, ingest_rows

def import_sensor_data(input_csv: str, output_db: str) -> int:
    """
    Import sensor data, create synthetic CRP records for environmental analysis.
    
    Strategy: Group sensors by device+session, create pseudo-CRP with 
    device_id from uid, session from timestamp, response="SENSOR_DATA",
    challenge as temperature+voltage hash.
    """
    
    rows_to_import: List[Dict[str, str]] = []
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            uid = row.get('uid', '').strip()
            temp = row.get('temperature', '0').strip()
            voltage = row.get('voltage', '3.3').strip()
            created_at = row.get('created_at', datetime.now().isoformat()).strip()
            
            # Create pseudo-CRP record
            # Challenge = hash(temp+voltage) for environmental tracking
            challenge = f"{float(temp):.2f}_{float(voltage):.5f}".replace('.', '').replace('_', '')
            
            # Response = placeholder indicating sensor data
            response = "feedU58D7"  # UTF-8 for "感測" in hex
            
            record = {
                'device_id': uid,
                'challenge': challenge,
                'response': response,
                'timestamp': created_at,
                'temperature_c': temp,
                'supply_proxy': voltage,
                'session_id': f"sensor_{row_num}",
                'source': 'real',
                'dataset_name': 'zenodo-tima-sensors',
                'metadata_json': f'{{"row_num": {row_num}, "type": "environmental"}}',
            }
            rows_to_import.append(record)
    
    # Write to database
    conn = sqlite3.connect(output_db)
    try:
        ensure_schema(conn)
        inserted = ingest_rows(conn, rows_to_import, dataset_name_override=None)
        return inserted
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: python zenodo_sensor_importer.py <input_csv> <output_db>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    inserted = import_sensor_data(input_file, output_file)
    print(f"Imported {inserted} sensor records into {output_file}")
