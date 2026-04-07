# 真實資料長期作戰手冊

這份文件是專題的共同規格。目標很簡單：
把目前可運行的 IoT PUF 展示系統，逐步升級成「有真實資料依據、可重現、可論文對比」的畢業專題版本。

## 兩個 Copilot Chat 怎麼分工

- `some_new_model`：快速原型、模型攻擊實驗、想法驗證。
- `IoT_Security_Project`：正式整合到專題主線（app、mqtt、node、資料庫、報告）。

如果同一週同時做模型與系統整合，流程固定：
1. 先在 `some_new_model` 試想法。
2. 有結果後再移植回 `IoT_Security_Project`。
3. 更新本文件與對應報告，避免兩邊規格分裂。

## 目前現況

- 系統已能穩定跑完整流程，但 live 路徑仍以模擬資料為主。
- 現在有了開源/真實資料的匯入與來源標記能力。
- 目前最大缺口是：真實資料驅動的端到端評估與論文對比表還沒補齊。

## 本專題對「真實資料」的最低要求

至少要有以下條件，才算是可報告的真實資料評估：

- 同一裝置跨時間重複量測。
- 多裝置資料。
- 環境欄位（溫度、供電或負載代理值）。
- 訓練與測試不能混用同一批 session。

每筆資料最少欄位：

- `device_id`
- `challenge`
- `response`
- `timestamp`
- `temperature_c`
- `supply_proxy`
- `session_id`
- `source`（`real` 或 `simulated`）

## 8 週整合路線

### 第 1-2 週：資料契約與匯入

- 定義 CSV / SQLite 欄位。
- 完成 ingest + validate 腳本。
- 全流程強制標記 `source=real/simulated`。

### 第 3-4 週：可重現 baseline

- 固定一套 baseline 攻擊流程。
- 固定 seed 產生可重跑結果。
- 輸出比較表（accuracy、EER proxy、HD）。

### 第 5-6 週：跨域評估

- Train on A、Test on B（跨 session / 跨條件）。
- 量化 domain shift 下的退化幅度。
- 在報告加上 robustness 小節。

### 第 7-8 週：防禦策略閉環

- 用攻擊信心分數反饋到驗證策略。
- 依風險調整 threshold / challenge policy。
- 產出最終儀表板與 ablation 報告。

## 論文與開源對比來源

- pypuf： https://github.com/nils-wisiol/pypuf
- pypuf docs： https://pypuf.readthedocs.io/en/latest/
- pypuf DOI： https://doi.org/10.5281/zenodo.3901410
- NN modeling attacks： https://eprint.iacr.org/2021/555
- LP-PUF paper： https://eprint.iacr.org/2021/1004
- LP-PUF repo： https://github.com/nils-wisiol/LP-PUF

## 後續工作指令範本

"""
請以 docs/REAL_DATA_LONG_TERM_PLAYBOOK.md 作為本次修改規格。
本次只做：
1) 真實資料 schema（CSV + SQLite）
2) ingest + validate
3) 全流程 source 標記
4) docs/reports 下的限制與假設文件
不要改動無關 UI 或做大型重構。
完成後請執行可用的檢查並回報產出檔案。
"""

## 每次實驗的交付標準

每次實驗至少留下：

- config snapshot（含 seed）
- metrics JSON
- 重要時間線或 telemetry
- assumptions / limitations 記錄
- 明確標記資料型態（real / simulated / mixed）

缺其中任一項，就不算完整可答辯結果。


