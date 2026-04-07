##  MQTT 無回應修復指南（Bridge 架構）

本專案目前採用三程序架構：
1. Streamlit 伺服器：app.py
2. Node 設備：node.py
3. MQTT Bridge：mqtt_bridge.py

若只啟動 app.py 與 node.py，Bridge 未啟動時會出現「測試可過、實際沒反應」的情況。

---

##  已修復項目

### 1. Bridge 連線穩定性
- 新增連線失敗重試機制（固定間隔重試）。
- 新增斷線狀態回報與重連流程。
- 保留 QoS=1，降低訊息遺失機率。

### 2. Bridge 心跳監控
- 新增 bridge_status.json 心跳檔。
- app.py 可即時顯示 Bridge 是否存活、是否已連上 Broker。

### 2.1 單實例保護
- mqtt_bridge.py 現在會拒絕重複啟動，避免多個 Bridge 同時寫入相同 IPC 檔案。
- node.py 也加入單實例保護，避免多個 Node 同時回傳造成 Response 混淆。
- 若啟動時出現「偵測到另一個已在執行」訊息，請先關閉重複視窗再重新啟動。

### 3. app.py 回應等待機制
- 將單次檢查改為限時輪詢（預設 15 秒）。
- 避免因非同步時序造成「提早判定失敗」。

### 4. 診斷訊息強化
- 顯示未收到 Response 的分流原因：
  - Node 未執行
  - Bridge 未啟動或中斷
  - 回應超時

---

##  正確啟動順序

請開三個終端機：

### 終端機 1：啟動 Node
```bash
python node.py
```

### 終端機 2：啟動 Bridge
```bash
python mqtt_bridge.py
```

### 終端機 3：啟動 Streamlit
```bash
streamlit run app.py
```

---

##  建議驗證流程

1. 在 UI 點擊「生成新挑戰碼」。
2. 點擊「發送至 Node 端」。
3. 觀察 Bridge 終端是否顯示「已透過 MQTT 成功發送」。
4. 等待 3 到 5 秒後點擊「檢查並驗證」。
5. 若正常，應看到漢明距離與認證結果。

### 不用腳本的手動驗證

1. 啟動一個 `node.py`。
2. 啟動一個 `mqtt_bridge.py`。
3. 啟動 `app.py` 後，先確認首頁的 Bridge 心跳與最近 Response 狀態。
4. 使用側邊欄的「手動驗證（免腳本）」區塊直接做健康檢查。
5. 再按「 一鍵驗證」做一次完整流程。

---

##  快速排查

### 情境 A：UI 顯示尚未收到 Response
請依序檢查：
1. node.py 是否仍在執行。
2. mqtt_bridge.py 是否仍在執行。
3. UI 的 Bridge 狀態是否為正常。
4. Bridge 終端是否有收到 response 主題訊息。

### 情境 B：Bridge 連不上 Broker
1. 先確認網路連線。
2. 測試 broker.emqx.io 是否可達。
3. 如學校網路封鎖 1883，改用可用 Broker 或本機 Broker。

### 情境 C：測試腳本可過，但 UI 仍偶發超時
1. 確認 Challenge 發送後有等待至少 3 秒。
2. 重新啟動三個程序，清掉舊連線狀態。
3. 檢查 bridge_status.json 的 last_seen 是否持續更新。

---

##  架構說明（目前版本）

資料流：
1. app.py 寫入 challenge_out.json
2. mqtt_bridge.py 讀取 challenge_out.json 並發送 MQTT
3. node.py 訂閱 challenge、回傳 response
4. mqtt_bridge.py 接收 response 後寫入 response_in.json
5. app.py 輪詢 response_in.json 並驗證

這代表 Bridge 是必要程序，不可省略。

---

##  後續重構建議

若要完全消除檔案輪詢時序問題，可進行第二階段重構：
1. app.py 改為直接 MQTT publish/subscribe。
2. 將 mqtt_bridge.py 降級為相容模式或退役。

目前版本先以穩定可運行為優先，確保展示與實驗流程可重現。

---

##  最近更新（2026-04-06）

- 已將 Bridge 與 Node 的重複啟動風險納入說明。
- 已新增 UI 內建手動驗證流程，方便不使用外部腳本時仍可檢查系統健康狀態。
- 已補上建議操作順序：先單一 Node、單一 Bridge，再開 app.py。




