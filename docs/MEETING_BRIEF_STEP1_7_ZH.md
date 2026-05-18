# SRAM PUF IoT 認證系統 — Meeting 進度報告

## 1. 一句話定位

這個專題不只是加密程式。  
我們建立的是一套「低成本 IoT 設備身份認證流程」：

```text
SRAM PUF 硬體指紋
-> 穩定位元前處理
-> Fuzzy Extractor 重建穩定金鑰
-> HMAC-SHA256 產生認證碼
-> MQTT 完成 Challenge-Response 認證
```

核心概念是：

> 不把固定金鑰存在 flash 裡，而是利用 SRAM PUF 從硬體本身重建裝置金鑰，再用這把金鑰做 IoT device authentication。

## 2. 目前進度

| 步驟 | 模組 | 狀態 | 證據 |
| --- | --- | --- | --- |
| Step 1 | Dataset Analysis | 完成 | `artifacts/device_summary.csv` |
| Step 2 | Stable-Bit Mask | 完成 | `artifacts/masks.json`, `artifacts/threshold_comparison.csv` |
| Step 3 | Fuzzy Extractor | 完成 | `artifacts/fuzzy_extractor_results.csv` |
| Step 4 | HMAC Authentication | 完成 | `tests/test_hmac_auth.py`, replay attack tests |
| Step 5 | MQTT Communication | 完成 | HiveMQ 公開 broker 實測通過 |
| Step 6 | System Integration | 完成，prototype implementation | `artifacts/mqtt_server_step6.out.log` |
| Step 7 | Experiment Evaluation | 進行中 | 需補論文圖表 |

Step 6 的精確說法：

> 目前完成的是 prototype implementation。MQTT server/device 已經使用 Step 3 產出的 PUF-derived key registry，不再使用寫死的假金鑰。這驗證了完整端對端認證協議。真實部署時，device 端會在開機時讀取 SRAM response，執行 Fuzzy Extractor `Rep()` 即時重建金鑰。

## 3. 目前的關鍵數據

### 資料集摘要

| 指標 | 結果 |
| --- | ---: |
| 裝置數量 | 84 台 |
| 每台裝置位元數 | 655,360 bits |
| 平均穩定度 | 0.9697 |
| 平均可用位元數，stability >= 0.90 | 574,655 bits |
| 最少可用位元數，stability >= 0.90 | 513,910 bits |

### Fuzzy Extractor 結果

| 指標 | 結果 |
| --- | ---: |
| 成功處理裝置數 | 81 台 |
| 每台消耗穩定位元數 | 2,816 bits |
| 無雜訊重建成功率 | 100.0% |
| 可校正 5% BER 重建成功率 | 100.0% |
| 純隨機 5% BER Monte Carlo 平均成功率 | 99.864% |
| 純隨機 5% BER Monte Carlo 最低成功率 | 98.0% |

### 唯一性，Inter-HD

| 指標 | 結果 |
| --- | ---: |
| 裝置對數 | 6,480 對 |
| 平均 Inter-HD | 0.2703 |
| 最小 Inter-HD | 0.0160 |
| 最大 Inter-HD | 0.3726 |
| 標準差 | 0.0567 |

重要說法：

> 理想 PUF 的 Inter-HD 會接近 0.5。我們目前觀察到的平均值是 0.2703，低於理想值，表示這份 SRAM dataset 存在 0/1 bit bias。這不是要隱藏的缺陷，而是本研究的動機：原始 SRAM PUF 並不完美，因此需要 stable-bit preprocessing、Fuzzy Extractor 與 HMAC 管線，將有偏誤且有雜訊的硬體 response 轉成可用的 authentication key material。

## 4. Meeting 展示方式

### 可展示的檔案

| 檔案 | 用途 |
| --- | --- |
| `artifacts/device_summary.csv` | 展示 84 台裝置穩定度統計 |
| `artifacts/threshold_comparison.csv` | 展示 threshold / BER 實驗，但目前需謹慎解釋 |
| `artifacts/fuzzy_extractor_results.csv` | 展示 FE 重建、5% BER、key uniqueness |
| `artifacts/inter_hd.csv` | 展示裝置間唯一性數據 |
| `artifacts/inter_hd_dist.png` | 展示 Inter-HD 分布圖 |
| `artifacts/mqtt_server_step6.out.log` | 展示 MQTT 端對端認證成功 |

### Demo 指令

先開 server：

```powershell
python mqtt/server.py --broker broker.hivemq.com --port 1883 --uid 3038470130373036003B0034 --key-registry artifacts/fuzzy_extractor_results.csv --challenge-topic iot/auth/challenge/amare0530_step6 --response-topic iot/auth/response/amare0530_step6 --challenge-interval 3
```

再開 device：

```powershell
python mqtt/device.py --broker broker.hivemq.com --port 1883 --uid 3038470130373036003B0034 --key-registry artifacts/fuzzy_extractor_results.csv --challenge-topic iot/auth/challenge/amare0530_step6 --response-topic iot/auth/response/amare0530_step6
```

預期看到：

```text
Authentication valid=True for uid=3038470130373036003B0034: Authentication Successful.
```

## 5. 我們的方法 vs 傳統固定金鑰 IoT

| 問題 | 傳統固定金鑰 IoT | 我們的 SRAM PUF 方案 |
| --- | --- | --- |
| 設備身份 | 金鑰存在 flash/config | 從 SRAM PUF 硬體特徵衍生 |
| 防複製能力 | 金鑰被讀出後可被複製 | 金鑰綁定 SRAM 物理行為 |
| 雜訊處理 | 通常未處理 | Stable-bit preprocessing + FE |
| Replay attack | 簡單系統常缺乏防護 | Nonce + timestamp + nonce cache |
| 通訊方式 | 固定 HMAC 或明文流程 | MQTT challenge-response HMAC |

要注意的說法：

> HMAC 提供的是 authentication 與 integrity，不是 encryption。如果要保護感測資料內容的機密性，仍需搭配 TLS 或 payload encryption。

> Helper data 可以公開是 Fuzzy Extractor 常見設計，但安全性取決於 PUF entropy、bias、helper-data leakage model 與 extractor 設計。因此不要直接說 helper data 完全零洩漏。

## 6. 老師可能問的問題與回答

### Q1. A/B/D 分級是什麼？是工具自動給的標準嗎？

不是工具固定標準，也不是教科書硬性規範。  
這是我們根據資料穩定度設計的 reliability classification。

依據是每個 bit 在多次 SRAM startup measurement 中保持 dominant value 的比例，也就是 stability score。

| 分級 | 建議定義 | 意義 |
| --- | --- | --- |
| A | stability >= 0.99 | 非常穩定，最適合用於 key reconstruction |
| B | 0.90 <= stability < 0.99 | 可用，但需要 FE / ECC 修正 |
| D | stability < 0.90 | 不穩定，丟棄 |

為什麼用 0.90？

> 0.90 是工程 trade-off。門檻太高會讓可用 bit 變少，門檻太低會增加 Fuzzy Extractor 的糾錯負擔。因此我們用 threshold sweep 觀察可用 bit 數與 BER，再選擇足夠穩定且 bit 數充足的設定。

### Q2. Adaptive Stable-Bit Preprocessing 是什麼？

這是 Step 2。  
我們對每台裝置計算每個 bit 的 stability，然後產生 per-device mask，只保留穩定 bit 再送進 Fuzzy Extractor。

叫 adaptive 的原因是：

> 每台裝置的穩定位元位置不一定相同，因此 mask 是 per-device 產生，而不是所有裝置共用同一組固定 bit 位置。

### Q3. IoT authentication 是驗證機器還是使用者？

目前是 device authentication，也就是驗證機器本身。  
我們確認 server 收到的 response 是否來自已註冊的合法 IoT device。

使用者權限是另一層：

```text
Device Authentication: 這台機器是不是真的？
User Authorization: 這個人可不可以操作它？
```

本研究先處理 device authentication。User authorization 可以作為未來 extension。

### Q4. 我們在保護什麼？

我們保護兩件事：

1. Device identity：確認設備不是偽造或複製裝置。
2. Message authenticity/integrity：確認 response 沒有被竄改或重放。

我們目前沒有宣稱 payload confidentiality。若要加密感測資料，需要再加 TLS 或 payload encryption。

### Q5. Inter-HD 為什麼不接近 0.5？

理想 PUF 的 Inter-HD 會接近 0.5。  
我們的平均 Inter-HD 是 0.2703，代表 dataset 有 SRAM bit bias。

回答方式：

> 這不是系統失敗，而是研究動機。真實 SRAM PUF 可能不是理想隨機，因此我們加入 reliability-aware preprocessing、Fuzzy Extractor 和 HMAC，讓系統在非理想資料上仍能完成穩定認證。

### Q6. Step 6 有真正從 SRAM 即時重建金鑰嗎？

目前還沒有。  
目前 Step 6 是 prototype implementation，使用 Step 3 產生的 PUF-derived key registry，模擬 device 端 FE `Rep()` 的輸出。

更精確說法：

> 在沒有實體 ESP32 SRAM response 的情況下，我們用 dataset 產出的 PUF-derived key registry 驗證整個 MQTT authentication protocol。真實部署時，device 端會在開機時讀取 SRAM response，並執行 `Rep(response, helper_data)` 即時重建 key。

### Q7. Server 到底存什麼？

目前 prototype：

```text
uid + PUF-derived key registry
```

更嚴格的未來設計：

```text
uid + mask/helper data + verifier/protected key record
```

注意：

> 不要說目前 server 只存 `masks.json`。目前 prototype 為了系統整合，server/device 都會讀取 key registry。

### Q8. 這是端對端加密嗎？

不是。  
這是端對端 authentication / integrity verification。

更精確說法：

> HMAC-SHA256 確認訊息來源與完整性，可防止偽造、竄改與 replay。但若要保護資料內容機密性，仍需加入 TLS 或 payload encryption。

### Q9. Nonce cache 會不會越來越大？

目前 `PUFAuthenticator` 有 `_prune_used_nonces()`。  
已使用 nonce 會依照 time window 清除，避免 cache 無限成長。

## 7. Step 7 還需要的圖表

目前已有：

| 圖表 / 資料 | 狀態 |
| --- | --- |
| 裝置穩定度統計表 | 已有 |
| FE 重建結果表 | 已有 |
| Inter-HD 分布圖 | 已有 |
| MQTT 認證 log | 已有 |

建議補上的圖：

| 圖表 | 用途 |
| --- | --- |
| `stability_distribution.png` | 展示 84 台裝置 mean stability 分布 |
| `selected_bits_per_device.png` | 展示每台裝置可用穩定位元數 |
| `fe_random_ber_success.png` | 展示 5% random BER 下 FE 成功率 |
| `method_comparison_table.md` | 對比 naive majority vote 4.9% 與 Code Offset 100% |

目前要小心的點：

> `threshold_comparison.csv` 目前 0.90 / 0.95 / 0.98 / 0.99 的 aggregate 結果一樣。這可能是資料穩定度分布造成，也可能是 threshold comparison 實作需要複查。Step 7 前不要把 threshold sweep 當成強 claim，建議先用 0.90 作為目前設計點，再補查原因。

## 8. 給老師的一段話

> 我們目前完成 Step 1 到 Step 6。系統從 SRAM PUF dataset analysis 出發，先計算每個 bit 的穩定度並產生 stable-bit mask，再用 Fuzzy Extractor 重建 PUF-derived key。接著，我們用 HMAC-SHA256 搭配 nonce、timestamp 與 nonce cache 防止 replay attack，最後透過 MQTT 完成 challenge-response authentication。
>
> Step 6 已經用 HiveMQ 公開 broker 完成端對端驗證，server 成功驗證 device 的 HMAC response。
>
> 目前限制是，系統整合使用 Step 3 產出的 PUF-derived key registry 來模擬 device 端的 Fuzzy Extractor `Rep()`。未來若接上實體 ESP32，device 端會改成即時讀取 SRAM response 並重建 key。
>
> 接下來 Step 7 會把目前 artifacts 整理成論文圖表，包括 stability distribution、stable bits per device、FE reliability，以及 Inter-HD distribution。

