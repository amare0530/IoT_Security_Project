# WASN 2026 Paper Draft - Bilingual Companion

This file follows the revised English draft in `docs/WASN2026_PAPER_DRAFT.md`.

Use it for checking meaning, discussing with teammates, and preparing answers for the advisor. The final submitted paper can still be English-only.

---

## Title / 題目

### English

A Reliability-Aware SRAM PUF and HMAC Authentication Pipeline for Resource-Constrained IoT Devices

### 中文理解

一套面向資源受限物聯網設備、結合可靠度感知 SRAM PUF 與 HMAC 的認證流程

---

## Abstract / 摘要

### English

IoT edge devices deployed in unattended environments face a practical risk: authentication credentials stored in flash memory may be extracted if an attacker gains physical access to the device. This paper presents a reliability-aware authentication pipeline that uses SRAM startup behavior to reconstruct device-specific key material instead of relying only on persistent key storage. The system operates in two phases. During offline enrollment, repeated SRAM startup responses from each device are analyzed to identify stable bit positions, generate a device-specific mask, and produce a PUF-assisted key record through a fuzzy extractor. During online authentication, the device uses the reconstructed or registered PUF-derived key to compute an HMAC-SHA256 response for an MQTT challenge containing a nonce and timestamp. Experiments on a dataset of 84 devices show an average bit stability of 0.9697, with at least 513,910 stable bits available per device at the 0.90 threshold. The fuzzy extractor achieves 100% key reconstruction in the no-noise setting and 99.864% average success under random 5% bit-error simulation across 81 devices. An MQTT prototype validates end-to-end authentication using keys generated from the dataset artifacts. The current implementation is a system-level prototype; live SRAM sampling on physical hardware and helper-data leakage analysis remain future work.

### 中文理解

部署在無人看管環境中的 IoT 邊緣設備有一個實際風險：如果攻擊者取得設備實體存取權，儲存在 flash memory 中的認證憑證可能被提取。本文提出一套可靠度感知認證流程，利用 SRAM 開機行為重建設備專屬金鑰材料，而不是只依賴永久儲存的金鑰。系統分成兩個階段。離線註冊階段會分析每台設備多次 SRAM 開機回應，找出穩定位元、產生設備專屬 mask，並透過 fuzzy extractor 產生 PUF-assisted key record。線上認證階段中，設備使用重建或註冊後的 PUF-derived key，針對包含 nonce 與 timestamp 的 MQTT challenge 計算 HMAC-SHA256 response。實驗資料包含 84 台設備，平均 bit stability 為 0.9697，在 0.90 門檻下每台設備至少有 513,910 個穩定位元。Fuzzy extractor 在無雜訊設定下達到 100% key reconstruction，在 81 台設備的隨機 5% bit-error simulation 中平均成功率為 99.864%。MQTT prototype 使用 dataset artifacts 產生的 key 驗證了端到端認證。現在的實作是 system-level prototype；實體硬體上的 live SRAM sampling 與 helper-data leakage analysis 是未來工作。

---

## Keywords / 關鍵詞

### English

SRAM PUF, Fuzzy Extractor, HMAC-SHA256, MQTT, IoT Authentication

### 中文理解

SRAM PUF、模糊提取器、HMAC-SHA256、MQTT、物聯網認證

---

## Core Logic / 核心因果鏈

### English

The pipeline should be understood as:

```text
SRAM dataset -> bit stability -> stable-bit mask -> fuzzy extractor -> PUF-derived key registry -> MQTT HMAC authentication
```

### 中文理解

整個專題的因果鏈應該這樣理解：

```text
SRAM 資料集 -> bit 穩定度分析 -> 穩定位元 mask -> fuzzy extractor -> PUF-derived key registry -> MQTT HMAC 認證
```

這很重要，因為論文不能寫成「我們只是 HMAC demo」，也不能寫成「我們已經完成真實 ESP32 live SRAM 取樣」。目前最準確的說法是：你們完成了從 SRAM PUF dataset artifacts 到 MQTT authentication 的 system-level prototype。

---

## I. Introduction / 緒論重點

### English Paper Meaning

The Introduction says that IoT devices may be physically exposed, so storing long-term keys directly in flash memory can be risky. SRAM PUFs offer a hardware-rooted identity source, but raw SRAM responses are noisy. Therefore, the project uses reliability-aware preprocessing and fuzzy extraction before using the key in MQTT authentication.

### 中文理解

緒論的意思是：IoT 設備可能放在外面或無人看管，所以如果長期金鑰直接放在 flash memory，會有被提取的風險。SRAM PUF 可以提供硬體指紋，但原始 SRAM 回應會有雜訊，不能直接拿來當穩定金鑰。因此，這個專題先做可靠度感知前處理與 fuzzy extraction，再把得到的 key 用於 MQTT 認證。

### Safer Chinese Explanation For Oral Defense

我們不是單純做加密，也不是宣稱 SRAM PUF 原始資料完美不可複製。我們的重點是把有雜訊的 SRAM PUF 資料，透過穩定位元挑選與 fuzzy extractor 轉成可以用於認證的 key material，最後接到 MQTT challenge-response 流程中驗證設備身份。

---

## II. Proposed Architecture / 系統架構重點

### English Paper Meaning

The architecture separates offline enrollment from online authentication. Offline enrollment performs the heavy work: converting dataset rows into bitstreams, calculating stability, selecting stable positions, and running fuzzy extractor enrollment. Online authentication is lightweight: the server sends `{UID, nonce, timestamp}`, and the device returns an HMAC tag.

### 中文理解

系統架構分成離線註冊與線上認證。離線註冊負責比較重的工作：把 dataset rows 轉成 bitstreams、計算 stability、挑選 stable positions，並執行 fuzzy extractor enrollment。線上認證則保持輕量：server 送 `{UID, nonce, timestamp}`，device 回傳 HMAC tag。

### Important Detail / 重要細節

### English

The fuzzy extractor does not simply hash raw SRAM bits into a key. It uses a code-offset style construction: enrollment generates key bits, repeats them, computes helper data with `W = C XOR R`, and later reconstructs the same key through XOR and majority voting.

### 中文理解

fuzzy extractor 不是直接把 raw SRAM bits hash 成 key。它比較像 code-offset / secure sketch 流程：註冊時產生 key bits，將 key bits 重複展開後，和穩定 SRAM response `R` 做 XOR 得到 helper data `W = C XOR R`；之後重建時用新的 response 與 helper data 還原 encoded key bits，再透過 majority voting 得到同一把 key。

這個細節很重要，因為如果論文寫成「key 直接從 SRAM bits 產生」，會不夠精準。

---

## III. System Implementation / 系統實作重點

### English Paper Meaning

The implementation is split across repository modules:

- `analysis/stability_analysis.py`: dataset loading, bitstream conversion, per-bit stability, masks, holdout BER.
- `puf/bit_selection.py`: threshold-based stable-bit selection.
- `puf/fuzzy_extractor.py`: repeated key-bit encoding, helper data, majority-vote reconstruction, Monte Carlo BER simulation.
- `puf/key_provider.py`: loads generated key registry for integration testing.
- `auth/hmac_auth.py`: nonce/timestamp challenge, HMAC-SHA256, nonce cache, constant-time comparison.
- `mqtt/server.py` and `mqtt/device.py`: MQTT challenge-response over configured topics.

### 中文理解

實作分散在幾個 module：

- `analysis/stability_analysis.py`：讀取資料集、轉 bitstream、計算 bit stability、產生 masks、估計 holdout BER。
- `puf/bit_selection.py`：用 threshold 挑穩定位元。
- `puf/fuzzy_extractor.py`：實作 repeated key-bit encoding、helper data、majority-vote reconstruction，以及 BER Monte Carlo simulation。
- `puf/key_provider.py`：讀取產生好的 key registry，用於 integration testing。
- `auth/hmac_auth.py`：產生 nonce/timestamp challenge、HMAC-SHA256、nonce cache、constant-time comparison。
- `mqtt/server.py` 和 `mqtt/device.py`：透過 MQTT topic 做 challenge-response。

### Implementation Boundary / 實作邊界

### English

The current Step 6 integration test uses a PUF-derived key registry generated from fuzzy-extractor outputs. It validates the complete MQTT authentication loop, but it does not yet perform live SRAM sampling on physical hardware.

### 中文理解

目前 Step 6 integration test 使用 fuzzy extractor 輸出產生的 PUF-derived key registry。它驗證了完整 MQTT authentication loop，但還沒有在實體硬體上做 live SRAM sampling。

這句一定要講清楚，因為這是老師或 reviewer 很可能問的地方。

---

## IV. Security Analysis / 安全性分析重點

### English Paper Meaning

The system supports authentication and integrity. Replay attacks are addressed by timestamp and nonce cache. Tampering and simple impersonation are addressed by HMAC verification. Physical key extraction risk is reduced in the intended design, but the current prototype still uses a key registry. Payload confidentiality is not provided by HMAC.

### 中文理解

系統提供的是認證與完整性。Replay attack 透過 timestamp 與 nonce cache 防護。訊息竄改與簡單冒用透過 HMAC verification 防護。設計目標上可以降低固定金鑰被提取的風險，但目前 prototype 還是使用 key registry。HMAC 不提供 payload confidentiality。

### Safe Wording / 安全寫法

### English

This work focuses on device authentication and message integrity, not payload confidentiality.

### 中文理解

本文聚焦在設備認證與訊息完整性，不是 payload 加密或資料保密。

### English

The current prototype validates the software pipeline; live SRAM sampling and on-device reconstruction are left for future hardware deployment.

### 中文理解

目前 prototype 驗證的是軟體流程；live SRAM sampling 與 device-side reconstruction 留待未來硬體部署。

---

## V. Evaluation / 實驗評估重點

### English Results

| Metric | Result |
| --- | ---: |
| Devices in stability summary | 84 |
| Bits per device | 655,360 |
| Mean bit stability | 0.9697 |
| Minimum mean bit stability | 0.9473 |
| Mean selected bits at threshold 0.90 | 574,655 |
| Minimum selected bits at threshold 0.90 | 513,910 |
| Devices processed by fuzzy extractor | 81 |
| Stable bits consumed per device | 2,816 |
| No-noise reconstruction success | 100.0% |
| Random 5% BER mean success | 99.864% |
| Random 5% BER minimum success | 98.0% |

### 中文理解

這張表的意思是：資料集穩定位元數量充足，fuzzy extractor 在目前設定下能可靠重建 key。這支撐的是「pipeline 可行」，不是「SRAM PUF 完美」。

### Inter-HD Results

| Metric | Result |
| --- | ---: |
| Pairwise comparisons | 6,480 |
| Mean Inter-HD | 0.2703 |
| Minimum Inter-HD | 0.0160 |
| Maximum Inter-HD | 0.3726 |
| Standard deviation | 0.0567 |

### 中文理解

Inter-HD 平均 0.2703，低於理想的 0.5。這不能藏起來，也不能硬說很好。比較好的說法是：資料集有 bias，所以不能直接依賴 raw SRAM responses；這也合理化我們使用 preprocessing + fuzzy extractor + HMAC pipeline。

---

## VI. Conclusion / 結論重點

### English Paper Meaning

The conclusion should say that the project validates a practical pipeline from SRAM PUF dataset analysis to MQTT-based HMAC authentication. It should also clearly state future work: live SRAM sampling, microcontroller latency measurement, and helper-data leakage analysis.

### 中文理解

結論要說：這個專題驗證了從 SRAM PUF dataset analysis 到 MQTT HMAC authentication 的可行流程。同時要誠實說明未來工作：live SRAM sampling、microcontroller latency measurement、helper-data leakage analysis。

---

## Things Not To Overclaim / 不要過度宣稱

### English

Do not claim:

- perfect security
- zero helper-data leakage
- ideal PUF uniqueness
- completed ESP32 runtime SRAM extraction
- payload encryption
- full end-to-end confidentiality

### 中文理解

不要宣稱：

- 完美安全
- helper data 完全零洩漏
- PUF uniqueness 很理想
- 已完成 ESP32 runtime SRAM extraction
- 有做 payload encryption
- 有完整端到端資料保密

---

## Best One-Sentence Explanation / 最好用的一句話

### English

This project validates a reliability-aware authentication pipeline that converts noisy SRAM PUF dataset measurements into reconstructable key material and uses it for MQTT-based HMAC device authentication.

### 中文理解

這個專題驗證了一套可靠度感知認證流程：把有雜訊的 SRAM PUF 資料集量測結果轉成可重建的 key material，並用於基於 MQTT 的 HMAC 設備認證。
