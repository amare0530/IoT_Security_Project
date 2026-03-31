# IoT Security Project

PUF-based device authentication prototype for IoT.

這個專案的目標很直接：
- 用 PUF 行為模擬設備指紋
- 用 Hamming Distance 做容錯認證
- 用 Nonce + Timestamp 防重放
- 用批次測試量化 FAR / FRR / EER

目前是「可重現實驗」導向，不是成品服務。

## Why This Repo Exists

大部分專題只做到「可以跑」。
這個 repo 想回答的是：
1. 在噪聲存在下，認證還能不能穩定？
2. 閾值怎麼選，才不會只追求漂亮 EER？
3. 防重放機制和 PUF 認證怎麼接在一起？

## Current Status

- Dynamic Challenge: implemented
- Session anti-replay (nonce cache): implemented
- Timestamp validity window (default 60s): implemented
- Batch metrics pipeline: implemented
- EER scanning script: implemented
- Security-first threshold discussion and audit notes: in progress

## Quick Start

### 1) Environment

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Run the three core processes

Terminal A:
```bash
python -m streamlit run app.py
```

Terminal B:
```bash
python node.py
```

Terminal C:
```bash
python mqtt_bridge.py
```

## Reproduce Core Experiments

### Batch test

```bash
python batch_test.py
```

Outputs:
- artifacts/batch_test_results.csv
- artifacts/batch_test_report.json

### ROC plot

```bash
python plot_roc.py --json artifacts/batch_test_report.json --output artifacts/roc_curve.png
```

### EER scan

```bash
python eer_scan.py
```

Output:
- artifacts/eer_analysis.txt

### Extreme environment test

```bash
python extreme_test.py
```

Output folder:
- artifacts/extreme_env_test/

## Security Notes (Important)

這個專案目前有幾個需要誠實面對的點：

1. 只看 EER 會誤導安全決策
- EER 是統計平衡，不是攻擊成本下界。

2. 閾值過高會帶來明顯風險
- 閾值需要配合 brute-force success probability 一起看。

3. ECC / Helper Data 是「可靠性工具」，不是萬能安全工具
- 如果 helper data 外洩，仍會影響有效熵。

## Repository Layout

```text
.
├─ app.py
├─ node.py
├─ mqtt_bridge.py
├─ puf_simulator.py
├─ batch_test.py
├─ plot_roc.py
├─ sensitivity_analysis.py
├─ extreme_test.py
├─ eer_scan.py
├─ calibrate_from_real_data.py
├─ test_phase2_antireplay.py
├─ test_phase2_realistic.py
├─ verify_all_phases.py
├─ artifacts/                  # generated outputs
└─ docs/
   ├─ guides/
   ├─ phases/
   ├─ reports/
   └─ checklists/
```

## Documentation Index

- docs/guides/QUICKSTART.md
- docs/guides/MQTT_FIX_GUIDE.md
- docs/phases/PHASE_2_QUICKSTART.md
- docs/reports/TECHNICAL_REPORT.md
- artifacts/README_ARCH.md
- artifacts/security_audit_report.txt

## Planned Next Steps

- Add strict security-threshold policy in scanning pipeline
- Add cluster-noise + interleaving experiments
- Upgrade helper-data path toward a more complete fuzzy extractor workflow

## License

No license file yet. If you plan to open-source formally, add one (MIT/Apache-2.0).
