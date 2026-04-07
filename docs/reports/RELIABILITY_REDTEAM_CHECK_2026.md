# Reliability Red-Team Check (2026-04-01)

This report validates the threshold calibration with a reliability-first mindset.
It focuses on worst-case risk rather than average-case success.

## 1) Data and Method

- Script: analyze_hd_distribution.py
- Sample size: 500 Genuine + 500 Impostor
- Baseline threshold candidate: T=38
- Additional checks:
  - Distribution shape (skewness, excess kurtosis)
  - Robust FRR<1% threshold under 95% confidence (Wilson upper bound)
  - Aging stress with unstable_ratio: 0.08 -> 0.20
  - Effective security when attacker knows 15% bias-bit positions

## 2) Key Results

### 2.1 Distribution Shape (Normality Risk)

- Genuine: mu=15.27, sigma=6.14, skewness=1.472, excess kurtosis=5.137
- Impostor: mu=128.56, sigma=7.48, skewness=0.005, excess kurtosis=-0.149
- Overlap zone: none

Interpretation:
- Genuine distribution is right-skewed and heavy-tailed.
- Therefore, strict normal assumption (mu + 3sigma) can under-estimate tail risk.

### 2.2 Threshold Comparison

- T_normal = 34 (mu + 3sigma)
  - FRR=1.20%, FAR=0.00%
- T_empirical = 38 (minimum threshold with sample FRR<1%)
  - FRR=0.80%, FAR=0.00%
- T_robust_10k = 55 (95% Wilson upper bound target: FRR <= 1%)
  - FRR=0.00%, FRR_upper95=0.76%, FAR=0.00%

Interpretation:
- T=38 is good in sample.
- For conservative thesis claims at larger deployment scale, T=55 is statistically safer.

### 2.3 Aging Stress (Corner Case)

At fixed threshold T=38:
- Baseline unstable_ratio=0.08: FRR=0.80%, FAR=0.00%
- Aging unstable_ratio=0.20: FRR=2.20%, FAR=0.00%

Interpretation:
- T=38 degrades under aging-like instability.
- Reliability remains usable but no longer meets FRR<1% target.

### 2.4 Security Margin Under Known Bias Bits

Assume attacker knows 15% bias-bit positions:
- Effective bits = 218
- At T=38: effective security bits = 75.97
- Still stronger than 2^-40 requirement

Interpretation:
- Security decreases from idealized setting, but remains above project target.
- This should be reported as a conditional claim in thesis limitations.

## 3) Required Thesis Wording (Recommended)

Use this claim format:

1. The calibrated threshold T=38 achieves FRR<1% in current baseline sampling.
2. Genuine HD is heavy-tailed; therefore, robust reliability claims should use confidence-bounded thresholds.
3. Under aging-like instability (unstable_ratio=0.20), FRR increases to 2.2% at T=38.
4. If 15% bias-bit positions are leaked, effective security remains above 2^-40 in current setting.

## 4) Artifacts

- Summary JSON: artifacts/hd_distribution_summary.json
- Raw samples: artifacts/hd_distribution_samples.csv
- Distribution figure: artifacts/hd_distribution_hist.png


