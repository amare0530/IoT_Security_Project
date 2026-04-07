#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 3: Extreme Environment Testing
極限環境測試 - 比較標準環境 vs 極端惡劣環境下的系統表現
"""

import os
import json
import csv
import time
from datetime import datetime
from typing import List, Dict
import math
import statistics

from puf_simulator import (
    PUFSimulator,
    PUFConfig,
    AuthenticationEngine,
    generate_challenge
)

class ExtremeTestConfig:
    """極限環境測試配置"""
    
    # Standard environment (baseline)
    STANDARD_NOISE_SIGMA = 0.05
    
    # Extreme environment (harsh conditions)
    EXTREME_NOISE_SIGMA = 0.15  # 3x worse than standard
    
    # Test parameters
    NUM_GENUINE = 100
    NUM_IMPOSTOR = 100
    
    # PUF parameters
    puf_key = "EXTREME_TEST_DEVICE_001"
    
    # Output paths
    OUTPUT_DIR = os.path.join("artifacts", "extreme_env_test")
    OUTPUT_STANDARD = os.path.join(OUTPUT_DIR, "standard_environment.json")
    OUTPUT_EXTREME = os.path.join(OUTPUT_DIR, "extreme_environment.json")
    OUTPUT_COMPARISON = os.path.join(OUTPUT_DIR, "environment_comparison.json")
    OUTPUT_CONTRAST_PLOT = os.path.join(OUTPUT_DIR, "contrast_roc_curve.png")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def run_environment_test(noise_sigma: float, environment_name: str, config: ExtremeTestConfig) -> Dict:
    """
    執行單一環境下的測試
    
    Returns:
      測試結果字典
    """
    print(f"\n{'='*70}")
    print(f" Testing {environment_name} Environment (σ={noise_sigma})")
    print(f"{'='*70}")
    
    # Setup
    puf_config = PUFConfig(
        noise_sigma=noise_sigma,
        bias_ratio=0.10,
        bias_strength=0.90
    )
    puf = PUFSimulator(config.puf_key, puf_config)
    auth_engine = AuthenticationEngine(threshold=50)
    
    genuine_hds = []
    impostor_hds = []
    
    # Genuine tests
    print(f"\n【Genuine Tests】({config.NUM_GENUINE} randomly generated challenges)")
    for i in range(config.NUM_GENUINE):
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{config.NUM_GENUINE}")
        
        challenge = generate_challenge(f"genuine_{i}")
        ideal_resp, noisy_resp1 = puf.generate_response(challenge, add_noise=True)
        _, noisy_resp2 = puf.generate_response(challenge, add_noise=True)
        
        hd = puf.get_hamming_distance(noisy_resp1, noisy_resp2)
        genuine_hds.append(hd)
    
    # Impostor tests
    print(f"\n【Impostor Tests】({config.NUM_IMPOSTOR} cross-device challenges)")
    for i in range(config.NUM_IMPOSTOR):
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{config.NUM_IMPOSTOR}")
        
        challenge_a = generate_challenge(f"impostor_a_{i}")
        challenge_b = generate_challenge(f"impostor_b_{i}")
        
        _, resp_a = puf.generate_response(challenge_a, add_noise=True)
        _, resp_b = puf.generate_response(challenge_b, add_noise=True)
        
        hd = puf.get_hamming_distance(resp_a, resp_b)
        impostor_hds.append(hd)
    
    # Compute statistics
    genuine_mean = statistics.mean(genuine_hds)
    genuine_std = statistics.stdev(genuine_hds) if len(genuine_hds) > 1 else 0
    impostor_mean = statistics.mean(impostor_hds)
    impostor_std = statistics.stdev(impostor_hds) if len(impostor_hds) > 1 else 0
    
    # Calculate FAR/FRR metrics at different thresholds
    roc_data = {}
    for threshold in range(30, 65, 5):
        genuine_pass = sum(1 for hd in genuine_hds if hd <= threshold)
        impostor_pass = sum(1 for hd in impostor_hds if hd <= threshold)
        
        far = impostor_pass / len(impostor_hds) if impostor_hds else 0.0
        frr = (len(genuine_hds) - genuine_pass) / len(genuine_hds) if genuine_hds else 0.0
        
        roc_data[threshold] = {
            "FAR": round(far, 4),
            "FRR": round(frr, 4),
            "accuracy": round((genuine_pass + len(impostor_hds) - impostor_pass) / (len(genuine_hds) + len(impostor_hds)), 4)
        }
    
    # Print statistics
    print(f"\n【Statistics】")
    print(f" Genuine:  mean={genuine_mean:.2f}, std={genuine_std:.2f}, range=[{min(genuine_hds)}, {max(genuine_hds)}]")
    print(f" Impostor: mean={impostor_mean:.2f}, std={impostor_std:.2f}, range=[{min(impostor_hds)}, {max(impostor_hds)}]")
    print(f" Separation: {impostor_mean - genuine_mean:.2f} bits ({impostor_mean/genuine_mean:.2f}x)")
    
    result = {
        "environment": environment_name,
        "noise_sigma": noise_sigma,
        "timestamp": config.timestamp,
        "statistics": {
            "genuine": {
                "count": len(genuine_hds),
                "mean_hd": round(genuine_mean, 2),
                "std_dev": round(genuine_std, 2),
                "min_hd": min(genuine_hds),
                "max_hd": max(genuine_hds)
            },
            "impostor": {
                "count": len(impostor_hds),
                "mean_hd": round(impostor_mean, 2),
                "std_dev": round(impostor_std, 2),
                "min_hd": min(impostor_hds),
                "max_hd": max(impostor_hds)
            },
            "separation_bits": round(impostor_mean - genuine_mean, 2),
            "separation_ratio": round(impostor_mean / genuine_mean, 2)
        },
        "roc_points": roc_data,
        "genuine_hds": genuine_hds,  # Raw data for comparison plot
        "impostor_hds": impostor_hds
    }
    
    return result


def generate_comparison_report(standard_result: Dict, extreme_result: Dict) -> Dict:
    """生成對比報告"""
    
    print(f"\n{'='*70}")
    print("【Environment Comparison Analysis】")
    print(f"{'='*70}")
    
    std_genuine = standard_result["statistics"]["genuine"]["mean_hd"]
    ext_genuine = extreme_result["statistics"]["genuine"]["mean_hd"]
    std_impostor = standard_result["statistics"]["impostor"]["mean_hd"]
    ext_impostor = extreme_result["statistics"]["impostor"]["mean_hd"]
    
    genuine_degradation = ((ext_genuine - std_genuine) / std_genuine) * 100
    impostor_degradation = ((ext_impostor - std_impostor) / std_impostor) * 100 if std_impostor > 0 else 0
    
    print(f"\n Genuine HD (合法用戶):")
    print(f"  Standard: {std_genuine:.2f}")
    print(f"  Extreme:  {ext_genuine:.2f}")
    print(f"  Degradation: {genuine_degradation:+.1f}%")
    
    print(f"\n Impostor HD (冒充者):")
    print(f"  Standard: {std_impostor:.2f}")
    print(f"  Extreme:  {ext_impostor:.2f}")
    print(f"  Degradation: {impostor_degradation:+.1f}%")
    
    print(f"\n Separation:")
    print(f"  Standard: {(std_impostor - std_genuine):.2f} bits ({(std_impostor/std_genuine):.2f}x)")
    print(f"  Extreme:  {(ext_impostor - ext_genuine):.2f} bits ({(ext_impostor/ext_genuine):.2f}x)")
    
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "standard_environment": standard_result["environment"],
        "extreme_environment": extreme_result["environment"],
        "noise_ratio": extreme_result["noise_sigma"] / standard_result["noise_sigma"],
        "genuine_hd_comparison": {
            "standard": std_genuine,
            "extreme": ext_genuine,
            "degradation_percent": round(genuine_degradation, 2)
        },
        "impostor_hd_comparison": {
            "standard": std_impostor,
            "extreme": ext_impostor,
            "degradation_percent": round(impostor_degradation, 2)
        },
        "system_resilience": "EXCELLENT" if genuine_degradation < 30 else "GOOD" if genuine_degradation < 50 else "FAIR"
    }
    
    print(f"\n  System Resilience: {comparison['system_resilience']}")
    
    return comparison


def main():
    config = ExtremeTestConfig()
    
    # Create output directory
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    print("="*70)
    print("Phase 3: Extreme Environment Testing")
    print("比較標準環境 vs 極端惡劣環境")
    print("="*70)
    
    # Test standard environment
    standard_result = run_environment_test(
        config.STANDARD_NOISE_SIGMA,
        "Standard",
        config
    )
    
    # Save standard results
    with open(config.OUTPUT_STANDARD, 'w', encoding='utf-8') as f:
        # Remove raw data before saving
        result_to_save = {k: v for k, v in standard_result.items() if k not in ['genuine_hds', 'impostor_hds']}
        json.dump(result_to_save, f, indent=2, ensure_ascii=False)
    print(f"\n Saved: {config.OUTPUT_STANDARD}")
    
    # Test extreme environment
    extreme_result = run_environment_test(
        config.EXTREME_NOISE_SIGMA,
        "Extreme",
        config
    )
    
    # Save extreme results
    with open(config.OUTPUT_EXTREME, 'w', encoding='utf-8') as f:
        result_to_save = {k: v for k, v in extreme_result.items() if k not in ['genuine_hds', 'impostor_hds']}
        json.dump(result_to_save, f, indent=2, ensure_ascii=False)
    print(f" Saved: {config.OUTPUT_EXTREME}")
    
    # Generate comparison
    comparison = generate_comparison_report(standard_result, extreme_result)
    with open(config.OUTPUT_COMPARISON, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    print(f" Saved: {config.OUTPUT_COMPARISON}")
    
    print(f"\n{'='*70}")
    print(" Phase 3 Extreme Environment Testing Complete!")
    print(f"{'='*70}")
    print(f"\nOutput files:")
    print(f"  📄 {config.OUTPUT_STANDARD}")
    print(f"  📄 {config.OUTPUT_EXTREME}")
    print(f"  📄 {config.OUTPUT_COMPARISON}")


if __name__ == '__main__':
    main()

