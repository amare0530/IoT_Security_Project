#!/usr/bin/env python3
"""
Temperature-stratified margin analysis.

Calculate margin across three temperature ranges:
- Cold: 9-15°C (below historical average)
- Nominal: 16-25°C (design temperature)
- Hot: 26-34°C (high stress)
"""

import json
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

def hamming_distance(resp1: str, resp2: str) -> int:
    """Calculate Hamming distance between two hex responses."""
    if not resp1 or not resp2:
        return 0
    int1 = int(resp1, 16)
    int2 = int(resp2, 16)
    diff = int1 ^ int2
    return bin(diff).count('1')

def percentile(values: list, p: float) -> float:
    """Calculate percentile."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(round((len(sorted_vals) - 1) * p))
    return float(sorted_vals[max(0, min(idx, len(sorted_vals) - 1))])

def stats_dict(values: list) -> dict:
    """Generate statistics dictionary."""
    if not values:
        return {"count": 0, "mean": 0.0, "std": 0.0, "p05": 0.0, "p95": 0.0}
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "p05": percentile(values, 0.05),
        "p95": percentile(values, 0.95)
    }

def categorize_temp(temp: float) -> str:
    """Categorize temperature into cold/nominal/hot."""
    if temp < 15:
        return "cold"
    elif temp < 25:
        return "nominal"
    else:
        return "hot"

def analyze_by_temperature():
    """Calculate margin at each temperature range."""
    
    db_path = "artifacts/zenodo_crp_corrected_v2.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch all CRP records with temperature
    query = """
    SELECT 
        device_id, 
        challenge,
        response,
        temperature_c
    FROM crp_records
    ORDER BY device_id, challenge, temperature_c
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Organize by temperature category and device/challenge
    data_by_temp = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    
    temp_stats = {"cold": [], "nominal": [], "hot": []}
    
    for device_id, challenge, response, temp in rows:
        temp_cat = categorize_temp(temp)
        data_by_temp[temp_cat][device_id][challenge].append({
            "response": response,
            "temp": temp
        })
        temp_stats[temp_cat].append(temp)
    
    print("Temperature Distribution:")
    for cat in ["cold", "nominal", "hot"]:
        temps = temp_stats[cat]
        if temps:
            print(f"  {cat:10} ({len(temps):6} samples): "
                  f"{min(temps):5.1f}-{max(temps):5.1f}°C "
                  f"(mean {statistics.mean(temps):5.1f}°C)")
    
    # Calculate margin for each temperature category
    results = {}
    
    print("\n" + "="*70)
    print("TEMPERATURE-STRATIFIED MARGIN ANALYSIS")
    print("="*70)
    
    for temp_category in ["cold", "nominal", "hot"]:
        data = data_by_temp[temp_category]
        
        if not data:
            print(f"\n[{temp_category.upper()}] No data")
            continue
        
        # Calculate intra-device for this temperature
        intra_hds = []
        for device_id, challenges_dict in data.items():
            for challenge, resp_list in challenges_dict.items():
                responses = [r["response"] for r in resp_list]
                for i in range(len(responses)):
                    for j in range(i + 1, len(responses)):
                        hd = hamming_distance(responses[i], responses[j])
                        intra_hds.append(hd)
        
        # Calculate inter-device for this temperature
        inter_hds = []
        all_challenges = set()
        for device_data in data.values():
            all_challenges.update(device_data.keys())
        
        for challenge in all_challenges:
            device_responses = {}
            for device_id, challenges_dict in data.items():
                if challenge in challenges_dict:
                    resp_list = challenges_dict[challenge]
                    if resp_list:
                        device_responses[device_id] = resp_list[0]["response"]
            
            device_list = list(device_responses.keys())
            for i in range(len(device_list)):
                for j in range(i + 1, len(device_list)):
                    hd = hamming_distance(
                        device_responses[device_list[i]],
                        device_responses[device_list[j]]
                    )
                    inter_hds.append(hd)
        
        # Calculate margin
        intra_stats = stats_dict(intra_hds)
        inter_stats = stats_dict(inter_hds)
        
        intra_95 = intra_stats["p95"]
        inter_5 = inter_stats["p05"]
        margin = inter_5 - intra_95
        
        results[temp_category] = {
            "intra": intra_stats,
            "inter": inter_stats,
            "intra_p95": intra_95,
            "inter_p05": inter_5,
            "margin": margin,
            "pairs": {
                "intra": intra_stats["count"],
                "inter": inter_stats["count"]
            }
        }
        
        # Print summary
        print(f"\n{temp_category.upper()} TEMPERATURE RANGE:")
        print(f"  Intra-device (pairs: {intra_stats['count']}):")
        print(f"    Mean HD: {intra_stats['mean']:.1f} bits")
        print(f"    95th %ile: {intra_95:.1f} bits")
        print(f"  Inter-device (pairs: {inter_stats['count']}):")
        print(f"    Mean HD: {inter_stats['mean']:.1f} bits")
        print(f"    5th %ile: {inter_5:.1f} bits")
        print(f"  Margin: {margin:.1f} bits "
              f"{'PASS' if margin > 50 else 'FAIL'}")
    
    # Overall analysis
    print("\n" + "="*70)
    print("TEMPERATURE IMPACT ASSESSMENT")
    print("="*70)
    
    margins = [
        (results[cat]["margin"], cat) 
        for cat in ["cold", "nominal", "hot"] 
        if cat in results
    ]
    margins.sort(reverse=True)
    
    print(f"\nMargin by temperature (best to worst):")
    for margin, cat in margins:
        status = "PASS" if margin > 50 else "FAIL"
        print(f"  {cat:10} {margin:6.1f} bits [{status}]")
    
    min_margin = min(m[0] for m in margins) if margins else 0
    
    print(f"\nMinimum margin: {min_margin:.1f} bits")
    if min_margin > 100:
        print("  → ✓ ECC NOT NEEDED across all temperatures")
    elif min_margin > 50:
        print("  → ⚠ ECC OPTIONAL (light implementation)")
    else:
        print("  → ✗ ECC REQUIRED for operation at extreme temperatures")
    
    # Save results
    output = {
        "metadata": {
            "analysis": "temperature-stratified-margin",
            "source": "zenodo_crp_corrected_v2.db",
            "response_bits": 512
        },
        "by_temperature": results,
        "assessment": {
            "min_margin": min_margin,
            "recommendation": (
                "No ECC" if min_margin > 100 else
                "Optional ECC" if min_margin > 50 else
                "Required ECC"
            )
        }
    }
    
    output_path = Path("artifacts/margin_by_temperature.json")
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n[OK] Results saved to {output_path}")

if __name__ == "__main__":
    analyze_by_temperature()
