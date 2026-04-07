# 指導老師回報摘要（2026-04-07）

## 現況摘要
專題已從「只有模擬展示」進入「可匯入開源資料、可追溯來源、可做量化比較」的階段。

## 目前已完成
1. 資料來源可追溯
- `auth_history` 已新增：`source`、`dataset_name`、`session_id`、`temperature_c`、`supply_proxy`。
- UI 歷史頁可直接篩選 `real/simulated`。

2. 開源資料可接入
- 已新增 `real_data_ingest.py`，可驗證 CSV 後寫入 SQLite 的 `crp_records`。
- 已提供欄位範本 `docs/guides/REAL_DATA_SCHEMA_TEMPLATE.csv`。

3. 安全機制已上線
- 使用動態 seed（timestamp + nonce + HMAC）。
- 已有 nonce 防重放檢查。

4. FRR 統計較貼近真實
- 雜訊改為機率翻轉模型，不再是固定翻位元造成 0% 或 100% 的僵硬結果。

## 下一步（明確缺口）
1. `node.py` 改為可由真實/開源資料驅動，不只模擬回應。
2. 補完整 FAR/FRR/EER 曲線與 threshold 掃描結論。
3. 補論文 baseline 對照表與可重現 benchmark。

## 簡短口頭回報建議
- 我們已先把系統做成可研究、可追溯，不再只是展示介面。
- 現在每筆資料可分辨 real/simulated，也能匯入開源資料做統一流程驗證。
- 下一階段是把 live 路徑改成真實資料驅動，並交付 FAR/FRR/EER 與論文 baseline 對照。

## 這週可展示操作
1. `real_data_ingest.py --validate-only` 驗證資料格式。
2. 匯入資料後確認 `crp_records` 有新增紀錄。
3. 在 app 歷史頁用 `source` 篩選 real/simulated。

## 真實性聲明
- 目前是「模擬 + 開源資料接軌」混合狀態。
- 不宣稱已完成硬體端完整閉環，避免過度包裝結果。




