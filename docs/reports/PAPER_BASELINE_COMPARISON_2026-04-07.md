# 論文與基準對照表（2026-04-07）

## 目的
把「我們目前做到的成果」和「可引用論文/開源基準」放在同一張表比較，避免只剩功能展示。

## 基準來源
1. pypuf（可重現工具基準）
- Repo: https://github.com/nils-wisiol/pypuf
- Docs: https://pypuf.readthedocs.io/en/latest/
- DOI: https://doi.org/10.5281/zenodo.3901410

2. PUF 神經網路建模攻擊
- Paper: https://eprint.iacr.org/2021/555

3. LP-PUF
- Paper: https://eprint.iacr.org/2021/1004
- Repo: https://github.com/nils-wisiol/LP-PUF

## 對照表
| 維度 | 典型 baseline 做法 | 我們目前狀態 | 待補項目 |
|---|---|---|---|
| 資料來源 | 硬體採集或公開資料，含 metadata | 已可匯入 open CSV，並標記 source | live node 尚未改成真實資料驅動 |
| 防重放 | nonce + time window + session check | 已有動態 seed 與 nonce 檢查 | 尚缺跨 session 壓測報告 |
| 指標 | FAR / FRR / EER / ROC | 已有 FRR 與 HD 統計 | 尚缺完整 FAR/EER 曲線與門檻建議 |
| 可重現性 | 固定 seed、固定設定與輸出 | 已有部分腳本可重跑 | 尚缺統一 run manifest/provenance |
| 論文對照 | baseline + ablation | 已有資料來源清單 | 尚缺正式 benchmark 對照章節 |

## 目前可主打的進步點
1. 有系統整合：VRF、反重放、MQTT、UI、DB 已串成可跑流程。
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


