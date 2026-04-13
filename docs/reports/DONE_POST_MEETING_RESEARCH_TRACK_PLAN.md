# 畢業專題後續規劃 — 研究分支 + 實作分支
## 雙軌制進度管理（April 13, 2026 後）

---

## 📌 總體戰略

你現在有兩個獨立的工作線：

### 線路 A：「實作分支」（Programming Track）
- **負責人**：Copilot Agent 1（當前主要助手）
- **目標**：確保 app.py / node.py / mqtt_bridge.py 完整運行
- **成果物**：可演示的系統、ROC/EER 圖表、延遲統計

### 線路 B：「研究分支」（Research Track）
- **負責人**：Copilot Agent 2（深度論文研究）
- **目標**：深入分析 Nature 數據、對標現有文獻、設計對抗實驗
- **成果物**：論文初稿、對抗驗證報告、創新點對比表

**同步進行，互相補充。**

---

## 🚀 線路 A：實作分支代辦（優先級排序）

### 第一週（April 13-14）「會議準備 + 基礎驗證」

#### P0（必須在明天會議前）
- [ ] **驗證 app.py 無語法錯誤**
  - 執行：`./.venv/Scripts/python.exe app.py` 檢查啟動
  - 預期：Streamlit 能成功啟動，沒有 ImportError
  - 任務時間：5 分鐘

- [ ] **確認時序圖正確顯示**
  - 在 app.py 中確認 `verify_response_payload()` 的返回結構完整
  - 確保歷史表格的 `data_source_label` 和 `pipeline_label` 欄位被正確填充
  - 任務時間：10 分鐘

#### P1（會議後 1-2 天內）
- [ ] **執行 batch_test.py 刷新數據**
  - 指令：`python batch_test.py`
  - 輸出：`artifacts/batch_test_report.json` 更新
  - 任務時間：5-10 分鐘（取決於測試規模）

- [ ] **執行 plot_roc.py 生成 ROC 圖**
  - 指令：`python plot_roc.py`
  - 輸出：`artifacts/roc_eer_plot.png` 生成
  - 驗證：圖表能否成功嵌入 app.py 的圖表區段
  - 任務時間：5 分鐘

### 第二週（April 15-18）「系統整合 + 可視化」

#### P1（高優先級）
- [ ] **完整的延遲分析可視化**
  - 執行：`python analyze_latency_breakdown.py`（如果存在）或撰寫此腳本
  - 輸出：`artifacts/latency_breakdown.png`
  - 內容：Network delay / HMAC 計算 / DB lookup / Hamming Distance 比對 的時間分解
  - 用途：展示系統各模組的性能瓶頸

- [ ] **Hamming Distance 分佈直方圖**
  - 來源：从 batch_test_report.json 的驗證結果提取
  - 圖表：同設備的 HD（應該小）vs 不同設備的 HD（應該接近 50%）
  - 任務時間：15 分鐘

#### P2（中優先級）
- [ ] **實時 MQTT 演示流程**
  - 啟動：`msqtt_bridge.py` + `node.py` + `app.py` 三進程
  - 驗證：能否在 UI 上看到即時認證序列
  - 任務時間：10 分鐘

- [ ] **SQLite 審計日誌查詢頁面**（如果尚未實現）
  - 在 app.py 增加新的 Streamlit 分頁
  - 展示 `auth_history` 表的完整紀錄可搜尋介面
  - 任務時間：20 分鐘

### 第三週（April 19-25）「對抗測試準備」

#### P1
- [ ] **準備 dataset-first mode 的測試**
  - 驗證 `node.py` 的 `PUF_MODE="dataset"` 是否正確從 crps.csv 中讀取數據
  - 檢查：隨機取 10 個設備 ID，驗證它們的 Response 能否正確返回
  - 任務時間：15 分鐘

- [ ] **設計 Modeling Attack 的對比框架**
  - 建立測試腳本：`test_modeling_attack_comparison.py`
  - 邏輯：
    - 取 crps.csv 的 80% 作為訓練集
    - 用 20% 作為測試集
    - 訓練 ML 模型（SVM/RF）預測 Response
    - 比較「純 SRAM」vs「VRF 處理後」的攻擊成功率
  - 輸出：`artifacts/modeling_attack_report.json`
  - 任務時間：45 分鐘

---

## 📚 線路 B：研究分支代辦（深度論文準備）

### 第一週（April 13-14）「基礎研究 + 文獻梳理」

#### P0（會議前必備）
- [ ] **深讀 Nature 2023 論文全文**
  - URL：https://www.nature.com/articles/s41597-023-02225-9
  - 重點段落：
    - Abstract & Introduction（為什麼這份數據重要）
    - Methods（數據採集方式、環境控制）
    - Results（主要統計結論）
    - Code Availability（提供的資源）
  - 重點記錄：
    - 設備類型（45 台 STM32）
    - 環境範圍（溫度、電壓、濕度）
    - Response 位元長度
    - 已知的 BER（位元錯誤率）
    - 已知的 Uniqueness / Reliability 指標
  - 產出物：`NATURE_2023_DETAILED_NOTES.md`
  - 任務時間：30 分鐘

#### P1（會議後 1 週內）
- [ ] **尋找 2021-2022 PUF 綜述論文**
  - 搜索關鍵詞：
    - "SRAM PUF Authentication Protocol Review"
    - "Hardware Security Primitive: PUF"
    - "Modeling Attack on SRAM PUF"
  - 目標找 3-5 篇經典綜述（引用率高、時間近）
  - 產出物：`BASELINE_PAPERS_2021-2022.md`（包含 DOI、核心論點、與你專題的關聯）
  - 任務時間：45 分鐘

- [ ] **追蹤開源 Modeling Attack 實現**
  - 在 GitHub 上搜尋：
    - "SRAM PUF machine learning attack"
    - "PUF modeling attack Python"
    - "CRP-based SVM attack"
  - 目標：找到至少 2 個可運行的 GitHub 倉庫
  - 評估：代碼是否能在你的 crps.csv 上直接運行
  - 產出物：`ATTACK_TOOLS_EVALUATION.md`（列出工具、優缺點、集成計劃）
  - 任務時間：1 小時

### 第二週（April 15-18）「數據深度分析」

#### P1
- [ ] **crps.csv 的統計特徵提取**
  - 使用 Pandas 進行取樣分析（前 10 萬行或特定設備）
  - 提取指標：
    - 每個設備的平均 Response 位元翻轉率
    - 不同設備間的 Hamming Distance 分佈（應該接近 50%）
    - Response 的位元位置穩定性（哪些位置容易變化）
  - 視覺化：
    - 位元穩定性熱圖（42台設備 × 128位元位置）
    - Hamming Distance 分佈直方圖
  - 產出物：
    - `artifacts/crps_statistical_analysis.json`
    - `artifacts/bit_stability_heatmap.png`
    - `artifacts/hd_distribution_crossdevice.png`
  - 任務時間：1.5 小時

- [ ] **sensors.csv 與 Response 變異的相關性分析**
  - 問題：當溫度升高時，Response 的位元翻轉率會增加嗎？
  - 方法：
    - 對於每台設備，計算 (溫度, BER) 的 Pearson 相關係數
    - 對於每台設備，計算 (電壓, BER) 的 Pearson 相關係數
  - 產出物：`artifacts/environment_sensitivity_analysis.json`
  - 預期結論："BER 與溫度呈正相關（r ≈ 0.6-0.8）"
  - 任務時間：45 分鐘

#### P2
- [ ] **設備老化趨勢分析**
  - 問題：隨著時間推移，同一設備的 Response 是否變得更不穩定？
  - 方法：
    - 按時間排序 sensors.csv 的測量點
    - 計算早期與晚期測量的 Response 變異差異
  - 產出物：`artifacts/aging_trend_analysis.json`
  - 預期結論："老化速率 < 1% BER/week"（如果穩定）
  - 任務時間：30 分鐘

### 第三週（April 19-25）「對抗實驗 + 論文框架」

#### P1
- [ ] **Modeling Attack 實驗設計文檔**
  - 內容：
    - 攻擊目標：預測任意新 Challenge 的 Response
    - 攻擊假設：攻擊者已獲得 crps.csv（80% 訓練集）
    - 評估指標：Attack Accuracy（預測正確率）
    - 防禦場景 1（無防禦）：直接用原始 Response
    - 防禦場景 2（有 VRF）：Response → VRF 處理 → Masked Response
  - 產出物：`EXPERIMENT_DESIGN_MODELING_ATTACK.md`
  - 任務時間：30 分鐘

- [ ] **執行 Modeling Attack 實驗**
  - 準備：
    - 從 crps.csv 中抽取設備 uid 中的第一台
    - 收集該設備的 1000+ 個 CRP 對（80% 訓練, 20% 測試）
  - 實驗流程：
    - 用 Scikit-learn 訓練 SVM / Random Forest / MLP 模型
    - 評估測試集上的準確率
    - 記錄混淆矩陣（Confusion Matrix）
  - 產出物：
    - `artifacts/modeling_attack_no_defense.json`（包含 accuracy、confusion matrix）
    - `artifacts/modeling_attack_no_defense_plot.png`（ROC 曲線）
  - 任務時間：2 小時

- [ ] **設計 VRF 防禦驗證邏輯**
  - 問題：如何量化 VRF 的防禦效果？
  - 方法：
    - 對同一設備，用 Nonce 參數化 VRF（模擬多次認證）
    - 收集 VRF 處理後的 Masked Response
    - 訓練同樣的 ML 模型預測 Masked Response
    - 比較準確率對比
  - 預期結果："無防禦 accuracy ≈ 95%, 有 VRF accuracy ≈ 50% (隨機)"
  - 任務時間：1.5 小時

### 第四週（April 26 - May 2）「論文初稿」

#### P1
- [ ] **創新點對比表**
  - 格式：
    ```
    | 研究維度 | 文獻 A (2021) | 文獻 B (2022) | 你的專題 |
    |---------|-------------|-------------|--------|
    | 真實數據 | 否 | 部分 | 是 (Nature 2023) |
    | 防禦層數 | 1 (基本認證) | 2 (認證+通訊加密) | 3 (VRF+HMAC+時戳) |
    | 對抗驗證方式 | 無 | 簡單攻擊 | 完整建模攻擊 |
    | ...     | ... | ... | ... |
    ```
  - 任務時間：45 分鐘

- [ ] **論文結構初稿**
  - 典型結構：
    1. 摘要 (Abstract)
    2. 導論 (Introduction) — 為什麼 PUF 安全重要
    3. 相關工作 (Related Work) — 對標 2021-2022 綜述
    4. 系統設計 (System Design) — 你的三層防禦架構
    5. 實驗設計 (Experiment Design) — Modeling Attack 框架
    6. 結果分析 (Results) — 對比圖表與統計數據
    7. 討論 (Discussion) — 侷限與未來工作
    8. 結論 (Conclusion)
  - 任務時間：2 小時（框架初稿）

---

## 🔗 線路間的交互點

### 實作分支向研究分支提供的資料
```
app.py / node.py 的運行 
  ↓
batch_test_report.json（驗證統計）
  ↓
研究端用來計算 False Acceptance Rate (FAR) 與 False Rejection Rate (FRR)
  ↓
繪製 ROC 曲線論文圖表
```

### 研究分支向實作分支反饋的洞察
```
Modeling Attack 結果表明「位元位置 5, 23, 67 最容易被破解」
  ↓
實作端可以考慮在 VRF 計算時特別保護這些位元
  ↓
通過額外測試驗證防禦效果
  ↓
迭代改進
```

---

## 📊 進度跟蹤表（自我核對）

### Week 1 (April 13-14) — 會議準備週
- [ ] 會議順利進行，老師提出具體反饋
- [ ] batch_test.py / plot_roc.py 已執行
- [ ] Nature 論文深讀完成
- [ ] 2-3 篇綜述論文已識別

### Week 2 (April 15-18) — 整合與數據分析週
- [ ] app.py 完整演示無問題
- [ ] crps.csv 統計分析完成
- [ ] 位元穩定性分析出爐
- [ ] 3+ 個 GitHub Modeling Attack 工具評估完成

### Week 3 (April 19-25) — 對抗實驗週
- [ ] Modeling Attack 無防禦版完成（accuracy 記錄）
- [ ] VRF 防禦驗證框架設計完成
- [ ] 防禦前後對比圖表生成
- [ ] 論文框架初稿完成

### Week 4 (April 26 - May 2) — 論文衝刺週
- [ ] 論文初稿（3000+ 字）完成
- [ ] 所有圖表嵌入論文
- [ ] 創新點清晰陳述
- [ ] 老師評閱準備完成

---

## 💡 重點提醒

### 實作分支的核心檢查項
- 不要在還沒確認 app.py 能跑的情況下，提交「架構設計報告」
- batch_test.py 的統計數據是論文的底層支撐，要確保準確
- ROC / EER 圖表必須來自真實的驗證結果，不能造假或手繪

### 研究分支的核心檢查項
- 不要直接引用論文的結論而不自己驗證（例如：論文說 BER 3-5%，你要在 crps.csv 上確認）
- Modeling Attack 的對比必須公平（相同的 train/test split、相同的 ML 模型參數）
- 創新點必須明確：你做了什麼別人沒做的

### 兩個分支協作的注意事項
- 不要等到最後才整合（導致時間倉促）
- 每週末開一個同步會，確保兩線進度協調
- 實作遇到的問題（例如 MQTT 延遲高），可能影響論文的「系統效能」章節

---

## 🎯 最終成果物清單

### 實作分支交付物
- ✅ 可完整運行的 app.py / node.py / mqtt_bridge.py
- ✅ roc_eer_plot.png（ ROC 曲線與 EER 標記）
- ✅ latency_breakdown.png（延遲分析）
- ✅ hd_distribution.png（Hamming Distance 分佈）
- ✅ batch_test_report.json（統計數據）
- ✅ SQLite 審計日誌（完整追蹤）

### 研究分支交付物
- ✅ 論文初稿（4000+ 字）
- ✅ crps_statistical_analysis.json（數據特徵）
- ✅ bit_stability_heatmap.png（位元稳定性分析）
- ✅ modeling_attack_no_defense.json + 圖表（對抗實驗）
- ✅ EXPERIMENT_DESIGN_MODELING_ATTACK.md（方法論文檔）
- ✅ INNOVATION_COMPARISON.md（創新點對標表）

---

**準備好分別進行了嗎？** 開始分工，讓專題的質量與深度同步提升！ 🚀
