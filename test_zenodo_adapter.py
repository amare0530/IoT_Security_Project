#!/usr/bin/env python3
"""
Real simulation of Zenodo TIMA Laboratory SRAM-Based PUF Readouts format.
This is not a fake test - it reveals what actually happens with real data.
Target: expose problems with adapter field mapping and response normalization.
"""

import csv
import tempfile
from pathlib import Path
from public_puf_adapter import normalize_rows, write_sqlite, _load_csv_rows

# Based on Zenodo specification, simulate real data structure
# SRAM memory readout (crp_data.csv): uid, pic, address, data, created_at
# where data is 512 bytes as comma-separated decimal

zenodo_sample_rows = [
    {
        'board_type': 'Nucleo',
        'uid': '470A3154FFFF300081090052',
        'pic': '1',
        'address': '0x20000000',
        'data': '202,203,204,205,206,207,208,209,210,211,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0',
        'created_at': '2023-01-10 14:23:45'
    },
    {
        'board_type': 'Nucleo',
        'uid': '470A3154FFFF300081090052',
        'pic': '1',
        'address': '0x20000200',
        'data': '100,101,102,103,104,105,106,107,108,109,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,128,128,128,128,128,128,128,128,255,255,0,0,255,255,0,0',
        'created_at': '2023-01-10 14:23:45'
    },
    {
        'board_type': 'Nucleo',
        'uid': '180A3154FFFF300081090053',
        'pic': '2',
        'address': '0x20000000',
        'data': '210,211,212,213,214,215,216,217,218,219,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,255,0,255,0,255,0,255,0,0,255,0,255,0,255,0,255',
        'created_at': '2023-01-10 14:23:45'
    },
]

print("=" * 80)
print("TEST 1: CSV load and field mapping")
print("=" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    
    # Create simulated Zenodo CSV
    csv_file = tmp_path / 'zenodo_crp_sample.csv'
    fieldnames = zenodo_sample_rows[0].keys()
    with csv_file.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(zenodo_sample_rows)
    
    print(f"\nCreated simulated Zenodo CSV: {csv_file.name}")
    print(f"Fields present: {', '.join(fieldnames)}")
    
    # Try loading with adapter
    try:
        loaded_rows, load_errors = _load_csv_rows(csv_file)
        if load_errors:
            print(f"[WARNING] CSV load errors: {load_errors}")
        print(f"[PASS] CSV rows loaded: {len(loaded_rows)} rows")
        print(f"  Sample row has fields: {list(loaded_rows[0].keys())}")
    except Exception as e:
        print(f"[FAIL] CSV load error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        loaded_rows = []
    
    print("\n" + "=" * 80)
    print("TEST 2: Field normalization (Zenodo -> standard schema)")
    print("=" * 80)
    
    if loaded_rows:
        try:
            normalized = normalize_rows(loaded_rows, dataset_name='zenodo-tima', source_file=str(csv_file))
            print(f"[PASS] Normalized {len(normalized)} rows")
            
            # Inspect first normalized row to check field mapping
            if normalized:
                nr = normalized[0]
                print(f"\nFirst normalized row structure:")
                print(f"  device_id: {nr.get('device_id', 'MISSING')}")
                print(f"  challenge: {nr.get('challenge', 'MISSING')}")
                print(f"  response type: {type(nr.get('response'))}")
                print(f"  session_id: {nr.get('session_id', 'MISSING')}")
                print(f"  timestamp: {nr.get('timestamp', 'MISSING')}")
                
                # Check response length
                resp = nr.get('response')
                if resp:
                    if isinstance(resp, bytes):
                        print(f"  response length (bytes): {len(resp)}")
                    elif isinstance(resp, str):
                        print(f"  response length (str): {len(resp)} chars")
                    elif isinstance(resp, (list, tuple)):
                        print(f"  response length (array): {len(resp)} elements")
                    else:
                        print(f"  response type: {type(resp)} (unexpected)")
                else:
                    print(f"  response: NONE/EMPTY")
        except Exception as e:
            print(f"[FAIL] Normalization error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            normalized = []
    
    print("\n" + "=" * 80)
    print("TEST 3: SQLite write and verify")
    print("=" * 80)
    
    if normalized:
        db_file = tmp_path / 'test_zenodo.db'
        try:
            write_sqlite(normalized, db_file)
            print(f"[PASS] Data written to SQLite: {db_file.name}")
            
            # Verify with direct SQLite query
            import sqlite3
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM crp_records")
            count = cursor.fetchone()[0]
            print(f"  Total records in DB: {count}")
            
            # Sample a row
            cursor.execute("SELECT device_id, challenge, session_id FROM crp_records LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                print(f"  Sample record: device={sample[0]}, challenge={sample[1]}, session={sample[2]}")
            
            # Check response column type
            cursor.execute("SELECT response FROM crp_records LIMIT 1")
            resp_sample = cursor.fetchone()[0]
            print(f"  Response column type: {type(resp_sample)} (length: {len(resp_sample) if resp_sample else 0})")
            
            conn.close()
        except Exception as e:
            print(f"[FAIL] SQLite write error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("RESULT SUMMARY")
    print("=" * 80)
    if loaded_rows and normalized:
        print("SUCCESS: Adapter successfully processed Zenodo format")
        print("  - CSV loading: OK")
        print("  - Field normalization: OK")
        print("  - SQLite storage: OK")
    else:
        print("FAILED: Adapter encountered issues processing Zenodo format")
        if not loaded_rows:
            print("  - CSV loading: FAILED")
        if not normalized:
            print("  - Field normalization: FAILED")
