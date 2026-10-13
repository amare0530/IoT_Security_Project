# 展示 Demo 操作指南

## 離線命令列 Demo

在簡報或影片前執行：

```powershell
python scripts/run_offline_demo.py --output-dir demo-output
```

這個流程會展示合成 SRAM 回應、穩定位元選擇、模糊提取器重建、HMAC
挑戰回應、成功認證與重放攻擊拒絕。不需要私有資料、公開 broker 或實體硬體。

## 瀏覽器展示頁面

最簡單的方法是雙擊專案根目錄的 `start_web_demo.bat`。也可以執行：

```powershell
python scripts/run_web_demo.py
```

瀏覽器通常會自動開啟 `http://127.0.0.1:8765`。若沒有自動開啟，請手動輸入網址。
頁面會展示：

- 註冊階段與穩定位元數量
- 模糊提取器 Gen / Rep 金鑰重建
- HMAC-SHA256 認證成功
- 重放攻擊拒絕
- 未知裝置拒絕

若要讓同一網路上的其他電腦開啟頁面，可以執行：

```powershell
python scripts/run_web_demo.py --host 0.0.0.0
```

再用執行展示程式電腦的區域網路 IP 加上 `:8765` 開啟。一般展示優先使用
`127.0.0.1`，避免依賴網路。

## MQTT 展示

可以使用本機 MQTT broker，再啟動 `mqtt/server.py` 與 `mqtt/device.py`，並使用
fixture registry 或明確指定的測試 key。請使用唯一的 topic。這個實作目前驗證
MQTT 協議流程，但不宣稱已在微控制器上即時取樣 SRAM 或執行 `Rep()`。

## 必須使用的說法

請使用：**以資料集為基礎的 system-level SRAM-PUF 認證原型**。

請不要宣稱：已完成 live hardware key reconstruction、helper data 完全零洩漏，
或 Inter-HD 已達理想的 0.5。

`demo_result.json` 只包含一次性展示用輔助資料，不是 production key store。

## Identity Lab 展示版

成果展建議使用新版 Identity Lab：

```powershell
python scripts/run_identity_lab.py
```

頁面提供「展示模式」、「實驗室模式」與「攻擊模式」。展示模式會依序播放
Device boot、SRAM、stability、fuzzy extractor、HMAC、MQTT、server verify
與攻擊阻擋。攻擊模式的 replay、竄改 HMAC、未知 UID、未來 timestamp 和錯誤
payload 會實際呼叫 Python 驗證邏輯。

若本機有 `data/crps.csv`，可使用：

```powershell
python scripts/run_identity_lab.py --auto-local-data
```

程式會在程序內快取已載入的資料矩陣，之後隨機選擇合法 UID，不會每次按鈕都重新
讀取大型 CSV。沒有資料集時則使用合成 fixture。
