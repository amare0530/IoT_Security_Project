# 指導老師回報摘要（2026-04-07）

## 現況摘要
專題已從「只有模擬展示」進入「可匯入開源資料、可追溯來源、可做量化比較」的階段。

## 目前已完成
1. 資料來源可追溯
- `auth_history` 已新增：`source`、`dataset_name`、`session_id`、`temperature_c`、`supply_proxy`。
- UI 歷史頁可直接篩選 `Dataset-Offline / Live-Pipeline / Simulated`。

2. 來源標籤化已落地（防誤導）
- 最近一次驗證結果會顯示：`Pipeline Source` 與 `Data Source`。
- 最新 Response 區會顯示來源標籤，避免把即時流程與離線統計混為同一來源。
- 系統監控頁新增「研究量化圖表（口試展示）」區塊，並標示來源說明。

3. 開源資料可接入
- 已新增 `real_data_ingest.py`，可驗證 CSV 後寫入 SQLite 的 `crp_records`。
- 已提供欄位範本 `docs/guides/REAL_DATA_SCHEMA_TEMPLATE.csv`。

4. 安全機制已上線
- 使用動態 seed（timestamp + nonce + HMAC）。
- 已有 nonce 防重放檢查。

5. FRR 統計較貼近真實
- 雜訊改為機率翻轉模型，不再是固定翻位元造成 0% 或 100% 的僵硬結果。

## 下一步（明確缺口）
1. 補 UI 圖表區與簡報中的來源標籤一致性（截圖、文字、口頭說法一致）。
2. 補完整 FAR/FRR/EER 曲線與 threshold 掃描結論（跨資料切分重跑）。
3. 補論文 baseline 對照表與可重現 benchmark（固定 run manifest）。

## 下週三張量化圖（必交）
1. ROC + EER 定位圖
- 橫軸 FAR、縱軸 1-FRR，標示 FAR=FRR 的交點。
- 目前輸出：`artifacts/roc_eer_plot.png`
- 本輪量測（batch_test_report.json）：EER ≈ 0.020（FAR=0.000, FRR=0.040, T=45）。

### ROC 優先策略（先跟老師定調）
我們先把 ROC 當作主圖，因為它直接決定門檻 $T$ 的選擇，並且能把 Offline 與 Live 路徑串起來。

1. 樣本定義
- Genuine：合法配對（同裝置/正確 response）。
- Impostor：非合法配對（異裝置或錯誤 response）。

2. 門檻掃描
- 判定規則：$HD \le T$ 視為通過。
- 對每個 $T$ 計算 FAR 與 FRR。

3. 指標定義
- $FAR(T)=\frac{\text{Impostor 被接受數}}{\text{Impostor 總數}}$
- $FRR(T)=\frac{\text{Genuine 被拒絕數}}{\text{Genuine 總數}}$
- ROC 繪圖採 $(x,y)=(FAR,1-FRR)$。

4. EER 解讀
- $EER$ 為 FAR 與 FRR 最接近的操作點。
- 本輪結果 EER 約 0.020，代表在真實雜訊條件下仍維持可用分離度。

5. Offline -> Live 連動說法
- Offline ROC/EER：決定候選門檻區間（統計信度）。
- Live Pipeline：驗證該門檻在即時流程下是否穩定（工程效度）。
- 定調：兩條路徑分工不同，但門檻策略一致，不是兩套互相矛盾的系統。

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
- 現在每筆資料可分辨 Dataset-Offline / Live-Pipeline / Simulated，也能匯入開源資料做統一流程驗證。
- 下一階段是把 live 路徑改成真實資料驅動，並交付 FAR/FRR/EER 與論文 baseline 對照。

## ROC 防追問口試稿（可直接使用）
Q1. 你這張 ROC 是即時系統跑出來的嗎？
- A：ROC/EER 來自 Dataset-Offline 的批次統計，用來建立門檻的統計信度；即時系統負責驗證流程可行性與延遲表現。

Q2. 為什麼不是只報一個準確率？
- A：準確率會被資料不平衡影響；ROC 與 EER 可以同時呈現 FAR/FRR 權衡，更適合安全系統評估。

Q3. 你怎麼把離線結果用在即時系統？
- A：先用 ROC 找候選門檻區間，再在 Live-Pipeline 驗證該門檻的誤拒率與延遲，保持同一門檻策略跨場景一致。

## 這週可展示操作
1. `real_data_ingest.py --validate-only` 驗證資料格式。
2. 匯入資料後確認 `crp_records` 有新增紀錄。
3. 在 app 歷史頁用 `source` 篩選 real/simulated。

## 會前 5 分鐘重跑（ROC 優先）
1. 重新產生批次統計
- `python batch_test.py`

2. 重新繪製 ROC 圖
- `python plot_roc.py`

3. 確認輸出檔存在
- `artifacts/batch_test_report.json`
- `artifacts/roc_eer_plot.png`（口試主圖）

## 真實性聲明
- 目前是「模擬 + 開源資料接軌」混合狀態。
- 不宣稱已完成硬體端完整閉環，避免過度包裝結果。
- 本系統目前以公開資料集進行系統層驗證，實體板子直接對接與完整硬體閉環為下一階段目標。




