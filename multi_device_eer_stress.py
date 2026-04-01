#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-device EER stress test with bootstrap confidence intervals.

Goal:
- Evaluate whether EER remains stable across many device identities
- Use a realistic, non-IID noise profile from config
- Export reproducible metrics for thesis/reporting
"""

import csv
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from config import get_realistic_puf_profile
from puf_simulator import PUFConfig, PUFSimulator, generate_challenge


ARTIFACT_DIR = Path("artifacts")
DEVICE_CSV = ARTIFACT_DIR / "multi_device_eer_by_device.csv"
SUMMARY_JSON = ARTIFACT_DIR / "multi_device_eer_summary.json"


@dataclass
class StressConfig:
    num_devices: int = 60
    sessions_per_device: int = 400
    bootstrap_rounds: int = 1000
    random_seed: int = 20260401


def compute_metrics_for_threshold(
    genuine_hds: List[int], impostor_hds: List[int], threshold: int
) -> Tuple[float, float]:
    far = sum(1 for x in impostor_hds if x <= threshold) / len(impostor_hds)
    frr = sum(1 for x in genuine_hds if x > threshold) / len(genuine_hds)
    return far, frr


def compute_eer(genuine_hds: List[int], impostor_hds: List[int]) -> Dict[str, float]:
    best = None
    for threshold in range(0, 257):
        far, frr = compute_metrics_for_threshold(genuine_hds, impostor_hds, threshold)
        gap = abs(far - frr)
        score = (gap, (far + frr) / 2.0, threshold, far, frr)
        if best is None or score < best:
            best = score

    assert best is not None
    _, eer, threshold, far, frr = best
    return {
        "threshold": int(threshold),
        "eer": float(eer),
        "far": float(far),
        "frr": float(frr),
    }


def bootstrap_ci(values: List[float], rounds: int, seed: int) -> Dict[str, float]:
    rng = random.Random(seed)
    samples = []
    n = len(values)

    for _ in range(rounds):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(statistics.mean(draw))

    samples.sort()
    low = samples[int(0.025 * rounds)]
    high = samples[int(0.975 * rounds)]
    return {
        "mean": float(statistics.mean(values)),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "std": float(statistics.pstdev(values)),
    }


def build_realistic_puf_config() -> PUFConfig:
    p = get_realistic_puf_profile()
    return PUFConfig(
        response_bits=256,
        noise_sigma=p["noise_sigma"],
        bias_ratio=p["bias_ratio"],
        bias_strength=p["bias_strength"],
        unstable_ratio=p["unstable_ratio"],
        unstable_extra_noise=p["unstable_extra_noise"],
        cluster_noise_prob=p["cluster_noise_prob"],
        cluster_size=p["cluster_size"],
        env_noise_sigma=p["env_noise_sigma"],
        env_spike_prob=p["env_spike_prob"],
        env_spike_min=p["env_spike_min"],
        env_spike_max=p["env_spike_max"],
    )


def run_stress(cfg: StressConfig) -> Dict:
    random.seed(cfg.random_seed)

    per_device_rows = []
    device_eers = []
    threshold_votes = []

    for dev_idx in range(cfg.num_devices):
        device_key = f"DEVICE_KEY_{dev_idx:04d}"
        attacker_key = f"ATTACKER_KEY_{dev_idx:04d}"

        puf = PUFSimulator(device_key, build_realistic_puf_config())
        attacker = PUFSimulator(attacker_key, build_realistic_puf_config())

        genuine_hds = []
        impostor_hds = []

        for sess_idx in range(cfg.sessions_per_device):
            challenge = generate_challenge(seed=f"dev{dev_idx}_sess{sess_idx}")

            ideal, noisy = puf.generate_response(challenge, add_noise=True)
            genuine_hds.append(puf.get_hamming_distance(noisy, ideal))

            _, fake = attacker.generate_response(challenge, add_noise=True)
            impostor_hds.append(puf.get_hamming_distance(fake, ideal))

        metrics = compute_eer(genuine_hds, impostor_hds)
        device_eers.append(metrics["eer"])
        threshold_votes.append(metrics["threshold"])

        per_device_rows.append(
            {
                "device_id": dev_idx,
                "eer": round(metrics["eer"], 6),
                "eer_threshold": metrics["threshold"],
                "far_at_eer": round(metrics["far"], 6),
                "frr_at_eer": round(metrics["frr"], 6),
                "genuine_hd_mean": round(statistics.mean(genuine_hds), 3),
                "impostor_hd_mean": round(statistics.mean(impostor_hds), 3),
            }
        )

    ci = bootstrap_ci(device_eers, cfg.bootstrap_rounds, cfg.random_seed + 17)
    summary = {
        "config": {
            "num_devices": cfg.num_devices,
            "sessions_per_device": cfg.sessions_per_device,
            "bootstrap_rounds": cfg.bootstrap_rounds,
            "random_seed": cfg.random_seed,
            "realistic_profile": get_realistic_puf_profile(),
        },
        "eer_distribution": ci,
        "recommended_threshold_median": int(statistics.median(threshold_votes)),
        "recommended_threshold_mode": int(statistics.mode(threshold_votes)),
        "devices": per_device_rows,
    }
    return summary


def write_outputs(summary: Dict) -> None:
    ARTIFACT_DIR.mkdir(exist_ok=True)

    with DEVICE_CSV.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "device_id",
            "eer",
            "eer_threshold",
            "far_at_eer",
            "frr_at_eer",
            "genuine_hd_mean",
            "impostor_hd_mean",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary["devices"]:
            writer.writerow(row)

    with SUMMARY_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    cfg = StressConfig()
    report = run_stress(cfg)
    write_outputs(report)

    ci = report["eer_distribution"]
    print("=" * 72)
    print("Multi-device EER Stress Test Completed")
    print("=" * 72)
    print(f"Devices: {report['config']['num_devices']}")
    print(f"Sessions per device: {report['config']['sessions_per_device']}")
    print(f"Mean EER: {ci['mean']:.6f}")
    print(f"95% CI: [{ci['ci95_low']:.6f}, {ci['ci95_high']:.6f}]")
    print(f"Recommended threshold (median): {report['recommended_threshold_median']}")
    print(f"Output JSON: {SUMMARY_JSON}")
    print(f"Output CSV:  {DEVICE_CSV}")
