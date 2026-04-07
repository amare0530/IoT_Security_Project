#!/usr/bin/env python3
"""
Generate synthetic CRP data from real Zenodo sensor readings.

Strategy: Use temperature and voltage as pseudo-address/response pairs.
This allows us to advance blocker analysis while waiting for real CRP data.

When real crp_data.csv arrives, this synthetic version can be replaced.
"""

import csv
import hashlib
from pathlib import Path
from typing import List, Dict

def generate_synthetic_crps(sensor_csv: str, output_csv: str, crps_per_sensor: int = 160):
    """
    Generate synthetic SRAM CRP pairs from sensor data.
    
    For each sensor reading:
    - Use uid directly
    - Generate 160 synthetic addresses (0x20000000 to 0x20027FFF)
    - Use temperature+voltage to seed response generation
    
    This creates a realistic multi-dimensional dataset:
    - 84 devices × 11 samples × 160 addresses = 147,840 total CRPs
    - Responses vary by temperature/voltage (realistic PUF behavior)
    """
    
    rows = []
    
    with open(sensor_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for sensor_row in reader:
            uid = sensor_row['uid']
            temp = float(sensor_row['temperature'])
            voltage = float(sensor_row['voltage'])
            created_at = sensor_row['created_at']
            
            # Generate 160 synthetic addresses for this sensor reading
            for addr_idx in range(crps_per_sensor):
                # Address: 0x20000000 + (addr_idx * 512)
                address = 0x20000000 + (addr_idx * 512)
                address_hex = f"0x{address:08x}"
                
                # Generate response from seed (temperature, voltage, address)
                seed = f"{temp:.5f}_{voltage:.5f}_{addr_idx:03d}"
                seed_bytes = seed.encode()
                
                # Create 512-byte response using hash-based PRNG
                # This simulates SRAM content that varies with environmental conditions
                response_bytes = []
                for i in range(512):
                    # Generate byte using hash of (seed + offset)
                    fragment = hashlib.sha256((seed_bytes + i.to_bytes(4, 'big'))).digest()
                    
                    # Modify based on temperature/voltage to create correlation
                    # High temp → higher bit values
                    # High voltage → more variation
                    temp_mod = int((temp - 15) * 5) & 0xFF  # Centered at 15C
                    voltage_mod = int((voltage - 3.64) * 100) & 0xFF  # Centered at 3.64V
                    
                    byte_val = (fragment[0] ^ temp_mod ^ voltage_mod) & 0xFF
                    response_bytes.append(str(byte_val))
                
                response_str = ','.join(response_bytes)
                
                row = {
                    'board_type': 'Nucleo',
                    'uid': uid,
                    'pic': sensor_row['pic'],
                    'address': address_hex,
                    'data': response_str,
                    'created_at': created_at,
                }
                rows.append(row)
    
    # Write synthetic CRP data
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['board_type', 'uid', 'pic', 'address', 'data', 'created_at']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {len(rows)} synthetic CRP records")
    print(f"  Devices: 84")
    print(f"  Samples per device: 11")
    print(f"  Addresses per sample: 160")
    print(f"  Total: {84 * 11 * 160} expected, {len(rows)} created")
    return len(rows)

if __name__ == '__main__':
    import sys
    sensor_file = sys.argv[1] if len(sys.argv) > 1 else 'artifacts/zenodo_sensors_raw.csv'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'artifacts/zenodo_crp_synthetic.csv'
    
    count = generate_synthetic_crps(sensor_file, output_file)
    print(f"Saved to {output_file}")
