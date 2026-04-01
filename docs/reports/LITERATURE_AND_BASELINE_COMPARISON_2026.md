# Literature + GitHub Baseline Comparison (2026)

This note is written for thesis defense and red-team style review.
It focuses on two questions:

1. Are there recent, citable papers supporting your threat model?
2. Compared with real public implementations, what is your system's measurable advantage?

## 1) Recent papers (not old)

All items below were checked with DOI metadata and publication year.

1. Helper Data Masking for Physically Unclonable Function-Based Key Generation Algorithms
- Year: 2022
- Venue: IEEE Access
- DOI: 10.1109/ACCESS.2022.3165284
- Why relevant:
	- Directly addresses helper data leakage/manipulation risk.
	- Good reference for your helper-integrity defense argument.

2. A New Helper Data Scheme for Soft-Decision Decoding of Binary Physical Unclonable Functions
- Year: 2022
- Venue: IEEE Access
- DOI: 10.1109/ACCESS.2022.3146989
- Why relevant:
	- Discusses helper data design under noisy conditions.
	- Useful baseline against your Hamming(7,4)+interleaving path.

3. A quantum-safe authentication scheme for IoT devices using homomorphic encryption and weak physical unclonable functions with no helper data
- Year: 2024
- Venue: Internet of Things (Elsevier)
- DOI: 10.1016/J.IOT.2024.101389
- Why relevant:
	- A strong comparison point because it explicitly avoids helper data.
	- Good for discussing trade-off: cryptographic overhead vs lightweight implementation.

4. Helper Data Schemes for Coded Modulation and Shaping in Physical Unclonable Functions
- Year: 2025
- Venue: IEEE Open Journal of the Communications Society
- DOI: 10.1109/OJCOMS.2025.3615964
- Why relevant:
	- Very recent helper-data theory update.
	- Supports your claim that helper design remains an active, unsolved area.

5. Machine Learning of Physical Unclonable Functions using Helper Data
- Year: 2021
- Venue: IACR TCHES
- DOI: 10.46586/TCHES.V2021.I2.1-36
- Why relevant:
	- Core attack paper: helper data can assist modeling attacks.
	- Supports your need for integrity + privacy amplification + adversarial testing.

## 2) Real GitHub baseline groups

These repos are public and accessible. They are not all identical in objective, but each is a valid control group for one dimension.

1. https://github.com/BrahiM-Mefgouda/LPUF-AuthNet
- Focus: ML-based PUF authentication (TNN + split learning)
- Useful as control for:
	- ML-resistant claims
	- Model attack experiment setup

2. https://github.com/karanahujax/PUF
- Focus: Fuzzy extractor style key generation with helper data
- Useful as control for:
	- Classical FE pipeline structure
	- Helper-data-dependent reconstruction baseline

3. https://github.com/TechnologyAiGroup/pufC2D2
- Focus: Strong-PUF modeling attacks and CRP analysis
- Useful as control for:
	- Red-team/attacker capability baseline
	- Security analysis beyond simple FAR/FRR

4. https://github.com/IFM-Ulm/ro-pr-fw
- Focus: FPGA RO-PUF measurement framework with real hardware data collection
- Useful as control for:
	- Real measurement procedure and non-ideal noise behavior
	- Hardware-level reproducibility standards

## 3) Your system vs papers/repositories: technical differences

### A. Helper data security path

- Typical baseline:
	- Helper data used for reliability, but integrity is not always first-class in code path.
- Your current design:
	- Helper record binds `(challenge, helper_hex)` with HMAC tag.
	- Verification uses constant-time compare.
	- Tampered helper causes explicit authentication reject.
- Practical advantage:
	- Better resistance against helper-data manipulation attack at implementation layer.

### B. Entropy handling

- Typical baseline:
	- Decision often based on raw/corrected bit distance only.
- Your current design:
	- Adds privacy amplification (SHA-256 squeeze) after correction.
	- Keeps `raw_hd` and `pa_hd` for analysis.
- Practical advantage:
	- Clear separation between reliability metric and post-extraction key metric.

### C. Realistic noise model

- Typical baseline:
	- IID random bit flips dominate simulation.
- Your current design:
	- Includes bias bits, unstable bits, environmental spikes, and optional cluster noise.
	- Supports ECC interleaving for burst robustness tests.
- Practical advantage:
	- Better alignment with silicon behavior under voltage/temperature drift.

### D. Replay and protocol layer

- Typical baseline:
	- PUF response matching only, weak session freshness.
- Your current design:
	- Nonce cache + timestamp window in session verification.
	- Rejects replay explicitly and records reason.
- Practical advantage:
	- Stronger end-to-end protocol realism for IoT deployment narrative.

## 4) Honest gaps (must state in thesis)

1. HMAC key lifecycle is not yet production-grade.
- Need rotation policy, secure storage (HSM/TPM/secure enclave), and compromise handling.

2. Privacy amplification gate policy is not fully calibrated across devices.
- Need cross-device confidence intervals and threshold sweep under realistic stress.

3. Real hardware calibration data is still limited.
- Must include at least one public or measured board-level dataset comparison in final chapter.

## 5) Suggested defense narrative (short)

Use this 3-layer statement in oral defense:

1. Reliability layer: Hamming + optional interleaving handles stochastic and burst errors.
2. Integrity layer: helper data is authenticated (HMAC) before reconstruction.
3. Entropy layer: corrected response is privacy-amplified before final security decision.

This prevents mixing reliability claims and security claims into one weak metric.

## 6) Chapter-ready experiment protocol (for thesis writing)

Use this section directly in your "Baseline and Evaluation" chapter.

### 6.1 Evaluation objective

We compare three aspects across baselines and this project:

1. Reliability under non-IID noise (burst + unstable bits + environment spikes)
2. Integrity of helper-data path under active tampering
3. Protocol-level replay resistance in session authentication

### 6.2 Baseline grouping strategy

Not all repositories implement the same full stack, so we compare by capability domain:

1. FE/helper-data baseline:
- Repo: `karanahujax/PUF`
- Capability: reconstruction pipeline and helper-data dependence

2. Modeling attack baseline:
- Repo: `TechnologyAiGroup/pufC2D2`
- Capability: attacker perspective and CRP-driven model risk

3. ML-auth baseline:
- Repo: `BrahiM-Mefgouda/LPUF-AuthNet`
- Capability: data-driven authentication behavior and generalization risk

4. Hardware-measurement baseline:
- Repo: `IFM-Ulm/ro-pr-fw`
- Capability: non-ideal hardware capture workflow and reproducibility discipline

### 6.3 Metrics to report (minimum set)

1. Device-level EER distribution (mean, std, 95% CI)
2. FAR/FRR at selected operation threshold
3. Helper-data tamper rejection rate
4. Replay attack rejection rate
5. Burst-noise degradation slope (cluster size vs auth failure)

### 6.4 Reproducible script path in this repo

1. Multi-device EER stress test:
- `multi_device_eer_stress.py`
- Outputs:
	- `artifacts/multi_device_eer_summary.json`
	- `artifacts/multi_device_eer_by_device.csv`

2. Full system sanity verification:
- `verify_all_phases.py`

3. Anti-replay regression test:
- `test_phase2_antireplay.py`

### 6.5 Required threat statements (do not omit in thesis)

1. Helper data is public by design, so integrity must be cryptographically protected.
2. ECC improves reliability but does not automatically preserve entropy.
3. Nonce/timestamp logic protects protocol freshness, not PUF modeling attacks.

### 6.6 Why your system is stronger than a typical student baseline

1. It separates reliability, integrity, and entropy stages explicitly in code.
2. It provides adversarial outcomes (`tampered`, `replay`, `expired`) instead of only pass/fail.
3. It evaluates realistic noise with cross-device confidence intervals instead of one-device ideal simulation.
