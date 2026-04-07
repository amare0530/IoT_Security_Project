# IoT Security Project

PUF-based IoT device authentication demo project.

本專案現在是「可重現實驗 + 展示」型態，不是 production service。

## 你應該先看哪裡

如果你是 C++ 背景、Python 初學者，先看：

1. `docs/guides/CPP_TO_PYTHON_QUICKSTART.md`
2. `docs/guides/QUICKSTART.md`
3. `app.py`, `node.py`, `mqtt_bridge.py`（三個核心執行檔）

如果要先準備和老師報告，建議先看：

1. `docs/reports/ADVISOR_BRIEF_2026-04-07.md`
2. `docs/reports/PAPER_BASELINE_COMPARISON_2026-04-07.md`
3. `docs/guides/SYSTEM_DATAFLOW_ARCHITECTURE.md`

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

若要用資料集模式啟動 Node（從 `crp_records` 回傳 response）：

```bash
$env:PUF_MODE="dataset"
python node.py
```

可選參數：

```bash
$env:DATASET_NAME="your_dataset_name"
$env:ALLOW_SIM_FALLBACK="0"
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

## 開源/真實資料接軌（已完成第一階段）

目前已加入 CSV 驗證與 SQLite 匯入流程，可把開源或實測 CRP 資料納入同一套資料庫。

1. 先準備資料欄位（可直接用範本）

- `docs/guides/REAL_DATA_SCHEMA_TEMPLATE.csv`

2. 先只做驗證（不寫入）

```bash
python real_data_ingest.py --input docs/guides/REAL_DATA_SCHEMA_TEMPLATE.csv --validate-only
```

3. 驗證通過後再匯入 SQLite

```bash
python real_data_ingest.py --input your_dataset.csv --dataset-name your_open_dataset_name
```

4. 在 UI 的「歷史記錄」頁，可用 `資料來源` 篩選 `real/simulated`。

補充：
- `auth_history` 現在有 `source/dataset_name/session_id/temperature_c/supply_proxy` 欄位。
- 新增 `crp_records` 表專門存放開源/實測資料集，不會污染即時驗證流程。

### 公開資料集轉接器

如果你手上有公開 PUF 資料集的 CSV 或 TSV，可以先用 `public_puf_adapter.py` 轉成本專案的標準格式。

**先參考** [公開 PUF 資料集來源指南](docs/guides/PUBLIC_PUF_SOURCES.md)，了解現有的公開資料集在哪裡、怎麼下載與驗證格式相容性。

常用指令如下：

```bash
# 先預覽，確認欄位能否對映
python public_puf_adapter.py --input your_public_dataset.csv --dataset-name demo --preview --limit 5

# 正式轉接並輸出 CSV
python public_puf_adapter.py --input your_public_dataset.csv --dataset-name your_dataset_name --output-csv artifacts/your_dataset_normalized.csv

# 直接寫入 SQLite（推薦）
python public_puf_adapter.py --input your_public_dataset.csv --dataset-name your_dataset_name --output-db authentication_history.db --manifest artifacts/your_dataset_manifest.json
```

此工具會自動處理常見欄位名稱差異，例如 device、session、temperature、voltage 等，並補上 metadata_json。每筆資料都會帶上：
- `dataset_name`：資料集識別符
- `source`：標記為 `real`（表示來自公開/實驗資料）
- `metadata_json`：原始資料的無法對映欄位與來源檔案資訊
- `session_id`：若原資料缺失，會補上 `[dataset_name]_session_[列號]`
- `timestamp`：若原資料缺失，會用匯入時刻補上

## 論文對照摘要輸出

可用下列指令自動產生一份量化摘要 Markdown（含 FRR/PassRate/HD 與 source 分佈）：

```bash
python quant_compare_report.py
```

預設輸出到 `docs/reports/QUANT_COMPARISON_YYYY-MM-DD.md`。

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




