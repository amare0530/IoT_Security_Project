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
