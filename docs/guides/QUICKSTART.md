# 🚀 快速開始指南

### 第一步：建立虛擬環境

python -m venv .venv
```

### 第二步：安裝依賴
```bash
./.venv/Scripts/python.exe -m pip install -r requirements.txt
不使用 PowerShell 腳本，避免不同電腦 shell/路徑差異造成啟動失敗。

### 第三步：啟動伺服器（終端 1）
```bash
./.venv/Scripts/python.exe -m streamlit run app.py
```

### 第二步：啟動伺服器（終端 1）
### 第四步：啟動 Node 設備（終端 2）
python -m streamlit run app.py
./.venv/Scripts/python.exe node.py
自動在 `http://localhost:8501` 開啟網頁

### 第三步：啟動 Node 設備（終端 2）
### 第五步：啟動 Bridge（終端 3）
python node.py
./.venv/Scripts/python.exe mqtt_bridge.py
看到「等待伺服器發送挑戰」即表示成功連線

### 第四步：啟動 Bridge（終端 3）
### 第六步：開始認證流程
python mqtt_bridge.py
```
看到「MQTT 背景監聽已啟動」與連線成功訊息即表示可開始傳輸

### 停止方式
- 在三個終端機分別按 `Ctrl + C`。
- 若 `http://localhost:8501` 開不起來，先確認是否有舊 Streamlit 程序占用 8501。

### 第五步：開始認證流程

在 Streamlit 網頁上按照順序點擊：

1. **「🚀 一鍵驗證」**（推薦）
  - 自動執行：生成 Challenge → 發送至 Node → 等待回應 → 驗證
  - 完成後直接顯示漢明距離與認證結果

2. **分步操作**（進階）
  - 「1. 生成 Challenge」
  - 「2. 發送 Challenge」
  - 「3. 驗證最新回應」

---

## 執行實驗

### 單次測試
1. 調整「容錯門檻」(Threshold)
2. 調整「雜訊等級」(Noise Level)  
3. 點擊「模擬一次 PUF 出力」
4. 觀察是否認證通過

### 100 次批量實驗
1. 在第四階段調整「實驗雜訊等級」和「實驗容錯門檻」
2. 點擊「執行 100 次自動化實驗」
3. 查看 FRR (False Rejection Rate) 結果
4. 下載 CSV 檔案用於論文分析

---

## 常見問題

### Q: Node 無法連線？
**A:** 檢查網路連線，確認 `broker.emqx.io` 可用

### Q: 收不到 Response？
**A:** 依序確認：
1. `node.py` 正在執行
2. `mqtt_bridge.py` 正在執行
3. Streamlit 頁面中的 Bridge 狀態顯示正常
4. 發送 Challenge 後等待 3-5 秒再檢查

### Q: 想用本地 Broker？
**A:** 編輯 `app.py` 和 `node.py` 中的：
```python
client.connect("localhost", 1883, 60)
```

### Q: 如何匯出實驗結果？
**A:** 實驗完成後，在結果區塊點擊「📥 下載為 CSV 檔案」

---

## 進階設定

### 修改 VRF 私鑰
在側邊欄「伺服器私鑰」欄位修改（預設：`FU_JEN_CSIE_SECRET_2026`）

### 修改雜訊模式
編輯 `node.py` 中的 `simulate_puf_response()` 函數

### 切換 MQTT Broker
編輯 `config.py` 中的 `MQTT_CONFIG`

---

## 系統流程圖

```
Start
  ↓
[生成 Challenge]  ← VRF
  ↓
[發送到 Node]  ← MQTT
  ↓
[Node 接收]
  ↓
[模擬 PUF + 注入雜訊]
  ↓
[產生 Response]
  ↓
[透過 MQTT 回傳]
  ↓
[Server 接收 Response]
  ↓
[計算漢明距離]
  ↓
[距離 ≤ 門檻?]
  ├─ Yes → ✅ 認證通過
  └─ No  → ❌ 認證失敗
```

---

## 下一步

- 📖 閱讀 [完整 README](README.md)
- 🔍 瀏覽[程式碼註解](app.py)
- 📊 分析[實驗結果](results/)
- 🎓 參考[技術文檔](docs/)

---

**有問題？** 查看 README.md 或提交 GitHub Issue
