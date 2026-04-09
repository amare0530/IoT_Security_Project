# Next Sprint Plan (2026-04-09)

## Objective
Complete thesis-aligned quantitative evidence and finalize advisor presentation package.

## Scope Guardrails
1. Keep the project positioned as a research prototype (not production deployment).
2. Prioritize real-data workflow and baseline comparability over feature expansion.
3. Avoid new cryptographic claims; focus on measurable system-level validation.

## Work Items

### 1) Quantitative Figures (Must Deliver)
1. ROC + EER plot from current FAR/FRR threshold scan.
2. Intra-HD vs Inter-HD distribution chart (real-data focused).
3. Authentication latency breakdown chart:
   - Network round trip
   - HMAC compute
   - Database query
   - HD comparison

### 2) Baseline Comparison Completion
1. Freeze final baseline set:
   - Vinagrero et al. (data baseline)
   - pypuf (tool baseline)
   - Modeling attack / LP-PUF (research baseline)
2. Fill comparison table with available quantitative values.
3. Mark non-comparable rows explicitly as "different setup".

### 3) Real-Data Path Verification
1. Verify dataset-first path end-to-end:
   - `app.py` sends target metadata
   - `mqtt_bridge.py` forwards metadata
   - `node.py` retrieves deterministic matching row
2. Run one reproducible script sequence and save artifacts.

### 4) Advisor Demo Package
1. One-page architecture summary.
2. One-page baseline comparison summary.
3. One-page risk/limitation statement.

## Suggested Execution Order
1. Generate three charts.
2. Populate baseline table with current measured values.
3. Validate dataset-first path and export logs.
4. Assemble final advisor slides/markdown package.

## Exit Criteria
1. Three charts exist under `artifacts/`.
2. `PAPER_BASELINE_COMPARISON_2026-04-07.md` has complete comparison rows.
3. `ADVISOR_BRIEF_2026-04-07.md` includes final numeric highlights.
4. No document claims production readiness.
