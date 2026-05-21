# WASN 2026 Paper Draft - Bilingual Working Version

Purpose of this file:

- English paragraphs are intended for the final paper.
- Chinese paragraphs are for understanding, checking, and discussion with teammates or the advisor.
- The final submitted paper can remain English-only, while this file helps verify meaning and reduce translation mistakes.

Recommended final length: 4 to 5 pages.

---

## Title / 題目

### English

A Reliability-Aware SRAM PUF and HMAC Authentication Pipeline for Resource-Constrained IoT Devices

### 中文理解

一套面向資源受限物聯網設備、結合可靠度感知 SRAM PUF 與 HMAC 的認證流程

### Notes / 說明

這個題目強調三件事：

- reliability-aware：不是直接相信原始 SRAM PUF，而是先挑穩定位元。
- SRAM PUF and HMAC：有硬體指紋，也有實際通訊認證協定。
- resource-constrained IoT devices：符合 WASN / IoT / edge device 的範圍。

---

## Abstract / 摘要

### English

With the rapid deployment of Internet of Things (IoT) applications, edge devices are increasingly exposed to physical tampering and identity impersonation while operating under limited computational resources. Conventional authentication schemes often rely on long-term keys stored in non-volatile memory, which may be vulnerable to extraction once a device is physically accessed. This paper presents a reliability-aware lightweight authentication pipeline based on Static Random-Access Memory Physical Unclonable Functions (SRAM PUFs) and HMAC-SHA256. The proposed design separates the system into an offline enrollment phase and an online authentication phase. During enrollment, repeated SRAM startup responses are analyzed to identify stable bit positions, generate device-specific masks, and derive key material through a fuzzy extractor. During authentication, the device uses the PUF-derived key to complete an MQTT-based challenge-response protocol with nonce and timestamp protection. Experiments on an SRAM PUF dataset containing 84 devices show an average bit stability of 0.9697. The fuzzy extractor achieves 100% reconstruction success without injected noise and 99.864% average success under random 5% bit-error simulation. The MQTT prototype further validates end-to-end authentication using generated PUF-derived keys. The results suggest that combining reliability-aware preprocessing, fuzzy extraction, and lightweight message authentication is a practical direction for resource-constrained IoT device authentication, while helper-data leakage and live hardware deployment remain important future work.

### 中文理解

隨著物聯網應用快速普及，邊緣設備常部署在資源有限且容易被實體接觸的環境中，因此面臨實體竄改與身份冒用風險。傳統認證方式通常將長期金鑰存放在非揮發性記憶體中，一旦設備被攻擊者取得，金鑰可能被提取並用於複製設備身份。本文提出一套結合 SRAM PUF 與 HMAC-SHA256 的可靠度感知輕量級認證流程。系統分為離線註冊與線上認證兩階段：離線階段分析多次 SRAM 開機回應，挑選穩定位元、產生設備專屬 mask，並透過 fuzzy extractor 產生可用金鑰材料；線上階段則使用 PUF-derived key，透過 MQTT 執行帶有 nonce 與 timestamp 保護的 challenge-response 認證。實驗資料包含 84 個設備，平均 bit stability 為 0.9697；fuzzy extractor 在無注入雜訊下達到 100% 重建成功率，在隨機 5% BER 模擬下平均成功率為 99.864%。MQTT prototype 也驗證了使用 PUF-derived key 的端到端認證流程。結果顯示，可靠度感知前處理、fuzzy extraction 與輕量級訊息認證的結合，是資源受限 IoT 設備認證的一個可行方向；但 helper-data leakage 與真實硬體即時部署仍是未來工作。

### Keywords / 關鍵詞

SRAM PUF, IoT Security, HMAC-SHA256, MQTT, Device Authentication

---

## I. Introduction / 緒論

### English

The Internet of Things (IoT) has become a common infrastructure for sensing, monitoring, and automation systems. In many IoT deployments, edge devices are placed in distributed or unattended environments and communicate with servers through lightweight protocols such as MQTT [1]. This deployment model introduces a practical security problem: device credentials are often stored as long-term secrets in flash memory, configuration files, or other non-volatile storage. Once an attacker obtains physical access to a device, such stored secrets may be extracted and reused to clone the device identity or forge authentication messages.

### 中文理解

物聯網已經成為感測、監控與自動化系統中的常見基礎架構。許多 IoT 設備會部署在分散式、無人看管或容易被接觸的環境中，並透過 MQTT 這類輕量級協定與伺服器通訊。這種部署方式帶來一個實際的安全問題：設備憑證或金鑰常被長期存放在 flash、設定檔或其他非揮發性儲存空間中。一旦攻擊者取得設備實體存取權，這些秘密可能被提取，進而複製設備身份或偽造認證訊息。

### English

Physical Unclonable Functions (PUFs) provide a hardware-oriented alternative to conventional key storage. A PUF derives device-specific responses from manufacturing variations rather than from a permanently stored digital secret. SRAM PUFs are particularly attractive for low-cost IoT devices because SRAM is already available in many microcontrollers and its startup state can be used as a device fingerprint [2]. However, SRAM PUF responses are not perfectly stable. Environmental variations, aging, voltage changes, and measurement noise may introduce bit flips between repeated startups. Therefore, raw SRAM responses usually require reliability-aware preprocessing and error correction before they can be used as cryptographic key material [3], [4].

### 中文理解

PUF 提供了一種硬體導向的替代方案，不再依賴傳統的固定金鑰儲存。PUF 利用晶片製程差異產生設備專屬回應，而不是從永久保存的數位秘密取得金鑰。SRAM PUF 對低成本 IoT 設備特別有吸引力，因為許多微控制器本來就具備 SRAM，而 SRAM 開機初始狀態可作為設備指紋。不過，SRAM PUF 回應並非完全穩定；環境變化、老化、電壓波動與量測雜訊都可能造成不同次開機之間的 bit flip。因此，原始 SRAM 回應通常需要可靠度感知前處理與錯誤修正，才能作為密碼金鑰材料。

### English

This paper presents a reliability-aware SRAM PUF authentication pipeline for resource-constrained IoT devices. The proposed system moves expensive response analysis to an offline enrollment phase, where stable bit positions are selected and fuzzy-extractor helper data are generated. During online authentication, the device uses the PUF-derived key to compute an HMAC-SHA256 response [5], [6] for an MQTT challenge containing a nonce and timestamp. This design focuses on lightweight device authentication and message integrity rather than payload encryption.

### 中文理解

本文提出一套面向資源受限 IoT 設備的可靠度感知 SRAM PUF 認證流程。系統將較重的回應分析放到離線註冊階段，負責挑選穩定位元並產生 fuzzy extractor 的 helper data。線上認證時，設備使用 PUF-derived key，針對包含 nonce 與 timestamp 的 MQTT challenge 計算 HMAC-SHA256 回應。這個設計聚焦在輕量級設備認證與訊息完整性，而不是資料內容加密。

### English

The main contributions are as follows:

- A two-phase SRAM PUF authentication pipeline that separates offline reliability analysis from lightweight online authentication.
- A stable-bit selection and fuzzy-extractor workflow that converts noisy SRAM startup responses into usable PUF-derived key material.
- An MQTT-based HMAC-SHA256 challenge-response prototype with nonce and timestamp replay protection.
- An evaluation using real project artifacts, including stability analysis, fuzzy-extractor reconstruction results, inter-device Hamming distance, and end-to-end MQTT authentication logs.

### 中文理解

本文主要貢獻如下：

- 設計一套雙階段 SRAM PUF 認證流程，將離線可靠度分析與輕量級線上認證分離。
- 實作穩定位元選擇與 fuzzy extractor 流程，將有雜訊的 SRAM 開機回應轉換成可用的 PUF-derived key material。
- 實作基於 MQTT 的 HMAC-SHA256 challenge-response prototype，包含 nonce 與 timestamp replay protection。
- 使用真實專案產生的 artifacts 進行評估，包括 stability analysis、fuzzy extractor reconstruction、inter-device Hamming distance，以及端到端 MQTT authentication logs。

---

## II. Proposed Architecture / 系統架構

### English

The proposed reliability-aware authentication framework isolates heavy data modeling from real-time execution by employing a decoupled dual-phase pipeline: the offline enrollment phase and the online authentication phase. The offline phase prepares reliable PUF-derived authentication material before deployment, while the online phase performs lightweight challenge-response verification through MQTT.

### 中文理解

本系統透過雙階段架構，將較重的資料建模與即時認證執行分離：第一階段是離線註冊，第二階段是線上認證。離線階段在設備部署前準備可靠的 PUF-derived authentication material；線上階段則透過 MQTT 執行輕量級 challenge-response 驗證。

### A. Offline Enrollment Phase / 離線註冊階段

### English

The enrollment phase transforms noisy raw hardware states into stable cryptographic roots of trust before the device is deployed. First, multiple SRAM startup responses are collected from each device. Each record contains the device identifier (UID), memory address, raw response data, and a collection timestamp. The system converts the raw byte sequences into bitstreams and groups repeated measurements by device.

### 中文理解

離線註冊階段的目標，是在設備正式部署前，將有雜訊的原始硬體狀態轉換成較穩定的密碼信任根。首先，系統會針對每個設備收集多次 SRAM 開機回應。每筆資料包含設備 UID、記憶體位址、原始回應資料與收集時間。接著系統將原始 byte sequence 轉換成 bitstream，並依照設備分組整理多次量測結果。

### English

For each bit position `i`, the probabilities of observing 0 and 1 across repeated measurements are calculated. The bit stability score is defined as:

```text
S_i = max(P_i(0), P_i(1))
```

A global threshold of 0.90 is used in the current experiment. Bit positions with `S_i >= 0.90` are selected as stable cells, while unstable positions are discarded. This produces a device-specific stable-bit mask, stored as `masks.json`, which reduces the effect of environmental noise before key reconstruction.

### 中文理解

對每一個 bit 位置 `i`，系統會統計該位置在多次量測中出現 0 與 1 的機率。bit stability score 定義如下：

```text
S_i = max(P_i(0), P_i(1))
```

目前實驗採用 0.90 作為全域門檻。若某個 bit 位置滿足 `S_i >= 0.90`，就被視為穩定位元；不穩定的位置則捨棄。這個流程會產生設備專屬的 stable-bit mask，並儲存為 `masks.json`，用來在 key reconstruction 前降低環境雜訊影響。

### English

The selected stable bitstream is then processed by the fuzzy extractor. In this prototype, the fuzzy extractor uses repeated key-bit encoding and majority-vote reconstruction. During enrollment, it produces a PUF-derived key `K` and corresponding helper data. The helper data is not treated as a secret key, but its security still depends on the entropy and bias of the selected PUF bits. For the current end-to-end prototype, the generated PUF-derived keys are exported into a key registry used by the MQTT device and server programs.

### 中文理解

挑選出的穩定位元會進一步送入 fuzzy extractor。在目前 prototype 中，fuzzy extractor 使用 repeated key-bit encoding 與 majority-vote reconstruction。註冊階段會產生 PUF-derived key `K` 與對應 helper data。helper data 本身不被視為秘密金鑰，但其安全性仍然取決於被選 PUF bits 的 entropy 與 bias。為了完成目前的端到端 prototype，系統會將產生的 PUF-derived keys 匯出成 key registry，供 MQTT device 與 server 程式使用。

### Figure Placeholder

```text
[Place Figure 1 here: Overview of the proposed reliability-aware SRAM PUF enrollment and authentication pipeline architecture.]
```

### 中文提醒

Figure 1 建議放在 Section II 前半段，最好跨雙欄。圖中要有：IoT Device、SRAM PUF、Stable-bit Mask、Fuzzy Extractor、PUF-derived Key、MQTT Broker、Authentication Server、Enrollment Database 或 Key Registry。

### B. Online Authentication Phase / 線上認證階段

### English

After enrollment, the online authentication phase verifies device identity through an MQTT-based challenge-response protocol. The server publishes a challenge payload containing three fields: the target UID, a random nonce, and a timestamp. The nonce provides freshness, while the timestamp bounds the valid authentication window.

### 中文理解

完成註冊後，線上認證階段會透過 MQTT-based challenge-response protocol 驗證設備身份。伺服器會發布一個 challenge payload，包含三個欄位：目標 UID、隨機 nonce，以及 timestamp。nonce 用來提供 freshness，timestamp 則限制該 challenge 的有效時間範圍。

### English

Upon receiving the challenge, the device obtains the corresponding PUF-derived key. In a full hardware deployment, the device would acquire a live SRAM startup response, apply the stable-bit mask, and reconstruct `K` with the fuzzy extractor. In the current prototype, this step is represented by a key provider registry generated from the offline PUF-processing artifacts. The device then computes:

```text
tag = HMAC-SHA256(K, UID || nonce || timestamp)
```

The response payload contains the UID, nonce, timestamp, and HMAC tag, and is published back to the server through the MQTT response topic.

### 中文理解

設備收到 challenge 後，會取得對應的 PUF-derived key。在完整硬體部署中，設備應該會即時讀取 SRAM 開機回應、套用 stable-bit mask，並透過 fuzzy extractor 重建 `K`。但在目前 prototype 中，這個步驟由離線 PUF-processing artifacts 產生的 key provider registry 代表。接著設備計算：

```text
tag = HMAC-SHA256(K, UID || nonce || timestamp)
```

response payload 會包含 UID、nonce、timestamp 與 HMAC tag，並透過 MQTT response topic 發回 server。

### English

The server performs four checks before accepting the response. It verifies that the UID is enrolled, checks that the response matches a pending challenge, validates that the timestamp is within the allowed time window, and rejects reused nonces through a freshness cache. These checks prevent simple replay attempts and ensure that the HMAC response is bound to both the enrolled device identity and the fresh challenge.

### 中文理解

server 在接受 response 前會做四個檢查：確認 UID 已註冊、確認 response 對應 pending challenge、確認 timestamp 在允許時間範圍內，以及透過 freshness cache 拒絕重複使用的 nonce。這些檢查能防止簡單 replay attack，並確保 HMAC response 同時綁定已註冊設備身份與新鮮 challenge。

---

## III. System Implementation / 系統實作

### English

The functional prototype is implemented in Python 3.11 and organized into four major modules. The analysis module computes per-bit stability and generates stable-bit masks from the SRAM PUF dataset. The PUF module performs stable-bit selection and fuzzy-extractor reconstruction. The authentication module implements HMAC-SHA256 challenge-response verification with timestamp validation, nonce caching, and constant-time digest comparison. The MQTT module implements the device and server programs using the Paho MQTT client library.

### 中文理解

本系統 prototype 使用 Python 3.11 實作，並分成四個主要模組。analysis module 負責從 SRAM PUF dataset 計算每個 bit 的穩定度並產生 stable-bit mask。PUF module 負責 stable-bit selection 與 fuzzy-extractor reconstruction。authentication module 實作 HMAC-SHA256 challenge-response verification，包含 timestamp validation、nonce caching，以及 constant-time digest comparison。MQTT module 則使用 Paho MQTT client library 實作 device 與 server 程式。

### English

The core authentication logic is implemented in `auth/hmac_auth.py`. The signed payload is constructed from the device UID, nonce, and timestamp. The HMAC tag is generated using the PUF-derived key `K`:

```text
tag = HMAC-SHA256(K, UID || nonce || timestamp)
```

On the server side, `hmac.compare_digest()` is used instead of normal string equality to reduce timing leakage during tag comparison. The verifier also maintains a nonce cache and removes expired entries according to the configured authentication time window.

### 中文理解

核心認證邏輯位於 `auth/hmac_auth.py`。被簽署的 payload 由設備 UID、nonce 與 timestamp 組成。HMAC tag 使用 PUF-derived key `K` 產生：

```text
tag = HMAC-SHA256(K, UID || nonce || timestamp)
```

server 端使用 `hmac.compare_digest()`，而不是普通字串相等比較，以降低 tag comparison 時的 timing leakage。verifier 也維護 nonce cache，並依照設定的 authentication time window 移除過期項目。

### English

The network layer is implemented in `mqtt/device.py` and `mqtt/server.py`. The server publishes challenge messages to the configured MQTT challenge topic and subscribes to the response topic. The device subscribes to the challenge topic, filters messages by UID, computes the HMAC response, and publishes the response as a JSON payload. The key lookup interface is implemented in `puf/key_provider.py`, which loads generated PUF-derived keys from `artifacts/fuzzy_extractor_results.csv` for integration testing.

### 中文理解

網路層位於 `mqtt/device.py` 與 `mqtt/server.py`。server 會將 challenge message 發布到指定 MQTT challenge topic，並訂閱 response topic。device 訂閱 challenge topic，依照 UID 過濾屬於自己的訊息，計算 HMAC response，並以 JSON payload 發布回 response topic。key lookup interface 位於 `puf/key_provider.py`，會從 `artifacts/fuzzy_extractor_results.csv` 載入由 PUF 流程產生的 PUF-derived keys，用於 integration testing。

### English

A critical engineering boundary must be stated clearly. The Step 6 integration test verifies the complete MQTT authentication loop using keys generated from SRAM PUF dataset artifacts. It does not yet perform live SRAM sampling on a physical ESP32 during runtime. Therefore, the current implementation should be described as a system-level prototype that validates the cryptographic and network authentication pipeline. Replacing the registry lookup with live SRAM response acquisition and device-side fuzzy-extractor reconstruction is left as future work.

### 中文理解

這裡有一個很重要的工程邊界必須講清楚。Step 6 integration test 是使用 SRAM PUF dataset artifacts 產生的 key 來驗證完整 MQTT authentication loop；它目前還沒有在 runtime 從實體 ESP32 即時讀取 SRAM。因此，目前 implementation 應描述為 system-level prototype，用來驗證 cryptographic 與 network authentication pipeline。未來工作才是把 registry lookup 替換成 live SRAM response acquisition 與 device-side fuzzy-extractor reconstruction。

### Figure Placeholder

```text
[Place Figure 2 here: Sequence diagram of the MQTT-based HMAC challenge-response authentication flow.]
```

### 中文提醒

Figure 2 建議畫成 sequence diagram。角色可以是 Authentication Server、MQTT Broker、IoT Device。流程包含 Challenge、Key Reconstruction / Lookup、HMAC generation、Response、Verification。

---

## IV. Security Analysis / 安全性分析

### English

Replay attack resistance: Each challenge includes a fresh nonce and timestamp. The server rejects expired challenges and stores used nonces within the valid time window. Therefore, an attacker cannot simply record a valid response and replay it later.

### 中文理解

重放攻擊防護：每個 challenge 都包含新的 nonce 與 timestamp。server 會拒絕過期 challenge，並在有效時間窗內記錄已使用 nonce。因此，攻擊者不能單純錄下一個合法 response 後在之後重播使用。

### English

Message tampering resistance: The HMAC covers the UID, nonce, and timestamp. Any modification to these fields changes the expected tag and causes verification failure. The implementation also uses constant-time comparison for HMAC verification.

### 中文理解

訊息竄改防護：HMAC 覆蓋 UID、nonce 與 timestamp。任何欄位被修改，都會導致 server 重新計算出的 expected tag 不一致，進而驗證失敗。實作也使用 constant-time comparison 進行 HMAC verification。

### English

Device impersonation resistance: A device must possess the correct PUF-derived key to generate a valid HMAC for a fresh challenge. Therefore, knowing only the UID or MQTT topic is insufficient for impersonation.

### 中文理解

設備冒用防護：設備必須持有正確的 PUF-derived key，才能針對新的 challenge 產生有效 HMAC。因此，攻擊者只知道 UID 或 MQTT topic，並不足以冒用設備。

### English

Physical key extraction resistance: The design goal is to reduce dependence on permanent secret storage by deriving key material from SRAM PUF behavior. However, the current prototype still uses an exported key registry for integration testing. The final hardware version should reconstruct the key from live SRAM responses and avoid storing plaintext keys on the device.

### 中文理解

實體金鑰提取防護：此設計目標是透過 SRAM PUF 行為產生金鑰材料，降低對永久儲存秘密金鑰的依賴。不過，目前 prototype 仍使用匯出的 key registry 做 integration testing。最終硬體版本應該從 live SRAM responses 重建 key，並避免在設備上儲存 plaintext keys。

### English

Limitations: This work focuses on authentication and integrity, not payload confidentiality. MQTT messages should still be protected by TLS or application-layer encryption when sensor data confidentiality is required. In addition, helper data is not a secret, but helper-data leakage must be considered carefully when evaluating the entropy of the selected PUF bits.

### 中文理解

限制：本文聚焦在認證與完整性，不是 payload confidentiality。若 sensor data 需要保密，MQTT message 仍應搭配 TLS 或 application-layer encryption。此外，helper data 不是 secret，但在評估 selected PUF bits 的 entropy 時，仍需謹慎考慮 helper-data leakage。

---

## V. Evaluation / 實驗評估

### A. SRAM PUF Stability / SRAM PUF 穩定度

### English

The dataset summary contains 84 devices, each with 655,360 bit positions. The average per-device bit stability is 0.9697. On average, 574,655 bits per device have stability greater than or equal to 0.90, and the minimum device still contains 513,910 such bits. These results indicate that the dataset provides enough stable positions for reliability-aware key generation.

### 中文理解

資料集摘要包含 84 個設備，每個設備有 655,360 個 bit positions。平均每設備 bit stability 為 0.9697。平均而言，每個設備有 574,655 個 bits 的穩定度大於等於 0.90，即使最低的設備也有 513,910 個這類 bits。這表示資料集提供了足夠的穩定位元，可用於 reliability-aware key generation。

### B. Fuzzy Extractor Reliability / Fuzzy Extractor 可靠度

### English

The fuzzy extractor processed 81 devices and consumed 2,816 selected stable bits per device. Reconstruction succeeds for all processed devices in the no-noise setting. Under random 5% bit-error simulation with 100 trials per device, the average success rate is 99.864%, and the minimum device-level success rate is 98.0%. These results suggest that the selected stable bits and reconstruction method are sufficient for the prototype authentication setting.

### 中文理解

fuzzy extractor 處理了 81 個設備，每個設備使用 2,816 個 selected stable bits。在 no-noise setting 下，所有處理設備都能成功重建。在每個設備 100 次試驗的 random 5% bit-error simulation 下，平均成功率為 99.864%，最低 device-level success rate 為 98.0%。這些結果顯示 selected stable bits 與 reconstruction method 對目前 prototype authentication setting 來說是足夠的。

### C. Inter-Device Uniqueness / 跨設備差異性

### English

The inter-device Hamming distance experiment produces 6,480 pairwise comparisons. The mean Inter-HD is 0.2703, with a standard deviation of 0.0567. This is lower than the ideal value of 0.5 and indicates bias in the dataset. Therefore, this paper does not claim that the raw SRAM responses are ideal identifiers. Instead, the system uses reliability-aware preprocessing and fuzzy extraction before applying HMAC-based authentication.

### 中文理解

inter-device Hamming distance 實驗產生 6,480 組 pairwise comparisons。平均 Inter-HD 為 0.2703，標準差為 0.0567。這低於理想值 0.5，表示資料集存在 bias。因此，本文不宣稱 raw SRAM responses 是理想 identifier；相反地，系統會先使用 reliability-aware preprocessing 與 fuzzy extraction，再進行 HMAC-based authentication。

### D. MQTT Authentication Feasibility / MQTT 認證可行性

### English

The MQTT prototype validates the authentication flow using generated PUF-derived keys. The server publishes a challenge to the configured MQTT topic, and the device responds with an HMAC-SHA256 tag. The integration log confirms successful authentication for an enrolled UID. This result verifies the feasibility of combining the PUF-derived key pipeline with MQTT challenge-response authentication.

### 中文理解

MQTT prototype 使用產生的 PUF-derived keys 驗證 authentication flow。server 將 challenge 發布到指定 MQTT topic，device 回傳 HMAC-SHA256 tag。integration log 確認 enrolled UID 能成功通過 authentication。這個結果驗證了 PUF-derived key pipeline 與 MQTT challenge-response authentication 結合的可行性。

---

## VI. Conclusion / 結論

### English

This paper presented a reliability-aware SRAM PUF and HMAC authentication pipeline for resource-constrained IoT devices. The system combines offline stable-bit selection, fuzzy-extractor based key reconstruction, and MQTT-based HMAC-SHA256 challenge-response authentication. Experimental artifacts show high average bit stability, reliable key reconstruction under simulated noise, and successful end-to-end MQTT authentication using generated PUF-derived keys. The current prototype remains a system-level validation rather than a complete hardware deployment. Future work will replace the key registry with live SRAM response acquisition, measure authentication latency on microcontrollers, and analyze helper-data leakage under stronger entropy assumptions.

### 中文理解

本文提出一套面向資源受限 IoT 設備的 reliability-aware SRAM PUF 與 HMAC authentication pipeline。系統結合離線 stable-bit selection、基於 fuzzy extractor 的 key reconstruction，以及基於 MQTT 的 HMAC-SHA256 challenge-response authentication。實驗 artifacts 顯示平均 bit stability 高、在模擬雜訊下 key reconstruction 可靠，並且能使用 generated PUF-derived keys 完成端到端 MQTT authentication。目前 prototype 仍屬於 system-level validation，而不是完整硬體部署。未來工作將以 live SRAM response acquisition 取代 key registry、在微控制器上量測 authentication latency，並在更強 entropy assumptions 下分析 helper-data leakage。

---

## Tables / 表格

### Table 1. Dataset And Fuzzy Extractor Summary

| Metric | Result | 中文說明 |
| --- | ---: | --- |
| Devices in dataset summary | 84 | 資料集中整理出的設備數 |
| Bits per device | 655,360 | 每個設備的 bit 數 |
| Mean bit stability | 0.9697 | 平均 bit 穩定度 |
| Mean bits with stability >= 0.90 | 574,655 | 每設備平均可用穩定位元數 |
| Devices processed by fuzzy extractor | 81 | fuzzy extractor 成功處理的設備數 |
| Stable bits consumed per device | 2,816 | 每設備用於重建的穩定位元數 |
| No-noise reconstruction success | 100.0% | 無雜訊重建成功率 |
| Random 5% BER mean success | 99.864% | 5% 隨機 BER 模擬平均成功率 |
| Random 5% BER minimum success | 98.0% | 5% 隨機 BER 模擬最低設備成功率 |

### Table 2. Inter-Device Hamming Distance Summary

| Metric | Result | 中文說明 |
| --- | ---: | --- |
| Pairwise comparisons | 6,480 | 跨設備比較組數 |
| Mean Inter-HD | 0.2703 | 平均跨設備 Hamming distance |
| Minimum Inter-HD | 0.0160 | 最小值 |
| Maximum Inter-HD | 0.3726 | 最大值 |
| Standard deviation | 0.0567 | 標準差 |

---

## Reviewer-Safe Wording / 比較安全的寫法

Use these sentences when you are unsure how strongly to claim something.

### English

The current prototype validates the end-to-end authentication pipeline using PUF-derived keys generated from dataset artifacts.

### 中文理解

目前 prototype 是用資料集 artifacts 產生的 PUF-derived keys，驗證端到端 authentication pipeline。

### English

The system focuses on authentication and integrity; confidentiality should be provided by TLS or additional payload encryption when required.

### 中文理解

系統聚焦在認證與完整性；若需要保密性，應搭配 TLS 或額外 payload encryption。

### English

The Inter-HD result is lower than the ideal value, suggesting dataset bias. This motivates the use of preprocessing rather than direct reliance on raw SRAM responses.

### 中文理解

Inter-HD 低於理想值，代表資料集可能有 bias。這正好說明為什麼不能直接依賴 raw SRAM responses，而需要 preprocessing。

### English

Helper data is not treated as a secret, but its leakage implications require careful analysis under the selected fuzzy-extractor construction.

### 中文理解

helper data 不被視為秘密，但它的 leakage 影響仍需根據所選 fuzzy extractor construction 進一步分析。
