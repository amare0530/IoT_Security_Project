# 公開 PUF 資料集來源指南（實用版）

## 文件目的
整理查找公開 SRAM PUF / RO PUF 資料集的方法。由於公開資料集不如論文多，本文列出已知的搜尋渠道與驗證方式。

---

## 說實話

公開的 PUF 資料集其實不多。大部分 PUF 研究因為涉及硬體特性，資料集通常：
1. 被公司或研究機構限制分享（需申請）
2. 只附在論文著作裡（需聯絡作者）
3. 刪除識別資訊後在 Zenodo、GitHub 刊登

這份指南列出的是「可能找到的渠道」而不是「確保有料」的清單。

---

## 實際可用的搜尋渠道

### 1. GitHub — 最直接
**搜尋策略**：
```
site:github.com PUF SRAM dataset
site:github.com PUF challenge response
site:github.com SRAM measurements csv
```

**常見結果內容**：
- 部分會議或論文作者的 artifact 倉庫
- 研究生的專題程式碼與配套測試資料
- 馬上一個一個點進去檢查是否有 `.csv` 或 `data/` 資料夾

**檢查點**：
- 看 `README.md` 有沒有清楚說資料從哪來
- 看 `LICENSE` 是不是允許學術使用
- 有沒有 `requirements.txt` 或 `.py` 能驗證資料格式

### 2. Zenodo（正式資料倉庫）
**網址**：https://zenodo.org/

**搜尋**：
- 關鍵字：`"PUF" AND "SRAM"`、`"PUF" AND "dataset"`、`"PUF" AND "measurement"`
- 篩選：Publication Type = "Dataset"

**優點**：
- 有 DOI，可引用
- 通常會註明 License 與使用限制
- 多數學術資料集用這裡存

**檢查點**：
- 看 Description 有沒有清楚說資料格式
- 看有沒有 `Files` 區段能預覽欄位
- 注意 License 和 Access 限制

### 3. OSF (Open Science Framework)
**網址**：https://osf.io/

**搜尋**：
- 在搜尋框輸入 `PUF SRAM` 或只搜 `PUF`
- 篩選 Component Type = "Project"

**說明**：
- 多數是研究者發佈的配套資料
- 不如 Zenodo 正式，但也滿常見

### 4. 論文直接查詢
**方法**：
1. 用 Google Scholar 搜 `SRAM PUF dataset`
2. 進入論文頁面，找 "Data Availability" 或 "Supplementary Materials" 欄
3. 很多論文會在這裡貼 GitHub 連結、Zenodo DOI、或直接郵件聯絡方式

**常見論文與來源** (根據著作與會議記錄)：
- Fraunhofer AISEC 發表過的 PUF 工作 → 有時附 GitHub
- CHES、DATE、ISCAS 的 PUF 相關論文 → 通常附 artifact repo
- 但具體 URL 我不確定，建議直接在這些會議的網站查

### 5. 向研究團隊直接要
**實際可行性**：
- Fraunhofer AISEC (PUFdb 製作團隊) — 可試著發信要求學術使用授權
- 論文作者 — 很多願意分享拿不出品授權的資料

**找聯絡方式**：
- 在論文或機構網頁找作者 email
- GitHub 倉庫通常留 issue tracker

---

## 實際工作流程

### 第一步：精準的 Google Scholar 搜尋
```
site:scholar.google.com "SRAM PUF" "dataset" OR "measurement"
```

查看有 "Data Availability" 欄的論文。

### 第二步：找到資料集後，用 Adapter 驗證相容性
```bash
python public_puf_adapter.py \
  --input your_dataset.csv \
  --dataset-name test_preview \
  --preview \
  --limit 5
```
```
python public_puf_adapter.py \
  --input your_dataset.csv \
  --dataset-name test_preview \
  --preview \
  --limit 5
```

確認 `device_id`、`challenge`、`response` 都被正確對映，若無誤繼續。

### 第三步：正式匯入到 SQLite
```bash
python public_puf_adapter.py \
  --input your_dataset.csv \
  --dataset-name your_dataset_name \
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

## 欄位對映速查表

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

## 從這開始

如果你找到了具體的公開資料集連結（GitHub、Zenodo、論文），把 URL 或檔案放到這裡，我可以幫驗證格式能否對接。如果找不到，就用上面的搜尋方式自己摸。

**誠實話**：PUF 公開資料集真的不多。如果想做嚴肅的 benchmark，可能需要：
1. 聯絡研究團隊申請授權使用
2. 自己設計硬體實驗採集
3. 或者用我們專案的模擬資料當基線（已有），再用任何能找到的小樣本做比對

最後更新：2026-04-07
