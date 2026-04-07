#!/usr/bin/env python3
"""
Calculate margin from corrected synthetic CRP data.

Key difference from v1:
- Intra-device: should be LOW (noise only, HD ≈ num_bit_flips ≈ 2%)
- Inter-device: should be HIGH (different device keys, HD ≈ 50%)
"""

import json
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

def hex_to_int(hex_str: str) -> int:
    """Convert hex string to integer."""
    return int(hex_str, 16) if hex_str else 0

def hamming_distance(resp1: str, resp2: str) -> int:
    """Calculate Hamming distance between two hex responses."""
    if not resp1 or not resp2:
        return 0
    if len(resp1) != len(resp2):
        raise ValueError(f"Length mismatch: {len(resp1)} vs {len(resp2)}")
    
    # Convert hex to int, XOR, count bits
    int1 = int(resp1, 16)
    int2 = int(resp2, 16)
    diff = int1 ^ int2
    return bin(diff).count('1')

def get_responses_by_device_challenge(db_path: str) -> dict:
    """
    Load all responses grouped by device and challenge.
    
    Returns:
      {device_id: {challenge: [response1, response2, ...], ...}, ...}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        device_id,
        challenge,
        response
    FROM crp_records
    ORDER BY device_id, challenge, created_at
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    result = defaultdict(lambda: defaultdict(list))
    for device_id, challenge, response in rows:
        result[device_id][challenge].append(response)
    
    return dict((k, dict(v)) for k, v in result.items())

def calculate_intra_device_hd(responses_by_challenge: dict) -> list:
    """
    Calculate Hamming distances within a device.
    For each challenge, compare samples from same device, same challenge.
    """
    hds = []
    
    for challenge, resp_list in responses_by_challenge.items():
        # Compare all pairs of samples for same challenge
        for i in range(len(resp_list)):
            for j in range(i + 1, len(resp_list)):
                hd = hamming_distance(resp_list[i], resp_list[j])
                hds.append(hd)
    
    return hds

def calculate_inter_device_hd(all_responses: dict) -> list:
    """
    Calculate Hamming distances between different devices.
    
    For each challenge, take one response per device and compare.
    """
    hds = []
    
    # Get all challenges (should be same across devices)
    all_challenges = set()
    for device_resps in all_responses.values():
        all_challenges.update(device_resps.keys())
    
    for challenge in all_challenges:
        device_list = []
        device_responses = {}
        
        for device_id, responses_by_challenge in all_responses.items():
            if challenge in responses_by_challenge:
                resp_list = responses_by_challenge[challenge]
                if resp_list:  # Take first sample
                    device_list.append(device_id)
                    device_responses[device_id] = resp_list[0]
        
        # Calculate pairwise distances for this challenge
        for i in range(len(device_list)):
            for j in range(i + 1, len(device_list)):
                dev1, dev2 = device_list[i], device_list[j]
                hd = hamming_distance(device_responses[dev1], device_responses[dev2])
                hds.append(hd)
    
    return hds

def percentile(values: list, p: float) -> float:
    """Calculate percentile of values."""
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
    db_path = "artifacts/zenodo_crp_corrected_v2.db"
    
    print("[*] Loading responses from database...")
    all_responses = get_responses_by_device_challenge(db_path)
    
    num_devices = len(all_responses)
    print(f"[*] Loaded {num_devices} devices")
    
    for dev_id, challenges_dict in list(all_responses.items())[:2]:
        total_samples = sum(len(v) for v in challenges_dict.values())
        print(f"    {dev_id}: {total_samples} total samples across {len(challenges_dict)} challenges")
    
    print("\n[*] Calculating intra-device Hamming distances...")
    intra_hds = []
    for device_id, responses_by_challenge in all_responses.items():
        device_hds = calculate_intra_device_hd(responses_by_challenge)
        intra_hds.extend(device_hds)
    
    print(f"    Total intra-device pairs: {len(intra_hds)}")
    if intra_hds:
        print(f"    Sample intra-device HDs: {intra_hds[:10]}")
    
    print("\n[*] Calculating inter-device Hamming distances...")
    inter_hds = calculate_inter_device_hd(all_responses)
    print(f"    Total inter-device pairs: {len(inter_hds)}")
    if inter_hds:
        print(f"    Sample inter-device HDs: {inter_hds[:10]}")
    
    # Calculate statistics
    intra_stats = stats_dict(intra_hds)
    inter_stats = stats_dict(inter_hds)
    
    # Calculate margin
    intra_max = percentile(intra_hds, 0.95)  # worst-case reliability
    inter_min = percentile(inter_hds, 0.05)  # worst-case uniqueness
    margin = inter_min - intra_max
    
    print("\n" + "="*70)
    print("MARGIN ANALYSIS (Corrected Synthetic CRP Data - PUF Model v2)")
    print("="*70)
    print(f"\nIntra-device (Reliability - same device, same challenge, different samples):")
    print(f"  Mean HD: {intra_stats['mean']:.1f} bits")
    print(f"  Std Dev: {intra_stats['std']:.1f} bits")
    print(f"  95th %ile: {intra_max:.1f} bits (worst-case reliability)")
    print(f"  → Expected: ≈ {512 * 2 * 0.02:.0f} bits (2% × 512 bytes × 2)")
    
    print(f"\nInter-device (Uniqueness - different devices, same challenge):")
    print(f"  Mean HD: {inter_stats['mean']:.1f} bits")
    print(f"  Std Dev: {inter_stats['std']:.1f} bits")
    print(f"  5th %ile: {inter_min:.1f} bits (worst-case uniqueness)")
    print(f"  → Expected: ≈ {512 * 4:.0f} bits (50% × 512 bytes × 2)")
    
    print(f"\nSeparation Margin:")
    print(f"  {margin:.1f} bits = inter-5% ({inter_min:.0f}) - intra-95% ({intra_max:.0f})")
    print(f"  {'✓ PASS' if margin > 50 else '✗ FAIL'} (threshold: 50 bits)")
    
    print(f"\nECC Assessment:")
    if margin > 100:
        print(f"  → ✓ No ECC needed (margin > 100 bits)")
    elif margin > 50:
        print(f"  → ⚠ Light ECC possible (margin 50-100 bits)")
    else:
        print(f"  → ✗ Strong ECC required (margin < 50 bits)")
    
    # Save results
    results = {
        "metadata": {
            "source": "zenodo_crp_corrected.db",
            "model": "PUF v2 (deterministic ideal + gaussian noise)",
            "num_devices": num_devices,
            "num_challenges_per_device": 160,
            "num_samples_per_challenge": 11,
            "response_bits": 512,
            "noise_sigma": 0.02,
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
    
    output_path = Path("artifacts/margin_analysis_corrected.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n[✓] Results saved to {output_path}")

if __name__ == "__main__":
    main()
