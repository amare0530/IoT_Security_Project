# Reviewer #2 Red-Team Review (PUF + AuthenticationEngine)

This document records adversarial findings and concrete fixes for the current codebase.
The goal is not praise. The goal is to reduce hidden risk before thesis defense.

## Scope

- `puf_simulator.py`
- `AuthenticationEngine`
- Helper Data enrollment and reconstruction path
- ECC path under clustered noise conditions

## Findings (Ordered by Severity)

1. Critical: Helper Data could be modified without detection.
- Risk:
  - If an attacker changes helper bits, decoder behavior can be redirected.
  - This can force wrong reconstruction and either increase FRR or open targeted false-accept windows.
- Evidence:
  - Previous flow trusted stored helper bits directly.
- Fix applied:
  - Added HMAC integrity tag for helper data (`helper_tag`) bound to `(challenge, helper_hex)`.
  - Added constant-time verification via `hmac.compare_digest`.
  - Authentication now fails with `Auth Failed (Helper Data Tampered)` when verification fails.

2. High: Authentication depended only on raw corrected bits.
- Risk:
  - Post-ECC bit distribution may remain biased/correlated.
  - Effective key space can be lower than nominal 256-bit representation.
- Fix applied:
  - Added privacy amplification stage with SHA-256 over corrected response.
  - Added constant-time digest comparison when `privacy_threshold == 0`.
  - Exposes `pa_hd` and `raw_hd` separately for analysis.

3. Medium: Burst errors can defeat independent-noise assumptions.
- Risk:
  - Hamming(7,4) is single-error-correcting. Adjacent bursts can break multiple local codewords.
- Fix applied:
  - Added optional ECC bit interleaving (`use_ecc_interleaving`, `ecc_interleaving_depth`).
  - Interleaving spreads local bursts across different correction regions.

4. Medium: Timing side-channel concern in equality checks.
- Risk:
  - Non constant-time comparisons can leak progressive mismatch information.
- Fix applied:
  - Sensitive digest comparisons now use `hmac.compare_digest`.

## Model Critique (What still needs experiment proof)

1. Multi-device EER under helper-data correlation is not fully proven by code inspection.
- Why:
  - Correlation is data-driven and requires cross-device Monte Carlo runs.
- Recommendation:
  - Run `N >= 100` devices, each with `M >= 1000` sessions.
  - Report FAR/FRR/EER with and without helper data, and with/without privacy amplification.
  - Plot EER confidence intervals (bootstrap) rather than single-point values.

2. IID noise model is still optimistic by default.
- Why:
  - Real silicon often exhibits spatially clustered failures under thermal/voltage stress.
- Recommendation:
  - Keep `cluster_noise_prob > 0` in stress campaigns.
  - Sweep cluster size and compare degradation slope.

## Suggested Thesis Addendum

- Security argument must explicitly separate:
  - Reliability layer (ECC helper data)
  - Integrity layer (HMAC over helper data)
  - Entropy extraction layer (privacy amplification)
- Include an attacker model where helper storage is publicly readable and writable.
- Include residual risk statement for key management:
  - `helper_integrity_key` lifecycle, rotation, and storage policy.

## Quick Reproduction Checklist

- Enable helper integrity and privacy amplification in `AuthenticationEngine`.
- Enable `use_hamming74_ecc=True` and `use_ecc_interleaving=True` in `PUFConfig`.
- Run realistic and extreme tests, then compare:
  - `raw_hd`
  - `pa_hd`
  - Replay rejection rate
  - Tamper rejection rate
