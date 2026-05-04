# Experiment Workflow (Conference-Ready)

## E1: Intra-Device Reliability

**Goal:** quantify noise for repeated startups of the same device.

- Input: same UID, multiple captures.
- Metric: average normalized Hamming distance across repeated samples.
- Expected: low HD means stable PUF; high HD means noisy response.

## E2: Inter-Device Uniqueness

**Goal:** verify different devices are distinguishable.

- Input: one reference response per UID (or averaged prototype).
- Metric: inter-device normalized HD.
- Expected: near 50% for ideal uniqueness.

## E3: Bit Selection Effectiveness

**Goal:** show reliability-aware mask improves BER and reconstruction.

- Compare thresholds: 0.90 / 0.95 / 0.98 / 0.99
- Metrics:
  - BER before/after mask
  - key reconstruction success rate
- Deliverable table:

| Threshold | Selected Bits | BER | Reconstruction Success |
|-----------|---------------|-----|------------------------|
| 0.90      | ...           | ... | ...                    |
| 0.95      | ...           | ... | ...                    |
| 0.98      | ...           | ... | ...                    |
| 0.99      | ...           | ... | ...                    |

## E4: Authentication Performance

**Goal:** validate lightweight runtime overhead.

- Scenario: challenge-response with HMAC-SHA256.
- Metrics:
  - end-to-end latency (ms)
  - auth success/failure rate
  - CPU utilization (optional)

## Statistical Reporting Suggestions

- Report mean ± std (or median + IQR) over repeated runs.
- Include confidence intervals for BER and success rate.
- Fix random seeds where simulation is used.

## Plot Checklist

1. Intra/inter HD distributions (boxplot or violin)
2. BER vs threshold
3. Reconstruction success vs threshold
4. Authentication latency CDF
