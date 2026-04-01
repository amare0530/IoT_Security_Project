"""
HD distribution diagnostic and red-team reliability checks.

Outputs:
- Genuine / Impostor distribution stats
- Skewness and kurtosis (fat-tail check)
- Overlap zone
- Threshold suggestions:
    - T_normal = mu + 3*sigma
    - T_empirical: minimal threshold with sample FRR < 1%
    - T_robust_10k: minimal threshold where 95% Wilson upper bound of FRR <= 1%
- Security margin checks (P[HD<=T], 2^-40)
- Aging stress scenario (unstable_ratio escalation)
- Effective security under known bias-bit leakage
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path

from puf_simulator import PUFConfig, PUFSimulator, generate_challenge

ARTIFACTS_DIR = Path("artifacts")
SUMMARY_JSON = ARTIFACTS_DIR / "hd_distribution_summary.json"
DETAIL_CSV = ARTIFACTS_DIR / "hd_distribution_samples.csv"
HISTOGRAM_PNG = ARTIFACTS_DIR / "hd_distribution_hist.png"


def _moment_stats(values: list[int]) -> dict:
    """Return mean/std/skewness/excess kurtosis using population moments."""
    n = len(values)
    mu = statistics.mean(values)
    m2 = sum((x - mu) ** 2 for x in values) / n
    sigma = math.sqrt(m2)
    if sigma == 0:
        return {
            "mean": mu,
            "std": 0.0,
            "skewness": 0.0,
            "excess_kurtosis": -3.0,
        }
    m3 = sum((x - mu) ** 3 for x in values) / n
    m4 = sum((x - mu) ** 4 for x in values) / n
    skewness = m3 / (sigma ** 3)
    excess_kurtosis = (m4 / (sigma ** 4)) - 3.0
    return {
        "mean": mu,
        "std": sigma,
        "skewness": skewness,
        "excess_kurtosis": excess_kurtosis,
    }


def wilson_upper_bound(k_fail: int, n: int, confidence_z: float = 1.96) -> float:
    """Wilson score upper bound for binomial proportion."""
    if n <= 0:
        return 1.0
    p_hat = k_fail / n
    z2 = confidence_z ** 2
    denom = 1.0 + z2 / n
    center = p_hat + z2 / (2.0 * n)
    radius = confidence_z * math.sqrt((p_hat * (1.0 - p_hat) / n) + (z2 / (4.0 * n * n)))
    return (center + radius) / denom


def binomial_cdf_hd_leq(threshold: int, n_bits: int = 256) -> float:
    """P(HD <= threshold) where HD ~ Binomial(n_bits, 0.5)."""
    t = max(0, min(threshold, n_bits))
    return sum(math.comb(n_bits, k) for k in range(t + 1)) / (2 ** n_bits)


def overlap_zone(values_a: list[int], values_b: list[int]) -> tuple[int | None, int | None]:
    lo = max(min(values_a), min(values_b))
    hi = min(max(values_a), max(values_b))
    if lo <= hi:
        return lo, hi
    return None, None


def collect_distributions(samples: int, seed: int, cfg: PUFConfig | None = None) -> tuple[list[int], list[int]]:
    random.seed(seed)

    cfg = cfg or PUFConfig()
    genuine_puf = PUFSimulator("GENUINE_DEVICE_KEY_001", cfg)
    impostor_puf = PUFSimulator("IMPOSTOR_DEVICE_KEY_999", cfg)

    genuine_hd: list[int] = []
    impostor_hd: list[int] = []

    for i in range(samples):
        challenge = generate_challenge(seed=f"hd_dist_{i}_{seed}")

        ideal_response, noisy_response = genuine_puf.generate_response(challenge, add_noise=True)
        genuine_hd.append(genuine_puf.get_hamming_distance(ideal_response, noisy_response))

        _, impostor_response = impostor_puf.generate_response(challenge, add_noise=True)
        impostor_hd.append(genuine_puf.get_hamming_distance(ideal_response, impostor_response))

    return genuine_hd, impostor_hd


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Genuine/Impostor HD distributions")
    parser.add_argument("--samples", type=int, default=500, help="Number of genuine and impostor samples")
    parser.add_argument("--seed", type=int, default=20260401, help="Random seed for reproducibility")
    parser.add_argument("--fixed-threshold", type=int, default=38, help="Fixed threshold for stress check")
    parser.add_argument("--known-bias-ratio", type=float, default=0.15, help="Attacker-known bias-bit ratio")
    parser.add_argument("--aging-unstable-ratio", type=float, default=0.20, help="Aging scenario unstable_ratio")
    parser.add_argument("--plot", action="store_true", help="Save histogram PNG plot")
    args = parser.parse_args()

    base_cfg = PUFConfig()
    genuine_hd, impostor_hd = collect_distributions(args.samples, args.seed, cfg=base_cfg)

    g_m = _moment_stats(genuine_hd)
    i_m = _moment_stats(impostor_hd)
    mu_g = g_m["mean"]
    sigma_g = g_m["std"]
    mu_i = i_m["mean"]
    sigma_i = i_m["std"]

    t_normal = int(round(mu_g + 3.0 * sigma_g))
    t_normal = max(0, min(t_normal, 256))

    frr_normal = sum(1 for x in genuine_hd if x > t_normal) / len(genuine_hd)
    far_normal = sum(1 for x in impostor_hd if x <= t_normal) / len(impostor_hd)

    # Empirical threshold: smallest T with sample FRR < 1%
    t_empirical = None
    frr_empirical = None
    far_empirical = None
    for t in range(257):
        t_frr = sum(1 for x in genuine_hd if x > t) / len(genuine_hd)
        if t_frr < 0.01:
            t_empirical = t
            frr_empirical = t_frr
            far_empirical = sum(1 for x in impostor_hd if x <= t) / len(impostor_hd)
            break

    # Robust threshold for 10k-scale target: Wilson upper bound (95%) <= 1%
    t_robust = None
    frr_robust = None
    frr_robust_upper95 = None
    far_robust = None
    n_g = len(genuine_hd)
    for t in range(257):
        k_fail = sum(1 for x in genuine_hd if x > t)
        ub = wilson_upper_bound(k_fail, n_g, confidence_z=1.96)
        if ub <= 0.01:
            t_robust = t
            frr_robust = k_fail / n_g
            frr_robust_upper95 = ub
            far_robust = sum(1 for x in impostor_hd if x <= t) / len(impostor_hd)
            break

    ov_lo, ov_hi = overlap_zone(genuine_hd, impostor_hd)

    p_bf = binomial_cdf_hd_leq(t_normal, n_bits=256)
    secure_limit = 2 ** -40
    security_ok = p_bf <= secure_limit

    if not security_ok:
        security_note = "此環境雜訊過大，無法在保證安全的狀況下提供可用性"
    else:
        security_note = "安全邊際通過：P[HD<=T] <= 2^-40"

    empirical_security = None
    if t_empirical is not None:
        p_bf_practical = binomial_cdf_hd_leq(t_empirical, n_bits=256)
        empirical_security = {
            "threshold": t_empirical,
            "frr": frr_empirical,
            "far": far_empirical,
            "p_hd_leq_t": p_bf_practical,
            "log2_p_hd_leq_t": math.log2(p_bf_practical) if p_bf_practical > 0 else float("-inf"),
            "pass_2_minus_40": p_bf_practical <= secure_limit,
        }

    # Aging stress: increase unstable_ratio and check FRR/FAR at fixed threshold.
    aging_cfg = PUFConfig(
        response_bits=base_cfg.response_bits,
        noise_sigma=base_cfg.noise_sigma,
        use_hamming74_ecc=base_cfg.use_hamming74_ecc,
        use_ecc_interleaving=base_cfg.use_ecc_interleaving,
        ecc_interleaving_depth=base_cfg.ecc_interleaving_depth,
        cluster_noise_prob=base_cfg.cluster_noise_prob,
        cluster_size=base_cfg.cluster_size,
        bias_ratio=base_cfg.bias_ratio,
        unstable_ratio=args.aging_unstable_ratio,
        bias_strength=base_cfg.bias_strength,
        unstable_extra_noise=base_cfg.unstable_extra_noise,
        env_noise_sigma=base_cfg.env_noise_sigma,
        env_spike_prob=base_cfg.env_spike_prob,
        env_spike_min=base_cfg.env_spike_min,
        env_spike_max=base_cfg.env_spike_max,
    )
    g_aging, i_aging = collect_distributions(args.samples, args.seed + 1, cfg=aging_cfg)
    frr_aging_fixed = sum(1 for x in g_aging if x > args.fixed_threshold) / len(g_aging)
    far_aging_fixed = sum(1 for x in i_aging if x <= args.fixed_threshold) / len(i_aging)

    # Effective security bits if attacker knows some biased-bit positions.
    known_ratio = max(0.0, min(args.known_bias_ratio, 0.95))
    effective_bits = int(round(256 * (1.0 - known_ratio)))
    p_bf_effective = binomial_cdf_hd_leq(args.fixed_threshold, n_bits=effective_bits)
    effective_security_bits = -math.log2(p_bf_effective) if p_bf_effective > 0 else float("inf")

    # Optional plot for report.
    plot_saved = None
    if args.plot:
        try:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(8, 4.8))
            bins = list(range(0, 257, 2))
            plt.hist(genuine_hd, bins=bins, alpha=0.60, label="Genuine HD", density=True)
            plt.hist(impostor_hd, bins=bins, alpha=0.60, label="Impostor HD", density=True)
            plt.axvline(t_normal, color="black", linestyle="--", linewidth=1.2, label=f"T_normal={t_normal}")
            if t_empirical is not None:
                plt.axvline(t_empirical, color="green", linestyle=":", linewidth=1.3, label=f"T_empirical={t_empirical}")
            plt.axvline(args.fixed_threshold, color="red", linestyle="-.", linewidth=1.1, label=f"T_fixed={args.fixed_threshold}")
            plt.xlabel("Hamming Distance")
            plt.ylabel("Density")
            plt.title("Genuine vs Impostor HD Distributions")
            plt.legend()
            plt.tight_layout()
            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            plt.savefig(HISTOGRAM_PNG, dpi=170)
            plt.close()
            plot_saved = str(HISTOGRAM_PNG)
        except Exception as e:
            plot_saved = f"plot_failed: {e}"

    summary = {
        "samples_per_group": args.samples,
        "seed": args.seed,
        "genuine": {
            "mean_hd": mu_g,
            "std_hd": sigma_g,
            "skewness": g_m["skewness"],
            "excess_kurtosis": g_m["excess_kurtosis"],
            "min_hd": min(genuine_hd),
            "max_hd": max(genuine_hd),
        },
        "impostor": {
            "mean_hd": mu_i,
            "std_hd": sigma_i,
            "skewness": i_m["skewness"],
            "excess_kurtosis": i_m["excess_kurtosis"],
            "min_hd": min(impostor_hd),
            "max_hd": max(impostor_hd),
        },
        "overlap_zone": {
            "low": ov_lo,
            "high": ov_hi,
            "has_overlap": ov_lo is not None,
        },
        "recommended_threshold_normal_assumption": {
            "formula": "T = mu_genuine + 3 * sigma_genuine",
            "value": t_normal,
            "frr": frr_normal,
            "far": far_normal,
        },
        "empirical_threshold_for_frr_lt_1pct": empirical_security,
        "robust_threshold_for_10k_frr_target": {
            "threshold": t_robust,
            "frr": frr_robust,
            "frr_upper95": frr_robust_upper95,
            "far": far_robust,
            "target": "FRR_upper95 <= 1%",
        },
        "aging_stress_fixed_threshold": {
            "fixed_threshold": args.fixed_threshold,
            "baseline_unstable_ratio": base_cfg.unstable_ratio,
            "aging_unstable_ratio": args.aging_unstable_ratio,
            "frr_baseline": sum(1 for x in genuine_hd if x > args.fixed_threshold) / len(genuine_hd),
            "far_baseline": sum(1 for x in impostor_hd if x <= args.fixed_threshold) / len(impostor_hd),
            "frr_aging": frr_aging_fixed,
            "far_aging": far_aging_fixed,
        },
        "effective_security_under_known_bias": {
            "known_bias_ratio": known_ratio,
            "effective_bits": effective_bits,
            "fixed_threshold": args.fixed_threshold,
            "p_hd_leq_t": p_bf_effective,
            "log2_p_hd_leq_t": math.log2(p_bf_effective) if p_bf_effective > 0 else float("-inf"),
            "effective_security_bits": effective_security_bits,
            "pass_2_minus_40": p_bf_effective <= secure_limit,
        },
        "security_margin": {
            "p_hd_leq_t": p_bf,
            "log2_p_hd_leq_t": math.log2(p_bf) if p_bf > 0 else float("-inf"),
            "target": "2^-40",
            "pass": security_ok,
            "note": security_note,
        },
        "plot": {
            "requested": args.plot,
            "saved": plot_saved,
        },
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with SUMMARY_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with DETAIL_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "hd"])
        for hd in genuine_hd:
            writer.writerow(["genuine", hd])
        for hd in impostor_hd:
            writer.writerow(["impostor", hd])

    print("HD Distribution Analysis")
    print("=" * 60)
    print(f"Samples/group: {args.samples}")
    print(
        f"Genuine   : mu={mu_g:.2f}, sigma={sigma_g:.2f}, "
        f"skew={g_m['skewness']:.3f}, kurt={g_m['excess_kurtosis']:.3f}, "
        f"range=[{min(genuine_hd)}, {max(genuine_hd)}]"
    )
    print(
        f"Impostor  : mu={mu_i:.2f}, sigma={sigma_i:.2f}, "
        f"skew={i_m['skewness']:.3f}, kurt={i_m['excess_kurtosis']:.3f}, "
        f"range=[{min(impostor_hd)}, {max(impostor_hd)}]"
    )
    if ov_lo is None:
        print("Overlap   : none")
    else:
        print(f"Overlap   : [{ov_lo}, {ov_hi}]")
    print(f"T_normal  : T={t_normal} (mu+3sigma), FRR={frr_normal:.4f}, FAR={far_normal:.4f}")
    if t_empirical is not None:
        print(
            f"T_emp     : T={t_empirical} (sample FRR<1%), FRR={frr_empirical:.4f}, FAR={far_empirical:.4f}"
        )
    else:
        print("T_emp     : not found in [0, 256]")
    if t_robust is not None:
        print(
            f"T_robust  : T={t_robust}, FRR={frr_robust:.4f}, FRR_upper95={frr_robust_upper95:.4f}, FAR={far_robust:.4f}"
        )
    else:
        print("T_robust  : not found (needs more data or lower noise)")
    print(f"P[HD<=Tn] : {p_bf:.6e} (log2={math.log2(p_bf):.2f})")
    print(f"Security  : {security_note}")
    print(
        f"Aging@T={args.fixed_threshold}: unstable_ratio {base_cfg.unstable_ratio:.2f}->{args.aging_unstable_ratio:.2f}, "
        f"FRR {summary['aging_stress_fixed_threshold']['frr_baseline']:.4f}->{frr_aging_fixed:.4f}, "
        f"FAR {summary['aging_stress_fixed_threshold']['far_baseline']:.4f}->{far_aging_fixed:.4f}"
    )
    print(
        f"Known-bias({known_ratio:.0%}) effective bits: {effective_bits}, "
        f"security_bits={effective_security_bits:.2f}"
    )
    if plot_saved:
        print(f"Plot      : {plot_saved}")
    print(f"Saved     : {SUMMARY_JSON}")
    print(f"Saved     : {DETAIL_CSV}")


if __name__ == "__main__":
    main()
