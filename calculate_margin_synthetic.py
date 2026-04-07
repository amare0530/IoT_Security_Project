#!/usr/bin/env python3
"""
Calculate separation margin from synthetic CRP data.

Margin = min(inter-device HD) - max(intra-device HD)

This measures uniqueness (inter-device variation) versus 
reliability (intra-device consistency).
"""

import json
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

# Device mapping from synthetic CRP generator
# Each entry: (device_id_hex, temperature, voltage)
DEVICE_CONFIG = {
    # This will be extracted from the database
}

def hex_to_int(hex_str: str) -> int:
    """Convert hex string to integer."""
    return int(hex_str, 16)

def hamming_distance(resp1: str, resp2: str) -> int:
    """Calculate Hamming distance between two hex responses."""
    if len(resp1) != len(resp2):
        raise ValueError(f"Length mismatch: {len(resp1)} vs {len(resp2)}")
    
    # Convert hex to int, then count differing bits
    int1 = int(resp1, 16) if resp1 else 0
    int2 = int(resp2, 16) if resp2 else 0
    
    # XOR and count bits
    diff = int1 ^ int2
    return bin(diff).count('1')

def get_responses_by_device(db_path: str) -> dict:
    """
    Load all responses grouped by device.
    Returns: {device_id: [(challenge, response, temp, voltage), ...]}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all CRP records, keeping track of condition
    query = """
    SELECT 
        device_id,
        challenge,
        response,
        temperature_c,
        supply_proxy,
        session_id
    FROM crp_records
    ORDER BY device_id, challenge
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    result = defaultdict(list)
    for device_id, challenge, response, temp, voltage, session in rows:
        result[device_id].append({
            'challenge': challenge,
            'response': response,
            'temperature': float(temp) if temp else 0.0,
            'voltage': voltage,
            'session': session
        })
    
    return dict(result)

def calculate_intra_device_hd(responses: list) -> list:
    """
    Calculate Hamming distances within a device across samples.
    Takes response pairs from same device same challenge, different samples.
    """
    hds = []
    
    # Group by challenge to find same-challenge responses
    by_challenge = defaultdict(list)
    for resp_rec in responses:
        key = resp_rec['challenge']
        by_challenge[key].append(resp_rec['response'])
    
    # For each challenge with multiple samples, calculate pairwise HD
    for challenge, resp_list in by_challenge.items():
        if len(resp_list) > 1:
            for i in range(len(resp_list)):
                for j in range(i + 1, len(resp_list)):
                    hd = hamming_distance(resp_list[i], resp_list[j])
                    hds.append(hd)
    
    return hds

def calculate_inter_device_hd(all_responses: dict) -> list:
    """
    Calculate Hamming distances between different devices.
    Takes one response per device per challenge.
    """
    hds = []
    
    devices = list(all_responses.keys())
    
    # For each challenge, calculate pairwise HD between devices
    # Get max challenge count
    max_challenges = max(len(resps) for resps in all_responses.values())
    
    for challenge_idx in range(max_challenges):
        device_responses = {}
        
        for device_id, responses in all_responses.items():
            if challenge_idx < len(responses):
                device_responses[device_id] = responses[challenge_idx]['response']
        
        # Calculate pairwise distances for this challenge
        device_list = list(device_responses.keys())
        for i in range(len(device_list)):
            for j in range(i + 1, len(device_list)):
                dev1, dev2 = device_list[i], device_list[j]
                resp1 = device_responses[dev1]
                resp2 = device_responses[dev2]
                hd = hamming_distance(resp1, resp2)
                hds.append(hd)
    
    return hds

def percentile(values: list, p: float) -> float:
    """Calculate percentile of sorted values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 1:
        return float(sorted_vals[-1])
    idx = int(round((len(sorted_vals) - 1) * p))
    return float(sorted_vals[max(0, min(idx, len(sorted_vals) - 1))])

def stats_dict(values: list) -> dict:
    """Generate statistics dictionary."""
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "p05": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "max": 0.0
        }
    
    sorted_vals = sorted(values)
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": float(sorted_vals[0]),
        "p05": percentile(values, 0.05),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": float(sorted_vals[-1])
    }

def main():
    db_path = "artifacts/zenodo_crp_synthetic.db"
    
    print("[*] Loading responses from database...")
    all_responses = get_responses_by_device(db_path)
    
    num_devices = len(all_responses)
    print(f"[*] Loaded {num_devices} devices")
    
    for dev_id, resps in list(all_responses.items())[:3]:
        print(f"    {dev_id}: {len(resps)} responses")
    
    print("\n[*] Calculating intra-device Hamming distances...")
    intra_hds = []
    for device_id, responses in all_responses.items():
        device_hds = calculate_intra_device_hd(responses)
        intra_hds.extend(device_hds)
    
    print(f"    Total intra-device pairs: {len(intra_hds)}")
    
    print("\n[*] Calculating inter-device Hamming distances...")
    inter_hds = calculate_inter_device_hd(all_responses)
    print(f"    Total inter-device pairs: {len(inter_hds)}")
    
    # Calculate statistics
    intra_stats = stats_dict(intra_hds)
    inter_stats = stats_dict(inter_hds)
    
    # Calculate margin
    intra_max = percentile(intra_hds, 0.95)  # worst-case reliability
    inter_min = percentile(inter_hds, 0.05)  # worst-case uniqueness
    margin = inter_min - intra_max
    
    print("\n" + "="*60)
    print("MARGIN ANALYSIS (Synthetic CRP Data)")
    print("="*60)
    print(f"\nIntra-device (Reliability):")
    print(f"  Mean HD: {intra_stats['mean']:.1f} bits")
    print(f"  95th %ile: {intra_max:.1f} bits (worst-case)")
    
    print(f"\nInter-device (Uniqueness):")
    print(f"  Mean HD: {inter_stats['mean']:.1f} bits")
    print(f"  5th %ile: {inter_min:.1f} bits (worst-case)")
    
    print(f"\nSeparation Margin:")
    print(f"  {margin:.1f} bits (inter-5% - intra-95%)")
    print(f"  {'✓ PASS' if margin > 50 else '✗ WARN'} (threshold: 50 bits)")
    
    print(f"\nECC Assessment:")
    if margin > 100:
        print(f"  → No ECC needed (margin > 100 bits)")
    elif margin > 50:
        print(f"  → Light ECC possible (margin 50-100 bits)")
    else:
        print(f"  → Strong ECC required (margin < 50 bits)")
    
    # Save results
    results = {
        "metadata": {
            "source": "zenodo_crp_synthetic.db",
            "num_devices": num_devices,
            "intra_device_pairs": len(intra_hds),
            "inter_device_pairs": len(inter_hds)
        },
        "intra_device": intra_stats,
        "inter_device": inter_stats,
        "margin": {
            "intra_95th": intra_max,
            "inter_5th": inter_min,
            "separation_bits": margin
        }
    }
    
    output_path = Path("artifacts/margin_analysis_synthetic.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n[*] Results saved to {output_path}")

if __name__ == "__main__":
    main()
