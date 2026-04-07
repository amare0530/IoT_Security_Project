# 公開 PUF 資料集來源指南

## 文件目的
列出目前已知的公開 SRAM PUF / RO PUF 資料集，包括來源、下載方式、欄位格式與接軌方法。

---

## 已知公開資料集

### 1. PUFdb (Fraunhofer AISEC)
**來源**：https://pufdb.aisec.fraunhofer.de/

**說明**：
- 工業級 SRAM PUF 資料庫，包含多數量晶片與環境變異。
- 提供 CRP (Challenge-Response Pair) 與環境資料（溫度、電壓等）。
- 需要註冊帳號方可下載，採學術免費授權。

**資料格式**：
- CSV 或 TSV，通常欄位包含：
  - `device_id` 或 `chip_id`
  - `challenge`
  - `response`
  - `temperature`
  - `voltage`
  - `timestamp` 或 `date`

**適配方式**：
```bash
python public_puf_adapter.py \
  --input pufdb_export.csv \
  --dataset-name pufdb_[version] \
  --output-db authentication_history.db \
  --manifest artifacts/pufdb_manifest.json
```

**注意事項**：
- Challenge / Response 通常為十進位或十六進位，轉接器會自動正規化。
- 若溫度或電壓缺失，會自動補 `0` 或 `unknown`。

---

### 2. MIT CSAIL / 学术研究發布的 PUF 資料
**來源範例**：
- GitHub 倉庫（搜尋關鍵字）：`puf dataset sram`, `puf crp data`
- Zenodo：https://zenodo.org/（搜尋 "PUF" 或 "SRAM PUF"）
- OSF (Open Science Framework)：https://osf.io/（搜尋 "PUF"）

**推薦搜尋策略**：
1. 在 GitHub 上搜： `"PUF" "CRP" "challenge response"` + `filetype:csv`
2. 在 Zenodo 上搜： `PUF SRAM` 或 `Ring Oscillator PUF`
3. 在論文的 Supplementary Materials 或 Data Availability 欄查找

**常見論文資料集**：
- "Modeling and Exploiting the Unpredictability of SRAM PUF" — CMU / Fraunhofer（通常附 GitHub 或 data.zip）
- "SRAM PUF in the Wild" 系列 — 各校合作研究

**資料格式**：
- 通常為 CSV，欄位名稱可能有變：
  - `device`, `node_id`, `chip_number` → adapter 自動對映到 `device_id`
  - `c`, `q`, `query` → 對映到 `challenge`
  - `r`, `measurement`, `output` → 對映到 `response`
  - `temp`, `temp_c`, `temperature_celsius` → 對映到 `temperature_c`
  - `vdd`, `supply_voltage`, `power` → 對映到 `supply_proxy`

**適配方式**（以某個 GitHub 資料為例）：
```bash
# 下載資料
git clone https://github.com/[university]/puf-dataset.git
cd puf-dataset

# 轉接到本專案格式
python ../../public_puf_adapter.py \
  --input data/sram_puf_measurements.csv \
  --dataset-name github_[repo_name]_[date] \
  --output-csv ../../artifacts/github_dataset_normalized.csv \
  --output-db ../../authentication_history.db \
  --manifest ../../artifacts/github_manifest.json
```

---

### 3. CHES 工作坊 / 相關國際會議發佈的資料集
**來源**：
- CHES (Cryptographic Hardware and Embedded Systems)：https://ches.iacr.org/
- DATE (Design, Automation and Test in Europe)：https://www.date-conference.com/
- ISCAS (International Symposium on Circuits and Systems)：https://www.iscas2025.org/

**搜尋方式**：
- 進入會議網站，找 "Call for Data" 或 "Artifact Evaluation" 區段
- 查找標題含 "PUF", "Authentication", "Silicon" 的論文
- 檢查論文的 Data Availability 或 Supplementary 欄

**資料格式**：
- 通常提供經過消毒的 CRP 集合，格式多樣。
- 大多數使用 CSV 或 JSON。

**適配方式**：
- 先用 `--preview` 檢查欄位名稱：
  ```bash
  python public_puf_adapter.py --input raw_data.csv --preview --limit 3
  ```
- 若 preview 成功，再輸出至目標格式。

---

### 4. 業界開源專案
**來源範例**：
- **uPUF** (Xilinx / Vivado 相關)：部分提供模擬 PUF 的測試資料
- **PUF-Library** (TU Darmstadt)：https://github.com/tud-ics/puf-libraries/
- **FIPS 140 合規 PUF 模組的測試資料**：供應商有時會發佈去識別化的量化資料

**取得方式**：
- 多數需要向供應商或研究團隊申請
- 部分在 GitHub 或論文附錄公開

---

## 如何驗證資料集適配性

### 第一步：預覽資料
```bash
python public_puf_adapter.py \
  --input your_dataset.csv \
  --dataset-name test_preview \
  --preview \
  --limit 5
```

### 第二步：檢查輸出
- 確認 `device_id`、`challenge`、`response` 都被正確對映
- 確認 `timestamp` 與 `session_id` 已補值
- 確認 `metadata_json` 包含原始未對映的欄位

### 第三步：正式匯入
```bash
python public_puf_adapter.py \
  --input your_dataset.csv \
  --dataset-name your_dataset_name \
  --output-csv artifacts/your_dataset_normalized.csv \
  --output-db authentication_history.db \
  --manifest artifacts/your_dataset_manifest.json
```

### 第四步：驗證資料庫寫入
```python
import sqlite3
conn = sqlite3.connect('authentication_history.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM crp_records WHERE dataset_name = ?', ('your_dataset_name',))
print(f"匯入筆數：{cursor.fetchone()[0]}")
conn.close()
```

---

## Adapter 欄位對映速查表

| 標準欄位 | 常見別名 |
|------|--------|
| `device_id` | device, chip_id, chip_number, board_id, node_id, sensor_id |
| `challenge` | crp_challenge, c, q, query, input |
| `response` | crp_response, r, reply, measurement, output, bit_string |
| `session_id` | session, run_id, trial_id, capture_id, measurement_id |
| `timestamp` | time, datetime, capture_time, date, timestamp_unix |
| `temperature_c` | temperature, temp_c, temp, temp_celsius, temperature_celsius |
| `supply_proxy` | voltage, vdd, supply_voltage, power_state, load_state |

---

## 常見問題

**Q: 我下載的資料是 Excel（.xlsx）格式，怎麼處理？**

A: 先轉成 CSV：
```bash
python -c "import pandas as pd; pd.read_excel('data.xlsx').to_csv('data.csv', index=False)"
```

**Q: Challenge 或 Response 的位寬不一致，轉接器會怎樣？**

A: Adapter 會用原始長度當位寬，自動補齊或轉換。若有特定位寬需求，可在匯入後用 `calibrate_from_real_data.py` 調整。

**Q: 資料集沒有提供 device_id，adapter 會怎樣？**

A: 會自動生成 `[dataset_name]_device_[列號]`。

**Q: 轉接後要怎麼在量化對比中用？**

A: 執行 `quant_compare_report.py`，它會自動統計各 `dataset_name` 的 FAR/FRR/HD 分佈。

---

## 後續流程

1. **匯入資料**：用 `public_puf_adapter.py` 正規化並寫入 SQLite。
2. **追蹤來源**：每筆資料都會帶上 `dataset_name`、`source` 與 `metadata_json`。
3. **量化對比**：用 `quant_compare_report.py` 自動生成 FRR/PassRate/HD 分佈。
4. **論文報告**：對應 `docs/reports/PAPER_BASELINE_COMPARISON_2026.md` 的量化維度。

---

最後更新：2026-04-07
