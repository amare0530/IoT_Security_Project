# 論文與基準對照表（2026-04-07）

## 目的
把「我們目前做到的成果」和「可引用論文/開源基準」放在同一張表比較，避免只剩功能展示。

## 建議採用的正式 Baseline
本專題正式報告建議固定採用下列三層 baseline，分別對應資料來源、工具基準與研究型對照：

1. **資料基礎**：Vinagrero et al. (2023), Scientific Data
- 用途：證明公開 SRAM PUF 資料的來源、規模與環境條件。
- 定位：資料來源，不作為方法對照。

2. **工具基準**：pypuf
- Repo: https://github.com/nils-wisiol/pypuf
- Docs: https://pypuf.readthedocs.io/en/latest/
- DOI: https://doi.org/10.5281/zenodo.3901410
- 用途：作為可重現模擬基準，對照真實資料驅動流程。

3. **研究型 baseline**：
- PUF 神經網路建模攻擊
	- Paper: https://eprint.iacr.org/2021/555
- LP-PUF
	- Paper: https://eprint.iacr.org/2021/1004
	- Repo: https://github.com/nils-wisiol/LP-PUF
- 用途：說明 PUF 系統在面對建模攻擊與實作變體時的差異，並支撐我們加入抗重放與可審計流程的必要性。

## 對照表
| 維度 | 典型 baseline 做法 | 我們目前狀態 | 待補項目 |
|---|---|---|---|
| 資料來源 | 硬體採集或公開資料，含 metadata | 已可匯入 open CSV，並標記 source | live node 尚未改成真實資料驅動 |
| 防重放 | nonce + time window + session check | 已有動態 challenge 與 nonce 檢查 | 尚缺跨 session 壓測報告 |
| 指標 | FAR / FRR / EER / ROC | 已補最新量測：EER≈0.020（T=45），HD 分離度 128.52-15.50 | 需再補多資料域重跑（不同資料切分） |
| 可重現性 | 固定 seed、固定設定與輸出 | 已有部分腳本可重跑 | 尚缺統一 run manifest/provenance |
| 論文對照 | baseline + ablation | 已有資料來源清單 | 尚缺正式 benchmark 對照章節 |

## 報告用最終 Baseline 對照（可直接貼簡報）
| 比較維度 | 模擬工具（pypuf） | 數據論文（Vinagrero 2023） | 本系統（Our Work） |
|---|---|---|---|
| 物理層輸入 | 數學模型與隨機分佈 | 實體 SRAM 讀值（84 設備） | 實體 SRAM 讀值 + 環境欄位整合 |
| 通訊層機制 | 無（工具庫層） | 無（離線資料） | MQTT + HMAC + Nonce + Timestamp |
| 認證邏輯 | 偏向理想化匹配 | 統計品質分析為主 | 動態門檻 + 審計日誌（SQLite） |
| 結果輸出 | 模擬指標（方法依設定而變） | 資料統計指標（非即時認證） | FAR / FRR / EER / ROC + 可追溯紀錄 |
| 應用定位 | 演算法驗證工具 | 公開基準資料集 | 端到端 IoT 安全流程驗證平台 |

## 最新量化結果（2026-04-09）
1. ROC / EER（`artifacts/roc_eer_plot.png`）
- EER ≈ 0.020（FAR=0.000, FRR=0.040, T=45）。

2. HD 分佈（`artifacts/hd_distribution_hist.png`）
- Intra/Genuine：mean=15.50, std=6.49。
- Inter/Impostor：mean=128.52, std=7.75。
- T_normal=35 時：FRR=0.021, FAR=0.000。

3. 延遲分解（`artifacts/latency_breakdown.png`）
- Network RTT：mean=523.301 ms, p95=563.921 ms。
- HMAC：mean=0.002 ms, p95=0.003 ms。
- DB Query：mean=13.092 ms, p95=13.697 ms。
- HD Compare：mean=0.001 ms, p95=0.002 ms。

## 非可比註記（Different Setup）
1. pypuf 與本系統在通訊層與部署假設不同，Network RTT 不可直接橫比。
2. Vinagrero 2023 為資料集論文，主要是資料品質與條件描述，非端到端線上驗證流程。
3. 建模攻擊與 LP-PUF 文獻的 threat model 與實驗條件不同，僅能做方法層級對照，不做百分比優勢宣稱。

## 目前可主打的進步點
1. 有系統整合：動態 challenge、反重放、MQTT、UI、DB 已串成可跑流程。
2. 有真實化方向：已能接開源資料並保留來源欄位，不是只有模擬結果。
3. 有可審計性：每筆資料可追溯來源與環境欄位。

## 接下來兩週的量化交付
1. 三張圖：ROC、FAR/FRR 對門檻、跨 session 退化。
2. 一張總表：本系統 vs 至少三個 baseline。
3. 每次實驗都固定保存：config、seed、dataset、source、metrics JSON。

## 答辯時可用說法
- 我們已把專題從功能展示轉成可量化、可比較、可重現的研究流程。
- 結果不只看 pass/fail，還會對照資料來源與指標曲線。
- 後續重點是補齊 baseline 對照與跨資料域評估。
- 本報告採用三層 baseline：資料來源、模擬工具與研究型方法，避免把資料集與方法混為同一層次。




