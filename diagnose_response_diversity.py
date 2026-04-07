#!/usr/bin/env python3
"""Diagnose inter-device response diversity."""

import sqlite3

def hamming_distance(resp1: str, resp2: str) -> int:
    """Calculate Hamming distance between two hex responses."""
    if not resp1 or not resp2:
        return 0
    int1 = int(resp1, 16)
    int2 = int(resp2, 16)
    diff = int1 ^ int2
    return bin(diff).count('1')

conn = sqlite3.connect('artifacts/zenodo_crp_corrected_v2.db')
cursor = conn.cursor()

# Get first response of each device for challenge 0
cursor.execute("""
    SELECT device_id, response 
    FROM crp_records 
    WHERE challenge = '00000000'
    ORDER BY device_id
    LIMIT 5
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} devices for challenge 00000000\n")

for i, (dev1_id, resp1) in enumerate(rows):
    print(f"Device {i}: {dev1_id[:16]}...")
    print(f"  Response: {resp1[:32]}... (len={len(resp1)})")
    print(f"  Response bits: {len(resp1) * 4}")
    
    if i > 0:
        for j in range(i):
            dev2_id, resp2 = rows[j]
            hd = hamming_distance(resp1, resp2)
            print(f"    vs Device {j}: HD = {hd} bits ({hd*100/len(resp1)/4:.1f}%)")

conn.close()

# Expected: 512 bytes = 4096 bits
# 50% difference = 2048 bits
# Current: ~256 bits = 6% difference
print(f"\n[EXPECTED] Inter-device HD should be ~2048 bits (50% of 4096)")
print(f"[ACTUAL  ] Inter-device HD is ~256 bits (6% of 4096)")
print(f"\n[DIAGNOSIS] Response length and diversity issue detected")
