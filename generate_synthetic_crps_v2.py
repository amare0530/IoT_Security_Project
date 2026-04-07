#!/usr/bin/env python3
"""
Generate synthetic CRP using proper PUF model.

Key insight: PUF responses should be:
1. DETERMINISTIC within device for same challenge (ideal response)
2. NOISY across samples (gaussian noise added)
3. UNIQUE across devices (different physical properties)

This matches real STM32 SRAM PUF behavior.
"""

import csv
import hashlib
import random
from pathlib import Path

def hash_based_prng(seed: str, num_bytes: int) -> str:
    """Generate deterministic pseudo-random bytes using SHA-256."""
    h = hashlib.sha256(seed.encode())
    result = ""
    for i in range(num_bytes):
        h.update(h.digest())
        result += f"{h.digest()[0]:02x}"
    result = ""
    h = hashlib.sha256(seed.encode())
    while len(result) < num_bytes * 2:
        result += h.hexdigest()
        h = hashlib.sha256(h.digest())
    return result[:num_bytes * 2]

def device_key_for_id(device_id: str, sample_idx: int) -> str:
    """Generate unique physical key per device (constant across samples)."""
    return f"physkey_{device_id}_{sample_idx}"

def ideal_response(device_key: str, challenge_hex: str, bits: int = 4096) -> str:
    """
    Generate ideal (noiseless) response for a device+challenge.
    This is DETERMINISTIC per device, repeatable across samples.
    
    bits: 4096 = 512 bytes
    """
    seed = f"{device_key}|challenge={challenge_hex}"
    return hash_based_prng(seed, bits // 8)  # bits to bytes

def add_gaussian_noise(response_hex: str, noise_sigma: float = 0.02) -> str:
    """
    Add gaussian noise to response.
    noise_sigma: probability of bit flip (typically 0.01-0.05)
    """
    # Convert hex to bits
    bits = bin(int(response_hex, 16))[2:].zfill(len(response_hex) * 4)
    
    # Flip bits according to gaussian noise
    bits_list = list(bits)
    num_flips = int(len(bits) * noise_sigma * random.gauss(1.0, 0.1))
    flip_indices = random.sample(range(len(bits)), min(num_flips, len(bits)))
    
    for idx in flip_indices:
        bits_list[idx] = '0' if bits_list[idx] == '1' else '1'
    
    # Convert back to hex
    noisy_bits = ''.join(bits_list)
    noisy_int = int(noisy_bits, 2)
    noisy_hex = f"{noisy_int:0{len(response_hex)}x}"
    
    return noisy_hex

def main():
    # Load sensor data to get device list and conditions
    sensor_db_path = Path("artifacts/zenodo_sensors_raw.csv")
    
    if not sensor_db_path.exists():
        print(f"[!] Sensor data not found: {sensor_db_path}")
        return
    
    # Parse sensors to get unique (device_id, temperature, voltage)
    sensors = {}
    with open(sensor_db_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            device_id = row['uid']
            if device_id not in sensors:
                sensors[device_id] = []
            sensors[device_id].append({
                'temperature': float(row['temperature']),
                'voltage': float(row['voltage']),
                'sample_idx': len(sensors[device_id])
            })
    
    print(f"[*] Loaded {len(sensors)} devices from sensor data")
    
    # Configuration
    NUM_ADDRESSES = 160  # addresses per device per sample
    NUM_RESPONSE_BYTES = 64  # 512 bits per response
    NOISE_SIGMA = 0.02  # 2% bit flip rate
    
    crp_output = Path("artifacts/zenodo_crp_corrected.csv")
    
    print(f"[*] Generating {len(sensors)} devices × {NUM_ADDRESSES} addresses × {len(sensors[list(sensors.keys())[0]])} samples")
    print(f"[*] Response size: {NUM_RESPONSE_BYTES} bytes ({NUM_RESPONSE_BYTES * 8} bits)")
    print(f"[*] Noise level: {NOISE_SIGMA * 100:.1f}% bit flip rate")
    
    total_records = 0
    
    with open(crp_output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'device_id', 'sample_idx', 'address_idx', 'challenge', 'response',
            'temperature', 'voltage'
        ])
        writer.writeheader()
        
        for device_id, samples in sorted(sensors.items()):
            # Generate ONCE per device: the ideal response for each address
            # This ensures intra-device consistency
            device_key = device_key_for_id(device_id, 0)
            ideal_responses = {}
            
            for addr_idx in range(NUM_ADDRESSES):
                challenge_hex = f"{addr_idx:08x}"
                ideal = ideal_response(device_key, challenge_hex, NUM_RESPONSE_BYTES * 8)
                ideal_responses[addr_idx] = ideal
            
            # Now generate samples: same ideal, but with noise added
            for sample in samples:
                sample_idx = sample['sample_idx']
                temp = sample['temperature']
                voltage = sample['voltage']
                
                for addr_idx in range(NUM_ADDRESSES):
                    challenge_hex = f"{addr_idx:08x}"
                    ideal = ideal_responses[addr_idx]
                    
                    # Add noise (slight temperature-dependent noise)
                    # Higher temperature → slightly more noise
                    temp_noise_factor = 1.0 + (temp - 16.0) / 100.0  # ±2% based on temp
                    effective_sigma = NOISE_SIGMA * max(0.5, min(1.5, temp_noise_factor))
                    
                    noisy = add_gaussian_noise(ideal, effective_sigma)
                    
                    writer.writerow({
                        'device_id': device_id,
                        'sample_idx': sample_idx,
                        'address_idx': addr_idx,
                        'challenge': challenge_hex,
                        'response': noisy,
                        'temperature': temp,
                        'voltage': voltage
                    })
                    
                    total_records += 1
    
    print(f"\n[*] Generated {total_records} CRP records")
    print(f"[*] Saved to {crp_output}")
    
    # Show sample
    print(f"\n[*] Sample records:")
    with open(crp_output) as f:
        for i, line in enumerate(f):
            if i < 4:
                print(f"  {line.strip()}")
            if i >= 10:
                break

if __name__ == "__main__":
    main()
