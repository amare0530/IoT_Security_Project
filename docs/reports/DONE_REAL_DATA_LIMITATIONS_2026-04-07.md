# 真實資料限制說明（2026-04-07）

## 文件目的
這份文件用來誠實說明：專題正在從模擬資料過渡到開源/真實資料，目前做到哪裡、還缺什麼。

## 目前狀態
- 即時驗證流程仍以模擬節點為主。
- 認證紀錄已可標記來源（`real` / `simulated`）。
- 已有 `real_data_ingest.py` 可將資料匯入 `crp_records`。

## 目前限制
1. `node.py` 還是模擬回應，尚未接實體採集路徑。
2. 不同開源資料集欄位格式不一，仍需逐資料集做轉接（**已開始處理**）。
3. 多數分析腳本尚未強制跨 session 切分評估。
4. `temperature_c`、`supply_proxy` 的品質取決於外部資料內容。
5. 匯入資料尚未附檔案雜湊與來源簽章。

## 對結果可信度的影響
- 若只看模擬資料，結果可能過度樂觀。
- 若 train/test 同分布，容易低估實際部署時的退化。

## 已採取措施
- 已加入嚴格 CSV 欄位驗證。
- 已將 `source` 納入寫入與查詢流程。
- 已建立可重跑的資料匯入入口。

## 缺漏清單進度

### 項目 1：公開 PUF 資料集轉接器（進行中）

**完成項目**：
- `public_puf_adapter.py`：支援 CSV/TSV 讀取、欄位正規化、SQLite 寫入、manifest 產生。已通過 smoke test 驗證。
- `docs/guides/PUBLIC_PUF_SOURCES.md`：已驗證並列出唯一已確認存在的公開資料集（SRAM-Based PUF Readouts by TIMA Laboratory）。
- 在 README.md 補上使用指南與來源清單連結。

**已驗證存在的公開資料集**：
- **SRAM-Based PUF Readouts** (TIMA Laboratory, Zenodo)
  - URL: https://zenodo.org/records/7529513
  - DOI: 10.1038/s41597-023-02225-9
  - 84 個 STM32 Nucleo 微控制器的 SRAM 讀取 + 溫度/電壓資料
  - CSV 格式，可直接用 adapter 轉接

**待完成項目**：
- 下載 TIMA Laboratory 資料集並執行 adapter 進行全流程驗證。
- 將正規化資料寫入 `authentication_history.db` 的 `crp_records` 表。
- 用 `quant_compare_report.py` 驗證量化對比是否正常運作。
- 繼續搜尋其他開源資料集（但要確認真實存在再列出）。

**使用範例**：
```bash
# 先預覽
python public_puf_adapter.py --input dataset.csv --dataset-name my_dataset --preview --limit 5

# 正式轉接
python public_puf_adapter.py --input dataset.csv --dataset-name my_dataset \
  --output-db authentication_history.db \
  --manifest artifacts/dataset_manifest.json
```

### 項目 2-4：後續
- 強制 train/test 以 `session_id` 與 `source` 切分。
- 補充 provenance manifest 的實際應用案例。
- 將 `crp_records` 接入攻防 benchmark 腳本。




