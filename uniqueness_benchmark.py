#!/usr/bin/env python
"""
Multi-device uniqueness benchmark for thesis-grade evidence.

What this script measures:
- Inter-device uniqueness: HD between different device ideal responses
- Intra-device reliability: HD between ideal and noisy response per device
- Separation margin: inter-device low percentile minus intra-device high percentile

Outputs:
- artifacts/uniqueness_benchmark_summary.json
- artifacts/uniqueness_benchmark_scenarios.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from config import get_realistic_puf_profile
from puf_simulator import PUFConfig, PUFSimulator, generate_challenge


ARTIFACT_DIR = Path("artifacts")
SUMMARY_JSON = ARTIFACT_DIR / "uniqueness_benchmark_summary.json"
SCENARIO_CSV = ARTIFACT_DIR / "uniqueness_benchmark_scenarios.csv"


@dataclass
class BenchmarkConfig:
    num_devices: int = 32
    num_challenges: int = 240
    seed: int = 20260406


def _percentile(sorted_values: List[int], p: float) -> float:
    if not sorted_values:
        return 0.0
    if p <= 0:
        return float(sorted_values[0])
    if p >= 1:
        return float(sorted_values[-1])
    idx = int(round((len(sorted_values) - 1) * p))
    idx = max(0, min(idx, len(sorted_values) - 1))
    return float(sorted_values[idx])


def _stats(values: List[int]) -> Dict[str, float]:
    ordered = sorted(values)
    return {
        "count": float(len(values)),
        "mean": float(statistics.mean(values)),
        "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
        "min": float(ordered[0]),
        "p01": _percentile(ordered, 0.01),
        "p05": _percentile(ordered, 0.05),
        "p50": _percentile(ordered, 0.50),
        "p95": _percentile(ordered, 0.95),
        "p99": _percentile(ordered, 0.99),
        "max": float(ordered[-1]),
    }


def _device_key(i: int) -> str:
    return f"UNIQ_DEVICE_{i:04d}"


def _build_profiles() -> Dict[str, PUFConfig]:
    realistic = get_realistic_puf_profile()

    return {
        "default_profile": PUFConfig(),
        "realistic_profile": PUFConfig(
            response_bits=256,
            noise_sigma=realistic["noise_sigma"],
            bias_ratio=realistic["bias_ratio"],
            bias_strength=realistic["bias_strength"],
            unstable_ratio=realistic["unstable_ratio"],
            unstable_extra_noise=realistic["unstable_extra_noise"],
            cluster_noise_prob=realistic["cluster_noise_prob"],
            cluster_size=realistic["cluster_size"],
            env_noise_sigma=realistic["env_noise_sigma"],
            env_spike_prob=realistic["env_spike_prob"],
            env_spike_min=realistic["env_spike_min"],
            env_spike_max=realistic["env_spike_max"],
        ),
    }


def _iter_pairs(n: int) -> Iterable[tuple[int, int]]:
    for i in range(n):
        for j in range(i + 1, n):
            yield i, j


def evaluate_profile(name: str, puf_cfg: PUFConfig, cfg: BenchmarkConfig) -> Dict:
    random.seed(cfg.seed)
    devices = [PUFSimulator(_device_key(i), puf_cfg) for i in range(cfg.num_devices)]

    inter_hds: List[int] = []
    intra_hds: List[int] = []

    for c_idx in range(cfg.num_challenges):
        challenge = generate_challenge(seed=f"uniq_{name}_{cfg.seed}_{c_idx}")

        ideal_responses = [dev.generate_ideal_response(challenge) for dev in devices]

        for i, j in _iter_pairs(cfg.num_devices):
            inter_hds.append(devices[i].get_hamming_distance(ideal_responses[i], ideal_responses[j]))

        for i, dev in enumerate(devices):
            _, noisy = dev.generate_response(challenge, add_noise=True)
            intra_hds.append(dev.get_hamming_distance(ideal_responses[i], noisy))

    inter_stats = _stats(inter_hds)
    intra_stats = _stats(intra_hds)

    separation_margin = inter_stats["p05"] - intra_stats["p95"]
    risk_flags = []
    if inter_stats["mean"] < 120.0:
        risk_flags.append("inter_device_mean_hd_below_120")
    if inter_stats["p05"] < 105.0:
        risk_flags.append("inter_device_p05_hd_below_105")
    if separation_margin < 70.0:
        risk_flags.append("weak_inter_intra_separation_margin")

    return {
        "profile": name,
        "num_devices": cfg.num_devices,
        "num_challenges": cfg.num_challenges,
        "inter_device_hd": inter_stats,
        "intra_device_hd": intra_stats,
        "separation_margin_p05_minus_p95": separation_margin,
        "risk_flags": risk_flags,
        "pass": len(risk_flags) == 0,
    }


def write_outputs(results: Dict[str, Dict], cfg: BenchmarkConfig) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "config": {
            "num_devices": cfg.num_devices,
            "num_challenges": cfg.num_challenges,
            "seed": cfg.seed,
        },
        "results": results,
    }

    with SUMMARY_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with SCENARIO_CSV.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "profile",
            "pass",
            "inter_mean",
            "inter_p05",
            "intra_mean",
            "intra_p95",
            "separation_margin",
            "risk_flags",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for profile, data in results.items():
            writer.writerow(
                {
                    "profile": profile,
                    "pass": data["pass"],
                    "inter_mean": round(data["inter_device_hd"]["mean"], 3),
                    "inter_p05": round(data["inter_device_hd"]["p05"], 3),
                    "intra_mean": round(data["intra_device_hd"]["mean"], 3),
                    "intra_p95": round(data["intra_device_hd"]["p95"], 3),
                    "separation_margin": round(data["separation_margin_p05_minus_p95"], 3),
                    "risk_flags": "|".join(data["risk_flags"]) if data["risk_flags"] else "none",
                }
            )


def parse_args() -> BenchmarkConfig:
    parser = argparse.ArgumentParser(description="Run multi-device uniqueness benchmark")
    parser.add_argument("--devices", type=int, default=32, help="Number of device identities")
    parser.add_argument("--challenges", type=int, default=240, help="Number of challenges per profile")
    parser.add_argument("--seed", type=int, default=20260406, help="Random seed")
    args = parser.parse_args()
    return BenchmarkConfig(num_devices=args.devices, num_challenges=args.challenges, seed=args.seed)


def main() -> None:
    cfg = parse_args()
    profiles = _build_profiles()
    results: Dict[str, Dict] = {}

    for name, puf_cfg in profiles.items():
        results[name] = evaluate_profile(name, puf_cfg, cfg)

    write_outputs(results, cfg)

    print("=" * 72)
    print("Uniqueness Benchmark Completed")
    print("=" * 72)
    print(f"Devices: {cfg.num_devices}")
    print(f"Challenges per profile: {cfg.num_challenges}")
    for profile, data in results.items():
        inter = data["inter_device_hd"]
        intra = data["intra_device_hd"]
        print("-" * 72)
        print(f"Profile: {profile}")
        print(f"Inter-device mean HD: {inter['mean']:.3f} (p05={inter['p05']:.3f})")
        print(f"Intra-device mean HD: {intra['mean']:.3f} (p95={intra['p95']:.3f})")
        print(f"Separation margin (p05 inter - p95 intra): {data['separation_margin_p05_minus_p95']:.3f}")
        if data["risk_flags"]:
            print(f"Risk flags: {', '.join(data['risk_flags'])}")
        else:
            print("Risk flags: none")
    print("-" * 72)
    print(f"Output JSON: {SUMMARY_JSON}")
    print(f"Output CSV:  {SCENARIO_CSV}")


if __name__ == "__main__":
    main()

