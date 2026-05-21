# WASN 2026 Paper Draft

## What This Draft Is

This file is the working paper draft for MC 2026 & WASN 2026. The intended submission is an English conference paper in the local conference template, with IEEE-style wording and a realistic length of 4 to 5 pages.

The draft is written from the current repository state, not from an idealized future system. The current implementation validates the SRAM-PUF-to-MQTT authentication pipeline with dataset-derived keys. It does not yet perform live SRAM sampling on an ESP32 during runtime.

## Format Reminder

| Item | Requirement |
| --- | --- |
| Paper size | A4 |
| Layout | Two columns, single spacing |
| Maximum length | 8 pages |
| Recommended length | 4 to 5 pages |
| Paper title | 16 pt bold, centered |
| Authors, affiliation, email | 12 pt, centered |
| Section titles | 12 pt bold, centered |
| Body text | 10 pt Times New Roman |
| Figure caption | Below figure |
| Table caption | Above table |
| Submission files | Word and PDF |

## Recommended Title

A Reliability-Aware SRAM PUF and HMAC Authentication Pipeline for Resource-Constrained IoT Devices

Shorter alternative:

Reliability-Aware SRAM PUF Authentication for Resource-Constrained IoT Devices over MQTT

## English Abstract

IoT edge devices deployed in unattended environments face a practical risk: authentication credentials stored in flash memory may be extracted if an attacker gains physical access to the device. This paper presents a reliability-aware authentication pipeline that uses SRAM startup behavior to reconstruct device-specific key material instead of relying only on persistent key storage. The system operates in two phases. During offline enrollment, repeated SRAM startup responses from each device are analyzed to identify stable bit positions, generate a device-specific mask, and produce a PUF-assisted key record through a fuzzy extractor. During online authentication, the device uses the reconstructed or registered PUF-derived key to compute an HMAC-SHA256 response for an MQTT challenge containing a nonce and timestamp. Experiments on a dataset of 84 devices show an average bit stability of 0.9697, with at least 513,910 stable bits available per device at the 0.90 threshold. The fuzzy extractor achieves 100% key reconstruction in the no-noise setting and 99.864% average success under random 5% bit-error simulation across 81 devices. An MQTT prototype validates end-to-end authentication using keys generated from the dataset artifacts. The current implementation is a system-level prototype; live SRAM sampling on physical hardware and helper-data leakage analysis remain future work.

Approximate length: 209 words.

## 中文摘要草稿

部署於無人看管環境的物聯網邊緣設備面臨一個實際風險：若攻擊者取得設備實體存取權，儲存在快閃記憶體中的認證憑證可能遭到提取。本文提出一套可靠度感知認證流程，利用 SRAM 開機行為重建設備專屬金鑰材料，以降低對永久儲存金鑰的依賴。系統分為兩個階段：離線註冊階段分析每台設備的多次 SRAM 開機回應，挑選穩定位元、產生設備專屬遮罩，並透過 fuzzy extractor 產生 PUF-assisted key record；線上認證階段則使用重建或註冊後的 PUF-derived key，針對包含 nonce 與 timestamp 的 MQTT challenge 計算 HMAC-SHA256 回應。實驗資料涵蓋 84 台設備，平均 bit stability 為 0.9697，在 0.90 門檻下每台設備至少有 513,910 個穩定位元。Fuzzy extractor 在無雜訊情境下達到 100% 金鑰重建成功率，並在 81 台設備的隨機 5% 位元錯誤模擬中達到 99.864% 平均成功率。MQTT prototype 驗證了使用資料集 artifacts 產生之金鑰完成端到端認證的可行性。目前實作屬於系統層級 prototype，實體硬體上的即時 SRAM 取樣與 helper-data leakage 分析仍為未來工作。

## Keywords

SRAM PUF, Fuzzy Extractor, HMAC-SHA256, MQTT, IoT Authentication

## Final Page Plan

| Page | Content | Figure/Table |
| --- | --- | --- |
| 1 | Title, authors, abstract, keywords, I. Introduction | None or very small overview if space allows |
| 2 | II. Proposed Architecture | Figure 1 system architecture |
| 3 | III. System Implementation, IV. Security Analysis | Figure 2 sequence flow |
| 4 | V. Evaluation, VI. Conclusion | Table 1 and Table 2 |
| 5 optional | References or extra plot | Inter-HD distribution if space allows |

---

# Paper Body

## I. Introduction

IoT systems often rely on small edge devices that are inexpensive, resource-constrained, and physically exposed. In this setting, device authentication cannot assume that every node is protected inside a trusted data center. A sensor node installed in a classroom, factory, or outdoor environment may be inspected, removed, or copied. If its long-term authentication key is stored directly in flash memory or a configuration file, physical access can become a path to credential extraction and device impersonation.

Physical Unclonable Functions (PUFs) offer a different way to think about device identity. Instead of storing a fixed digital secret, a PUF uses manufacturing variations to produce device-specific responses. SRAM PUFs are attractive for low-cost IoT devices because SRAM is already present in many microcontrollers, and its power-up state can be treated as a hardware fingerprint. The difficulty is that SRAM responses are not perfectly stable. Bit values may change across power cycles because of temperature, voltage, aging, or measurement noise. Raw SRAM output is therefore not suitable as a cryptographic key without preprocessing and reconstruction support.

This work studies a practical authentication pipeline built around that constraint. The system first analyzes repeated SRAM startup responses offline, selects stable bit positions, and uses a fuzzy extractor to generate reconstructable key material. The online path is intentionally lightweight: an authentication server sends an MQTT challenge containing a nonce and timestamp, and the device answers with an HMAC-SHA256 tag computed from the PUF-derived key. The goal is not to claim a complete hardware security product, but to validate the engineering path from noisy SRAM PUF data to lightweight IoT authentication.

The contributions are:

- A two-phase SRAM PUF authentication pipeline that separates offline reliability analysis from online MQTT authentication.
- A stable-bit selection and fuzzy-extractor workflow that turns noisy SRAM startup responses into reconstructable key material.
- An HMAC-SHA256 challenge-response prototype with timestamp validation and nonce reuse protection.
- An evaluation using project artifacts, including bit stability, fuzzy-extractor reconstruction, inter-device Hamming distance, and MQTT integration logs.

## II. Proposed Architecture

The architecture follows the data path used in the implementation: SRAM measurements are processed into stable positions, stable positions are used by the fuzzy extractor, and the resulting key material is consumed by an MQTT authentication protocol. This separation matters because the expensive and data-heavy work happens before deployment, while the online device only needs the lightweight operations required for challenge response.

[Place Figure 1 here: Overview of the reliability-aware SRAM PUF enrollment and MQTT authentication pipeline.]

### A. Offline Enrollment

Enrollment begins with repeated SRAM startup measurements. Each dataset row contains a device identifier (UID), a memory address, response bytes, and a timestamp. The analysis script converts the response bytes into bitstreams and groups measurements by `(UID, timestamp)`, so each timestamp represents one startup sample for a device. Address blocks are sorted and concatenated to form a sample-level bit vector.

For each bit position, the system estimates the probability of observing 0 and 1 across repeated samples. The stability score is:

```text
S_i = max(P_i(0), P_i(1))
```

The dominant bit is the more frequently observed value. In the current experiments, positions with stability at least 0.90 are selected. This produces a device-specific mask: stable cells are retained, and unstable cells are ignored before reconstruction.

The fuzzy extractor uses the selected stable bits as the response source. Its implementation follows a code-offset style construction with repeated key-bit encoding. During `Gen()`, random enrollment key bits are expanded by repetition, XORed with selected stable response bits to form helper data, and then compressed into a 128-bit HMAC key by hashing the key bits together with the UID. During `Rep()`, a later response and the helper data reconstruct the encoded key bits through XOR and majority voting. This is more precise than saying the key is simply hashed from SRAM bits: SRAM behavior anchors reconstruction, while helper data supports recovery from noise.

The current prototype exports generated PUF-derived keys to `artifacts/fuzzy_extractor_results.csv`. This file is used as a key registry for the MQTT integration test. A stricter hardware deployment should replace that registry lookup with live SRAM response acquisition and device-side `Rep()` reconstruction.

### B. Online Authentication

The online phase authenticates one enrolled UID at a time. The server generates a challenge containing a random nonce and timestamp, then publishes `{UID, nonce, timestamp}` to the MQTT challenge topic. The device subscribes to the challenge topic and ignores messages whose UID does not match its configured identity.

For a matching challenge, the device obtains the corresponding PUF-derived key and computes:

```text
tag = HMAC-SHA256(K, UID || nonce || timestamp)
```

In the code, the signed payload is serialized as `uid:nonce:timestamp`. The device publishes a JSON response containing the UID, nonce, timestamp, and HMAC tag to the response topic.

The server accepts a response only if the UID is expected, the response matches the pending challenge, the timestamp is within the configured time window, the nonce has not already been used, and the HMAC tag matches the recomputed value. These checks bind the response to both the enrolled device and the fresh challenge.

## III. System Implementation

The prototype is implemented in Python and is divided into five small modules that mirror the pipeline. `analysis/stability_analysis.py` loads `crps.csv`, validates the required columns, converts byte strings to bitstreams, computes per-bit stability, writes `stability_summary.csv`, and generates `masks.json`. It also estimates holdout BER for threshold comparison. In the current artifact, the aggregate threshold rows are identical across 0.90, 0.95, 0.98, and 0.99; for that reason, the paper uses 0.90 as the working threshold rather than presenting the threshold sweep as a main result.

The PUF logic is implemented in `puf/bit_selection.py` and `puf/fuzzy_extractor.py`. The bit-selection module is intentionally simple: it marks positions whose stability score exceeds the threshold. The fuzzy extractor consumes 2,816 selected bits per device by default, corresponding to 256 key bits with repetition 11. Its majority-vote reconstruction can tolerate a limited number of bit flips per repeated group. The simulation script records no-noise reconstruction, a correctable 5% BER case, and random 5% BER Monte Carlo success rates.

The authentication logic is implemented in `auth/hmac_auth.py`. The `PUFAuthenticator` creates nonce/timestamp challenges, builds the signed payload from UID, nonce, and timestamp, computes HMAC-SHA256, and verifies responses using `hmac.compare_digest()` rather than ordinary string comparison. It also keeps a cache of used nonces and prunes expired entries according to the configured time window.

The MQTT layer is implemented in `mqtt/server.py` and `mqtt/device.py` using the Paho MQTT client. The server publishes challenges and stores the pending challenge per UID. The device listens for challenges, filters by UID, computes the HMAC response, and publishes the result. `puf/key_provider.py` loads the generated key registry, with an optional manual key override for testing.

[Place Figure 2 here: Sequence diagram of the MQTT challenge-response flow.]

Unit tests cover stable-bit selection, fuzzy-extractor reconstruction with noise, HMAC success and failure cases, tampered challenge rejection, expired timestamp rejection, immediate replay rejection, key-registry loading, and MQTT payload roundtrip construction. The Step 6 integration log confirms a successful MQTT authentication run for an enrolled UID using the generated PUF-derived key registry.

## IV. Security Analysis

The prototype addresses authentication and message integrity, not payload confidentiality. This distinction is important: HMAC can prove that a response was generated with the expected key and that authenticated fields were not modified, but it does not hide sensor data. If confidentiality is required, MQTT should be used with TLS or an additional payload-encryption layer.

Replay protection is handled through two mechanisms that work together. The timestamp limits the lifetime of a challenge, and the nonce cache prevents the same challenge from being accepted twice within the valid window. The tests include both an expired-challenge case and an immediate nonce-reuse case.

Message tampering and simple impersonation are rejected by the same HMAC verification step. If an attacker changes the nonce, timestamp, UID, or tag, the server recomputes a different value and rejects the response. Knowing the UID or MQTT topic is therefore insufficient; the attacker must also produce the correct HMAC for the fresh challenge.

The physical-security claim should be stated carefully. The design reduces reliance on a static key stored directly in device memory by tying key reconstruction to SRAM PUF behavior. However, the current Python prototype still uses an exported key registry for integration testing. It should not be described as a finished ESP32 hardware implementation. The stronger claim becomes valid only after live SRAM sampling and on-device reconstruction replace the registry lookup.

Helper data also needs conservative wording. It is public in the fuzzy-extractor model, but public does not mean irrelevant. Its leakage depends on the selected PUF bits, response bias, and extractor construction. The measured Inter-HD is lower than the ideal 0.5, so the paper should not claim ideal PUF uniqueness. Instead, the result motivates the reliability-aware preprocessing and honest future analysis.

## V. Evaluation

The evaluation is based on generated artifacts from the SRAM PUF dataset and the MQTT authentication prototype.

### A. SRAM Stability

The device summary contains 84 devices. Each device has 655,360 bit positions. The average per-device stability is 0.9697, with a minimum average stability of 0.9473 and a maximum of 0.9977. At the 0.90 threshold, each device has at least 513,910 selected stable bits, and the average is 574,655. These numbers show that the dataset contains enough stable positions for the extractor configuration used in the prototype.

### B. Fuzzy-Extractor Reconstruction

The fuzzy extractor processes 81 devices. Each processed device consumes 2,816 selected stable bits. Reconstruction succeeds for all 81 devices in the no-noise case and in the controlled correctable 5% BER case. Under random 5% BER Monte Carlo simulation with 100 trials per device, the average success rate is 99.864%, and the minimum device-level success rate is 98.0%.

### C. Inter-Device Hamming Distance

The inter-device Hamming distance experiment produces 6,480 ordered pairwise comparisons. The mean Inter-HD is 0.2703 with standard deviation 0.0567. This is below the ideal 0.5 expected from unbiased independent identifiers. The result should be reported directly. It suggests dataset bias and supports the decision not to rely on raw SRAM responses alone.

### D. MQTT Authentication

The MQTT integration test uses the key registry generated from fuzzy-extractor outputs. The server publishes challenges for an enrolled UID, and the device returns HMAC responses through the configured MQTT topics. The recorded Step 6 log contains a successful authentication result. This validates the end-to-end software path from generated PUF-derived key material to MQTT-based challenge-response verification.

### Table 1. Dataset and Reconstruction Summary

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

### Table 2. Inter-Device Hamming Distance Summary

| Metric | Result |
| --- | ---: |
| Pairwise comparisons | 6,480 |
| Mean Inter-HD | 0.2703 |
| Minimum Inter-HD | 0.0160 |
| Maximum Inter-HD | 0.3726 |
| Standard deviation | 0.0567 |

## VI. Conclusion

This paper presented a reliability-aware SRAM PUF and HMAC authentication pipeline for resource-constrained IoT devices. The implementation starts from repeated SRAM startup measurements, selects stable bit positions, reconstructs PUF-assisted key material with a fuzzy extractor, and uses the resulting key in an MQTT HMAC challenge-response protocol. The evaluation shows high average bit stability, reliable reconstruction under simulated noise, and a working end-to-end MQTT authentication prototype.

The current system is best understood as a software prototype that validates the pipeline and its boundaries. It does not yet replace the key registry with live SRAM sampling on physical hardware, and the Inter-HD result shows that the dataset is biased rather than ideal. Future work will focus on live microcontroller integration, latency measurement on constrained devices, and a stronger helper-data leakage analysis.

---

# Figure And Table Placement

## Figure 1

Place in Section II after the first architecture paragraph.

Caption:

Figure 1. Reliability-aware SRAM PUF enrollment and MQTT authentication pipeline.

Recommended blocks:

- SRAM startup dataset
- Stability analysis
- Stable-bit mask
- Fuzzy extractor Gen/Rep
- PUF-derived key registry/helper data
- MQTT device
- MQTT broker
- Authentication server

## Figure 2

Place in Section III near the MQTT implementation paragraph.

Caption:

Figure 2. MQTT-based HMAC challenge-response sequence.

Recommended actors:

- Authentication Server
- MQTT Broker
- IoT Device

Recommended messages:

1. Server publishes `{UID, nonce, timestamp}`.
2. Broker delivers challenge.
3. Device obtains/reconstructs PUF-derived key.
4. Device publishes `{UID, nonce, timestamp, hmac}`.
5. Broker delivers response.
6. Server checks pending challenge, time window, nonce cache, and HMAC.

# Reviewer-Safe Notes

Use these points if the teacher or reviewer asks hard questions.

- This is device authentication, not user authentication.
- HMAC gives authentication and integrity, not encryption.
- The current Step 6 integration uses a generated PUF-derived key registry.
- Live SRAM response acquisition is future work.
- Inter-HD is lower than ideal; this is reported as dataset bias.
- Helper data is public in the fuzzy-extractor model, but leakage still needs analysis.
- Threshold comparison artifacts currently have identical aggregate rows, so the paper should not overclaim a threshold sweep.

# References To Use

[1] OASIS Standard, "MQTT Version 3.1.1," Oct. 2014.

[2] D. E. Holcomb, W. P. Burleson, and K. Fu, "Initial SRAM state as a fingerprint and source of true random numbers for RFID tags," in Proc. RFID Security Workshop, 2007.

[3] Y. Dodis, R. Ostrovsky, L. Reyzin, and A. Smith, "Fuzzy extractors: How to generate strong keys from biometrics and other noisy data," SIAM Journal on Computing, vol. 38, no. 1, pp. 97-139, 2008.

[4] R. Maes, P. Tuyls, and I. Verbauwhede, "A soft decision helper data algorithm for SRAM PUFs," in Proc. IEEE International Symposium on Information Theory (ISIT), 2009.

[5] H. Krawczyk, M. Bellare, and R. Canetti, "HMAC: Keyed-hashing for message authentication," RFC 2104, Feb. 1997.

[6] National Institute of Standards and Technology, "The Keyed-Hash Message Authentication Code (HMAC)," FIPS PUB 198-1, July 2008.

[7] J. Delvaux, R. Peeters, D. Gu, and I. Verbauwhede, "A survey on lightweight entity authentication with strong PUFs," ACM Computing Surveys, vol. 48, no. 2, 2015.

[8] R. Maes and I. Verbauwhede, "Physically unclonable functions: A study on the state of the art and future research directions," in Towards Hardware-Intrinsic Security, Springer, 2010.
