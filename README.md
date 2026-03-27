# 🔒 IoT 硬體指紋認證系統 (IoT Security Authentication System)

## 📋 專案概述

這是一個基於 **VRF (可驗證隨機函數)** 與 **PUF (物理上不可複製函數)** 的硬體指紋認證系統。

### 核心特點
- 🎯 **VRF 挑戰生成**: 確保挑戰的隨機性與不可預測性
- 🔧 **PUF 模擬**: 軟體模擬物理特徵提取過程
- 📐 **漢明距離驗證**: 容錯機制處理硬體雜訊
- 📊 **FRR/FAR 分析**: 數據化安全性 Trade-off
- 🌐 **MQTT 閉環**: 伺服器-設備自動化通訊

---

## 🏗️ 系統架構

### 資料流圖

```
系統工作流程：

Challenge (C) ← VRF 生成
    ↓
    └──→ [MQTT Send] → Node Device
         
         在 Node 端：
         Challenge → [PUF Simulation] → Add Noise → Response (R)
         
    ↓
    └──← [MQTT Receive] ← Response with Noise
    
    ↓
    Server 驗證：
    Hamming Distance(C, R) ≤ Threshold?
         ✅ YES → 認證通過 (合法設備)
         ❌ NO  → 認證失敗 (非法設備或雜訊過大)
```

---

## 🚀 快速開始

### 前置需求

```bash
# Python 3.8+
pip install streamlit paho-mqtt pandas
```

### 執行方式

**終端機 1 - 啟動伺服器**
```bash
streamlit run app.py
```

**終端機 2 - 啟動設備節點**
```bash
python node.py
```

### 使用流程

1. 點擊「生成新挑戰碼」生成 VRF Challenge
2. 點擊「發送至 Node 端」透過 MQTT 傳送
3. Node 自動接收、模擬 PUF、回傳 Response
4. 點擊「檢查並驗證」查看漢明距離與認證結果
5. （可選）點擊「執行 100 次實驗」進行 FRR 分析

---

## 📄 檔案說明

### `app.py` - 伺服器端 (Streamlit)
- VRF Challenge 生成與發送
- MQTT 背景監聽 (接收 Response)
- 漢明距離計算與認證
- 100 次批量實驗 & FRR 統計

### `node.py` - 設備節點
- MQTT 訂閱 Challenge
- PUF 模擬 (軟體版本)
- 硬體雜訊注入
- MQTT 回傳 Response

### `vrf_run.py` - VRF 核心邏輯
- 獨立測試 VRF 功能
- 驗證確定性、不可預測性、可驗證性

---

## 🧪 實驗功能

### 批量 FRR 實驗

在 Streamlit 介面執行 100 次自動化測試：

1. **設置參數**
   - 雜訊等級 (0-20 bits)
   - 容錯門檻 (0-256)

2. **執行測試**
   - 產生 100 次獨立的帶雜訊 Response
   - 計算每次的漢明距離
   - 統計通過/失敗次數

3. **分析結果**
   - **FRR** = (失敗次數 / 100) × 100%
   - 可視化圖表
   - 匯出 CSV 數據

### 結果解釋

| FRR 範圍 | 評估 | 建議 |
|---------|------|------|
| < 5% | ✅ 優秀 | 可用於生產環境 |
| 5-10% | ⚠️ 適中 | 可考慮參數優化 |
| > 10% | ❌ 需改進 | 調整雜訊/門檻參數 |

---

## 🔐 安全性特性

### VRF 的三大特性

1. **確定性 (Deterministic)**
   - 相同輸入產出相同輸出
   - 利用 HMAC-SHA256 實現

2. **不可預測性 (Unpredictable)**
   - 無私鑰無法預測下一挑戰
   - 確保攻擊者無法提前準備

3. **可驗證性 (Verifiable)**
   - 用 Proof 驗證挑戰的真偽
   - 防止偽造挑戰

### 容錯 Trade-off

```
安全性 vs 易用性：
- 提高門檻值 → FRR ↓, FAR ↑ (更易用，安全性降低)
- 降低門檻值 → FRR ↑, FAR ↓ (更安全，易用性降低)
- 最佳平衡點：FRR < 5%, FAR < 2%
```

---

## 📊 可視化與數據匯出

- **折線圖**: 漢明距離分布
- **長條圖**: 認證成功/失敗比例
- **指標卡**: 關鍵統計數據
- **CSV 匯出**: 用於論文分析

---

## 🛠️ 進階設定

### 更改 MQTT Broker

編輯 `app.py` 和 `node.py`：

```python
# 預設 (公開演示)
client.connect("broker.emqx.io", 1883, 60)

# 本地 Broker
client.connect("localhost", 1883, 60)
```

### 修改 VRF 私鑰

在 `app.py` 側邊欄設定：

```python
sk = st.text_input("伺服器私鑰", value="YOUR_SECRET_KEY")
```

---

## 🎓 指導教授建議實踐

本專案根據指導教授 **Dolin** 的建議實現：

✅ **容錯機制深度** - 完整的 FRR/FAR 分析  
✅ **系統完整性** - MQTT 雙向閉環自動化  
✅ **數據化驗證** - 100 次批量實驗與統計  
✅ **程式文件** - 詳細的中文註解與架構說明  

---

## 📚 技術棧

- **Backend**: Python 3.8+
- **Frontend**: Streamlit
- **通訊協議**: MQTT (broker.emqx.io)
- **密碼學**: HMAC-SHA256, Hamming Distance
- **資料處理**: Pandas
- **圖表**: Streamlit Chart

---

## 聯繫方式

**GitHub**: [amare0530/IoT_Security_Project](https://github.com/amare0530/IoT_Security_Project)

---

## 📄 許可證

MIT License

---

<div align="center">

**🔒 IoT 硬體指紋認證系統**

*基於 VRF + PUF + Hamming Distance 的安全認證平台*

</div>
