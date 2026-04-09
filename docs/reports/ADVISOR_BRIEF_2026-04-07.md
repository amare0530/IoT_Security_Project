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

## 下週三張量化圖（必交）
1. ROC + EER 定位圖
- 橫軸 FAR、縱軸 1-FRR，標示 FAR=FRR 的交點。
- 目前輸出：`artifacts/roc_eer_plot.png`
- 本輪量測（batch_test_report.json）：EER ≈ 0.020（FAR=0.000, FRR=0.040, T=45）。

2. HD 分佈圖（Intra vs Inter）
- 同圖比較 Intra-HD 與 Inter-HD，並標示目前觀察到的誤差區間。
- 目前輸出：`artifacts/hd_distribution_hist.png`
- 本輪量測（samples=1000）：
	- Intra/Genuine：mean=15.50, std=6.49
	- Inter/Impostor：mean=128.52, std=7.75
	- T_normal=35（FRR=0.021, FAR=0.000）

3. 認證延遲分解圖
- 拆解 Network、HMAC、DB Query、HD Compare 四段耗時。
- 目前輸出：`artifacts/latency_breakdown.png`
- 本輪量測（samples=120，ms）：
	- Network RTT: mean=523.301, p95=563.921
	- HMAC: mean=0.002, p95=0.003
	- DB Query: mean=13.092, p95=13.697
	- HD Compare: mean=0.001, p95=0.002

## 本輪可交付檔案
1. `artifacts/roc_eer_plot.png`
2. `artifacts/hd_distribution_hist.png`
3. `artifacts/latency_breakdown.png`
4. `artifacts/latency_breakdown.json`
5. `artifacts/latency_breakdown.csv`

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
- 本系統目前以公開資料集進行系統層驗證，實體板子直接對接與完整硬體閉環為下一階段目標。




