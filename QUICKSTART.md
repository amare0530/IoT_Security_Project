# 🚀 快速開始指南

## 一分鐘快速上手

### 第一步：安裝依賴
```bash
pip install -r requirements.txt
```

### 第二步：啟動伺服器（終端 1）
```bash
streamlit run app.py
```
自動在 `http://localhost:8501` 開啟網頁

### 第三步：啟動 Node 設備（終端 2）
```bash
python node.py
```
看到「等待伺服器發送挑戰」即表示成功連線

### 第四步：開始認證流程

在 Streamlit 網頁上按照順序點擊：

1. **「生成新挑戰碼」** 
   - 伺服器使用 VRF 生成隨機 Challenge

2. **「發送至 Node 端」**
   - Challenge 透過 MQTT 發送到 Node 設備

3. **「檢查並驗證 Response」**
   - Node 回傳 Response，伺服器自動驗證
   - 顯示漢明距離和認證結果

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
**A:** 確保 `node.py` 正在運行，檢查終端是否有錯誤訊息

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
