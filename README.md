# Reliability-Aware Bit Selection for Lightweight SRAM-PUF Authentication in IoT Devices

## Chinese Title
基於位元穩定度分析之輕量化 SRAM-PUF IoT 裝置認證系統

## Core Objective
Address SRAM-PUF environmental noise by using reliability-aware bit selection to improve key reconstruction success rate without increasing computational burden.

## Recommended Implementation Sequence
1. PUF Dataset Analysis
2. Bit Stability Selection
3. Fuzzy Extractor
4. HMAC Authentication
5. MQTT Communication
6. System Integration
7. Experiment Evaluation

## Repository Structure
- `data/`: input dataset (put `crps.csv` here)
- `analysis/`: dataset analysis and mask generation
- `puf/`: bit selection and fuzzy extractor modules
- `auth/`: HMAC authentication utilities
- `mqtt/`: demo device/server over MQTT
- `experiments/`: evaluation scripts and plots
- `artifacts/`: generated outputs (created at runtime)

## Step 1: Run Stability Analysis
Expected CSV columns:
- `uid`
- `address`
- `data` (decimal byte 0-255)
- `created_at`

Run:

```powershell
python analysis/stability_analysis.py --input data/crps.csv --output-dir artifacts --thresholds 0.90 0.95 0.98 0.99
```

Outputs:
- `artifacts/stability_summary.csv`
- `artifacts/masks.json`
- `artifacts/threshold_comparison.csv`

## Next Step
Use `artifacts/masks.json` as the core input for fuzzy extractor and authentication experiments.

## Reproducible collaboration workflow

- Keep `data/*.csv` and full `artifacts/*.csv` / `*.json` on the desktop. They
  are intentionally ignored and must never be committed.
- Run the public, deterministic demo on any laptop without the private dataset:

  ```powershell
  python scripts/run_offline_demo.py --output-dir demo-output
  pytest -q
  ```

- Run a desktop analysis only into a new directory, for example
  `runs/2026-09-22-full`; never overwrite historical `artifacts/` evidence.
- See `docs/DATA_SETUP.md` for data boundaries and `docs/DEMO_GUIDE.md` for the
  exhibition workflow. This repository is a dataset-based system-level prototype,
  not a completed live microcontroller SRAM implementation.

The MQTT device demo reconstructs its key with `Rep()` for each challenge and
uses it immediately for HMAC. It best-effort clears its local `bytearray`
buffer afterward. Python cannot guarantee that all immutable `bytes` copies
have been overwritten; a true memory-clearing guarantee requires an MCU
implementation in C. The unauthenticated `iot/auth/result` topic is
informational only and never controls device behavior.

## Paper-Ready Docs
- Architecture: `docs/ARCHITECTURE_PAPER_STYLE.md`
- Experiment flow: `docs/EXPERIMENT_FLOW.md`
