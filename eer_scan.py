"""
EER 掃描工具
- 讀取 artifacts/batch_test_report.json
- 以 threshold 0..128 計算 FAR / FRR
- 找出 FAR 與 FRR 最接近的門檻 (EER 點)
- 輸出結果到 artifacts/eer_analysis.txt
"""

import json
import os
import math
from typing import List, Tuple

REPORT_PATH = os.path.join("artifacts", "batch_test_report.json")
OUTPUT_PATH = os.path.join("artifacts", "eer_analysis.txt")
SECURITY_LOG2_TARGET = -40.0
RESPONSE_BITS = 256


def load_hd_lists(report_path: str) -> Tuple[List[int], List[int]]:
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("all_records", [])
    genuine_hds = [r["hamming_distance"] for r in records if r.get("test_type") == "genuine"]
    impostor_hds = [r["hamming_distance"] for r in records if r.get("test_type") == "impostor"]

    if not genuine_hds or not impostor_hds:
        raise ValueError("report 中缺少 genuine 或 impostor 的 hamming_distance 資料")

    return genuine_hds, impostor_hds


def calc_far_frr(genuine_hds: List[int], impostor_hds: List[int], threshold: int) -> Tuple[float, float]:
    genuine_pass = sum(1 for hd in genuine_hds if hd <= threshold)
    impostor_pass = sum(1 for hd in impostor_hds if hd <= threshold)

    far = impostor_pass / len(impostor_hds)
    frr = (len(genuine_hds) - genuine_pass) / len(genuine_hds)
    return far, frr


def brute_force_success_prob(threshold: int, n_bits: int = RESPONSE_BITS) -> float:
    """P[HD <= threshold], where HD ~ Binomial(n_bits, 0.5)."""
    return sum(math.comb(n_bits, k) for k in range(threshold + 1)) / (2 ** n_bits)


def main() -> None:
    genuine_hds, impostor_hds = load_hd_lists(REPORT_PATH)

    best = None
    rows = []
    secure_rows = []

    for threshold in range(0, 129):
        far, frr = calc_far_frr(genuine_hds, impostor_hds, threshold)
        gap = abs(far - frr)
        eer = (far + frr) / 2.0
        p_bruteforce = brute_force_success_prob(threshold)
        log2_p = math.log2(p_bruteforce)
        rows.append((threshold, far, frr, eer, gap, p_bruteforce, log2_p))

        # Security-first policy: reject thresholds with weak brute-force margin.
        if log2_p <= SECURITY_LOG2_TARGET:
            secure_rows.append((threshold, far, frr, eer, gap, p_bruteforce, log2_p))

    if secure_rows:
        best = min(secure_rows, key=lambda x: x[4])
        best_threshold, far, frr, eer, gap, p_bf, log2_p = best
        policy_status = "SECURE-POLICY APPLIED"
    else:
        # Fallback for transparency when no secure threshold exists in scanned range.
        best = min(rows, key=lambda x: x[4])
        best_threshold, far, frr, eer, gap, p_bf, log2_p = best
        policy_status = "NO THRESHOLD MEETS SECURITY TARGET"


    lines = []
    lines.append("EER Analysis")
    lines.append("=" * 60)
    lines.append(f"Policy status: {policy_status}")
    lines.append(f"Security target: log2(P_bruteforce) <= {SECURITY_LOG2_TARGET}")
    lines.append(f"Samples: genuine={len(genuine_hds)}, impostor={len(impostor_hds)}")
    lines.append(f"Best secure threshold (0..128): {best_threshold}")
    lines.append(f"FAR at best threshold: {far * 100:.2f}%")
    lines.append(f"FRR at best threshold: {frr * 100:.2f}%")
    lines.append(f"EER (average of FAR/FRR): {eer * 100:.2f}%")
    lines.append(f"|FAR-FRR| gap: {gap * 100:.2f}%")
    lines.append(f"P_bruteforce at best threshold: {p_bf:.6e}")
    lines.append(f"log2(P_bruteforce): {log2_p:.2f}")
    lines.append("")
    lines.append(f"建議的安全閾值為 {best_threshold}，此時 EER 為 {eer * 100:.2f}%")
    lines.append("")
    lines.append("Top 10 secure points")
    lines.append("threshold\tFAR(%)\tFRR(%)\tEER(%)\tgap(%)\tP_bf\tlog2(P_bf)")

    ranked = sorted(secure_rows, key=lambda x: x[4]) if secure_rows else sorted(rows, key=lambda x: x[4])
    top10 = ranked[:10]
    for t, t_far, t_frr, t_eer, t_gap, t_pbf, t_log2 in top10:
        lines.append(
            f"{t}\t{t_far * 100:.2f}\t{t_frr * 100:.2f}\t{t_eer * 100:.2f}\t{t_gap * 100:.2f}\t{t_pbf:.3e}\t{t_log2:.2f}"
        )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(lines[11])
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
