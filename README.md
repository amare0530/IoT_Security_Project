# IoT Security Project

PUF-based IoT device authentication demo project.

本專案現在是「可重現實驗 + 展示」型態，不是 production service。

## 你應該先看哪裡

如果你是 C++ 背景、Python 初學者，先看：

1. `docs/guides/CPP_TO_PYTHON_QUICKSTART.md`
2. `docs/guides/QUICKSTART.md`
3. `app.py`, `node.py`, `mqtt_bridge.py`（三個核心執行檔）

## 系統架構（一句話版）

- `app.py`：Streamlit UI + 認證判斷（Server 角色）
- `mqtt_bridge.py`：把 UI 與 MQTT 裝置之間做檔案 IPC 橋接
- `node.py`：模擬裝置端 PUF 回應

## 快速啟動（Windows）

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

開三個 terminal：

Terminal A
```bash
python -m streamlit run app.py
```

Terminal B
```bash
python mqtt_bridge.py
```

Terminal C
```bash
python node.py
```

## 檔案整理後的分類

### A. 核心執行（先懂這些）

- `app.py`：Web UI、認證流程、SQLite 歷史紀錄
- `mqtt_bridge.py`：MQTT <-> 本地檔案 IPC 橋接
- `node.py`：模擬裝置端，收到 challenge 後生成 response
- `puf_simulator.py`：PUF 與雜訊模型核心

### B. 實驗與分析腳本

- `batch_test.py`：批次產生 genuine/impostor 資料
- `eer_scan.py`：掃描 EER 與閾值區間
- `plot_roc.py`：畫 ROC 曲線
- `extreme_test.py`：極端環境測試
- `sensitivity_analysis.py`：參數敏感度分析
- `calibrate_from_real_data.py`：用實測資料校正參數
- `run_5_scenarios.py`：一次跑 5 種場景

### C. 驗證與測試

- `test_phase2_antireplay.py`
- `test_phase2_realistic.py`
- `validate_phase1.py`
- `validate_phase1_windows.py`
- `verify_all_phases.py`
- `mqtt_test.py`

### D. 設定與 UI 輔助

- `config.py`：集中設定
- `ui_theme.py`：Streamlit 主題樣式

### E. 文件與產物

- `docs/`：說明文件、檢查表、報告
- `artifacts/`：執行輸出（報表/圖/稽核文檔）

## 主要產出檔

- `artifacts/batch_test_results.csv`
- `artifacts/batch_test_report.json`
- `artifacts/eer_analysis.txt`
- `artifacts/extreme_env_test/environment_comparison.json`

## 安全重點

1. Dynamic challenge + timestamp 檢查：限制重放窗口。
2. Nonce cache：阻擋 session 內重放。
3. HD threshold：是安全與可用性的權衡，不是越高越好。

## 已清理項目

- 移除一次性 patch 腳本：`patch_app.py`, `clean.py`, `do_part2.py`

這三個檔案是歷史修補工具，不屬於正式系統流程。

## 下一步建議

1. 先完整跑一次 `verify_all_phases.py`。
2. 再用 `batch_test.py` + `eer_scan.py` 做你要報告的閾值選擇依據。
3. 若要口試展示，建議固定噪聲設定並預先產生 `artifacts/`。
