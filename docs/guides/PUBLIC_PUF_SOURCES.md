# 公開 PUF 資料集來源指南（已驗證版）

## 文件目的
列出**實際存在且可下載**的公開 SRAM PUF 資料集。

---

## 已驗證可用的公開資料集

### 1. SRAM-Based PUF Readouts (TIMA Laboratory)

**來源**：https://zenodo.org/records/7529513

**說明**：
- 84 個 STM32 Nucleo STM32L476 微控制器的完整 SRAM 讀取
- 每個設備採集 9 週，每週 1 次讀取
- 包含溫度和電壓感測器資料
- TIMA Laboratory (Université Grenoble Alpes) 發布
- 2023 年發表在 *Scientific Data*（Nature 旗下期刊）
- DOI: 10.1038/s41597-023-02225-9
- 開放存取，可自由下載使用

**資料格式**：
兩個 CSV 文件：
1. SRAM 記憶體讀取（`crps.csv`）：
   - `board_type`: "Nucleo"
   - `uid`: STM32 96 位 ID（24 十六進位字元）
   - `pic`: 設備在鏈中的位置（1-84）
   - `address`: 記憶體位址
   - `data`: 512 位元組（以逗號分隔）
   - `created_at`: ISO 時間戳

2. 感測器讀取（`sensors.csv`）：
   - `board_type`: "Nucleo"
   - `uid`: STM32 96 位 ID
   - `pic`: 位置
   - `temperature`: 攝氏度
   - `voltage`: 電壓
   - `created_at`: ISO 時間戳

**適配步驟**：

```bash
# 1. 下載並解壓
cd ~/Downloads
unzip zenodo_sram_puf_readouts.zip
cd sram_puf_readouts

# 2. 預覽資料（確認欄位對映）
python YOUR_PROJECT/public_puf_adapter.py \
  --input crps.csv \
  --dataset-name sram_puf_tima_2023 \
  --preview \
  --limit 3

# 3. 轉接到本專案格式
python YOUR_PROJECT/public_puf_adapter.py \
  --input crps.csv \
  --dataset-name sram_puf_tima_2023 \
  --output-db YOUR_PROJECT/authentication_history.db \
  --manifest YOUR_PROJECT/artifacts/sram_puf_manifest.json

# 4. 驗證匯入
python -c "
import sqlite3
conn = sqlite3.connect('authentication_history.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM crp_records WHERE dataset_name = ?', ('sram_puf_tima_2023',))
print(f'Imported {cursor.fetchone()[0]} CRP records')
conn.close()
"
```

**引用方式**：
如使用此資料集，請引用：
> Sergio Vinagrero, Honorio Martin Gonzalez, Alice de Bignicourt, Gabriel Di Natale, Etienne Irissé Vatajelu, and Ernesto Trinidad García. "SRAM-Based PUF Readouts." *Scientific Data*, 10:333, 2023. https://doi.org/10.1038/s41597-023-02225-9

---

## 搜尋其他資料集的方法

### Zenodo（最可靠）
網址：https://zenodo.org/

1. 搜尋框輸入 `"SRAM PUF"` 或 `"physically unclonable"`
2. 篩選左側 Type = "Dataset"
3. 檢查 Description 是否有清楚的欄位說明
4. 看 Files 區段預覽資料

### GitHub
用以下搜尋語法：
```
site:github.com "SRAM" "challenge" "response" csv
site:github.com "PUF" "dataset" "CRP"
```

進入倉庫後檢查：
- README 有沒有清楚說明資料來源和格式
- LICENSE（確認允許學術使用）
- 有沒有 `data/` 或 `datasets/` 資料夾

### 論文的 Data Availability 欄
在 Google Scholar 或 IACR eprint 搜：
```
"SRAM PUF" "measurement" "dataset"
"challenge response pairs" "download"
```

進入論文後找 "Data Availability" 或 "Supplementary Materials" 欄，通常會有 Zenodo DOI、GitHub 連結或作者聯絡方式。

---

## 欄位對映速查表

| 標準欄位 | 常見別名 |
|------|--------|
| `device_id` | device, chip_id, chip_number, board_id, node_id, sensor_id, uid |
| `challenge` | crp_challenge, c, q, query, input, address |
| `response` | crp_response, r, reply, measurement, output, bit_string, data |
| `session_id` | session, run_id, trial_id, capture_id, measurement_id, pic |
| `timestamp` | time, datetime, capture_time, date, timestamp_unix, created_at |
| `temperature_c` | temperature, temp_c, temp, temp_celsius, temperature_celsius |
| `supply_proxy` | voltage, vdd, supply_voltage, power_state, load_state |

---

## 說實話

公開的 PUF 資料集**確實稀少**。如果找不到，合理的替代方案有：

1. **使用我們的模擬資料當基線**（已有 `puf_simulator.py`）
2. **聯絡論文作者直接申請**（很多願意分享）
3. **自己採集真實硬體資料**（ATMega、STM32 等都可以）

想做嚴肅 benchmark，至少要找到一份真實資料集與模擬基線對比。單純模擬資料會被評審質疑實驗有效性。

最後更新：2026-04-07
