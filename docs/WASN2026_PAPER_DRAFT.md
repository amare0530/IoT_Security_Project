# WASN 2026 Paper Draft

## Paper Type And Target

This draft is intended for a Taiwanese academic conference paper written in IEEE-style English while following the conference template layout.

Target length: 4 to 5 pages.

Reasoning:

- 2 pages is too short for architecture, implementation, security analysis, and evaluation.
- 6 to 8 pages would require deeper related work, physical deployment, power analysis, and latency benchmarking.
- 4 to 5 pages is realistic for the current project: the pipeline is implemented, evaluation artifacts exist, and the remaining work is to present the system clearly and honestly.

## Format Checklist

| Item | Requirement |
| --- | --- |
| Paper size | A4 |
| Layout | Two columns, single spacing |
| Maximum length | 8 pages |
| Paper title | 16 pt bold, centered |
| Authors, affiliation, email | 12 pt, centered |
| Section titles | 12 pt bold, centered |
| Body text | 10 pt Times New Roman |
| Figure caption | Below figure |
| Table caption | Above table |
| Final submission | Word and PDF |

## Recommended Title

A Reliability-Aware SRAM PUF and HMAC Authentication Pipeline for Resource-Constrained IoT Devices

Alternative shorter title:

Reliability-Aware SRAM PUF Authentication for Resource-Constrained IoT Devices over MQTT

Why the recommended title is better:

- It states the real contribution: reliability-aware preprocessing plus authentication pipeline.
- It avoids overstating novelty.
- It is specific enough for WASN because it includes IoT device authentication.
- It does not sound like a generic implementation report.

## Refined Abstract

With the rapid deployment of Internet of Things (IoT) applications, edge devices are increasingly exposed to physical tampering and identity impersonation while operating under limited computational resources. Conventional authentication schemes often rely on long-term keys stored in non-volatile memory, which may be vulnerable to extraction once a device is physically accessed. This paper presents a reliability-aware lightweight authentication pipeline based on Static Random-Access Memory Physical Unclonable Functions (SRAM PUFs) and HMAC-SHA256. The proposed design separates the system into an offline enrollment phase and an online authentication phase. During enrollment, repeated SRAM startup responses are analyzed to identify stable bit positions, generate device-specific masks, and derive key material through a fuzzy extractor. During authentication, the device uses the PUF-derived key to complete an MQTT-based challenge-response protocol with nonce and timestamp protection. Experiments on an SRAM PUF dataset containing 84 devices show an average bit stability of 0.9697. The fuzzy extractor achieves 100% reconstruction success without injected noise and 99.864% average success under random 5% bit-error simulation. The MQTT prototype further validates end-to-end authentication using generated PUF-derived keys. The results suggest that combining reliability-aware preprocessing, fuzzy extraction, and lightweight message authentication is a practical direction for resource-constrained IoT device authentication, while helper-data leakage and live hardware deployment remain important future work.

Approximate length: 219 words.

## Keywords

SRAM PUF, IoT Security, HMAC-SHA256, MQTT, Device Authentication

## Estimated Final Page Allocation

| Page | Content | Notes |
| --- | --- | --- |
| 1 | Title, authors, abstract, keywords, I. Introduction | Keep Introduction short and focused. |
| 2 | II. Proposed Architecture + Figure 1 | Use the system architecture diagram here. |
| 3 | III. Implementation + IV. Security Analysis | Use concise paragraphs, not long textbook explanation. |
| 4 | V. Evaluation + tables + VI. Conclusion | Use 2 compact tables, maybe 1 plot. |
| 5 optional | References or extra figure/table | Use only if Word layout becomes too tight. |

## Suggested Figures And Tables

### Figure 1. System Architecture

Place in Section II, near the first paragraph.

Recommended components:

- IoT Device
- SRAM PUF response source
- Stable-bit mask
- Fuzzy Extractor
- PUF-derived key
- MQTT Broker
- Authentication Server
- Key/helper-data registry or enrollment database

Caption suggestion:

Figure 1. Overview of the proposed reliability-aware SRAM PUF authentication pipeline.

### Figure 2. MQTT Challenge-Response Flow

Place in Section II-B or Section III.

Recommended sequence:

1. Server publishes challenge with UID, nonce, and timestamp.
2. Device reconstructs or retrieves the PUF-derived key.
3. Device computes HMAC-SHA256 over UID, nonce, and timestamp.
4. Device publishes authentication response through MQTT.
5. Server verifies pending challenge, timestamp, nonce reuse, and HMAC value.

Caption suggestion:

Figure 2. MQTT-based HMAC challenge-response authentication flow.

### Table 1. Dataset And Fuzzy Extractor Summary

Place in Section V.

Use one combined table to save space.

| Metric | Result |
| --- | ---: |
| Devices in dataset summary | 84 |
| Bits per device | 655,360 |
| Mean bit stability | 0.9697 |
| Mean bits with stability >= 0.90 | 574,655 |
| Devices processed by fuzzy extractor | 81 |
| Stable bits consumed per device | 2,816 |
| No-noise reconstruction success | 100.0% |
| Random 5% BER mean success | 99.864% |
| Random 5% BER minimum success | 98.0% |

### Table 2. Inter-Device Hamming Distance Summary

Place in Section V-C.

| Metric | Result |
| --- | ---: |
| Pairwise comparisons | 6,480 |
| Mean Inter-HD | 0.2703 |
| Minimum Inter-HD | 0.0160 |
| Maximum Inter-HD | 0.3726 |
| Standard deviation | 0.0567 |

Important wording:

Do not present Inter-HD as ideal. Say that it is lower than the ideal 0.5 and indicates dataset bias. This makes the paper more credible.

## I. Introduction

The Internet of Things (IoT) has become a common infrastructure for sensing, monitoring, and automation systems. In many IoT deployments, edge devices are placed in distributed or unattended environments and communicate with servers through lightweight protocols such as MQTT [1]. This deployment model introduces a practical security problem: device credentials are often stored as long-term secrets in flash memory, configuration files, or other non-volatile storage. Once an attacker obtains physical access to a device, such stored secrets may be extracted and reused to clone the device identity or forge authentication messages.

Physical Unclonable Functions (PUFs) provide a hardware-oriented alternative to conventional key storage. A PUF derives device-specific responses from manufacturing variations rather than from a permanently stored digital secret. SRAM PUFs are particularly attractive for low-cost IoT devices because SRAM is already available in many microcontrollers and its startup state can be used as a device fingerprint [2]. However, SRAM PUF responses are not perfectly stable. Environmental variations, aging, voltage changes, and measurement noise may introduce bit flips between repeated startups. Therefore, raw SRAM responses usually require reliability-aware preprocessing and error correction before they can be used as cryptographic key material [3], [4].

This paper presents a reliability-aware SRAM PUF authentication pipeline for resource-constrained IoT devices. The proposed system moves expensive response analysis to an offline enrollment phase, where stable bit positions are selected and fuzzy-extractor helper data are generated. During online authentication, the device uses the PUF-derived key to compute an HMAC-SHA256 response [5], [6] for an MQTT challenge containing a nonce and timestamp. This design focuses on lightweight device authentication and message integrity rather than payload encryption.

The main contributions are as follows:

- A two-phase SRAM PUF authentication pipeline that separates offline reliability analysis from lightweight online authentication.
- A stable-bit selection and fuzzy-extractor workflow that converts noisy SRAM startup responses into usable PUF-derived key material.
- An MQTT-based HMAC-SHA256 challenge-response prototype with nonce and timestamp replay protection.
- An evaluation using real project artifacts, including stability analysis, fuzzy-extractor reconstruction results, inter-device Hamming distance, and end-to-end MQTT authentication logs.

## II. Proposed Architecture

The proposed architecture consists of two phases: offline enrollment and online authentication. The offline phase prepares reliable authentication material from SRAM PUF measurements. The online phase uses this material to authenticate an IoT device through a lightweight challenge-response exchange.

### A. Offline Enrollment Phase

During enrollment, repeated SRAM startup responses are collected for each device. Each record contains a device identifier, memory address, response data, and collection timestamp. The system converts the recorded byte values into bitstreams and groups repeated measurements by device. For each bit position, the probability of observing 0 and 1 is computed across repeated startups. The stability score is defined as the larger of the two probabilities. A bit is selected if its stability score is greater than or equal to the configured threshold, producing a device-specific stable-bit mask.

The selected stable bits are then used by the fuzzy extractor. In the current implementation, the extractor uses repeated key-bit encoding and majority-vote reconstruction. The enrollment procedure generates a PUF-derived key and helper data. The helper data is not treated as a secret by itself, but its leakage implications still depend on the entropy and bias of the underlying PUF response. For system integration, the current prototype exports generated PUF-derived keys into a registry used by the MQTT device and server programs.

### B. Online Authentication Phase

During authentication, the server publishes a challenge containing the target device UID, a random nonce, and a timestamp. The device obtains the corresponding PUF-derived key and computes an HMAC-SHA256 tag over the UID, nonce, and timestamp. It then publishes a response containing the UID, nonce, timestamp, and HMAC value. The server accepts the response only if four checks pass: the UID is enrolled, the response matches a pending challenge, the timestamp is within the allowed time window, and the nonce has not been used before.

This design avoids public-key cryptography during the online authentication path. The device-side workload is limited to key reconstruction or key retrieval in the prototype, message formatting, and HMAC computation. The nonce and timestamp prevent simple replay attacks, while the HMAC binds the response to both the device identity and the fresh challenge.

## III. System Implementation

The prototype is implemented in Python and organized into four main components. The analysis component computes per-bit stability and generates stable-bit masks from the SRAM PUF dataset. The PUF component implements stable-bit selection and fuzzy-extractor reconstruction. The authentication component implements HMAC-SHA256 challenge-response verification with timestamp validation, nonce caching, and constant-time digest comparison. The MQTT component implements a device and server pair using the Paho MQTT client.

The authentication tag is computed as:

```text
tag = HMAC-SHA256(K, UID || nonce || timestamp)
```

where `K` is the PUF-derived key. On the server side, the same payload is reconstructed from the pending challenge and the expected device UID. The server then recomputes the HMAC and compares it with the received tag. If the HMAC does not match, the timestamp is expired, or the nonce was already used, authentication is rejected.

The Step 6 integration test uses a PUF-derived key registry generated by the fuzzy extractor. This is an important implementation boundary: the prototype validates the complete MQTT authentication loop using keys generated from SRAM PUF processing artifacts, but it does not yet acquire live SRAM startup responses from a physical ESP32 during runtime. In a full deployment, the registry lookup on the device side should be replaced by live SRAM response acquisition and fuzzy-extractor reconstruction.

## IV. Security Analysis

Replay attack resistance: Each challenge includes a fresh nonce and timestamp. The server rejects expired challenges and stores used nonces within the valid time window. Therefore, an attacker cannot simply record a valid response and replay it later.

Message tampering resistance: The HMAC covers the UID, nonce, and timestamp. Any modification to these fields changes the expected tag and causes verification failure. The implementation also uses constant-time comparison for HMAC verification.

Device impersonation resistance: A device must possess the correct PUF-derived key to generate a valid HMAC for a fresh challenge. Therefore, knowing only the UID or MQTT topic is insufficient for impersonation.

Physical key extraction resistance: The design goal is to reduce dependence on permanent secret storage by deriving key material from SRAM PUF behavior. However, the current prototype still uses an exported key registry for integration testing. The final hardware version should reconstruct the key from live SRAM responses and avoid storing plaintext keys on the device.

Limitations: This work focuses on authentication and integrity, not payload confidentiality. MQTT messages should still be protected by TLS or application-layer encryption when sensor data confidentiality is required. In addition, helper data is not a secret, but helper-data leakage must be considered carefully when evaluating the entropy of the selected PUF bits.

## V. Evaluation

The evaluation uses artifacts generated from the SRAM PUF dataset and the MQTT authentication prototype.

### A. SRAM PUF Stability

The dataset summary contains 84 devices, each with 655,360 bit positions. The average per-device bit stability is 0.9697. On average, 574,655 bits per device have stability greater than or equal to 0.90, and the minimum device still contains 513,910 such bits. These results indicate that the dataset provides enough stable positions for reliability-aware key generation.

### B. Fuzzy Extractor Reliability

The fuzzy extractor processed 81 devices and consumed 2,816 selected stable bits per device. Reconstruction succeeds for all processed devices in the no-noise setting. Under random 5% bit-error simulation with 100 trials per device, the average success rate is 99.864%, and the minimum device-level success rate is 98.0%. These results suggest that the selected stable bits and reconstruction method are sufficient for the prototype authentication setting.

### C. Inter-Device Uniqueness

The inter-device Hamming distance experiment produces 6,480 pairwise comparisons. The mean Inter-HD is 0.2703, with a standard deviation of 0.0567. This is lower than the ideal value of 0.5 and indicates bias in the dataset. Therefore, this paper does not claim that the raw SRAM responses are ideal identifiers. Instead, the system uses reliability-aware preprocessing and fuzzy extraction before applying HMAC-based authentication.

### D. MQTT Authentication Feasibility

The MQTT prototype validates the authentication flow using generated PUF-derived keys. The server publishes a challenge to the configured MQTT topic, and the device responds with an HMAC-SHA256 tag. The integration log confirms successful authentication for an enrolled UID. This result verifies the feasibility of combining the PUF-derived key pipeline with MQTT challenge-response authentication.

## VI. Conclusion

This paper presented a reliability-aware SRAM PUF and HMAC authentication pipeline for resource-constrained IoT devices. The system combines offline stable-bit selection, fuzzy-extractor based key reconstruction, and MQTT-based HMAC-SHA256 challenge-response authentication. Experimental artifacts show high average bit stability, reliable key reconstruction under simulated noise, and successful end-to-end MQTT authentication using generated PUF-derived keys. The current prototype remains a system-level validation rather than a complete hardware deployment. Future work will replace the key registry with live SRAM response acquisition, measure authentication latency on microcontrollers, and analyze helper-data leakage under stronger entropy assumptions.

## Reviewer-Style Weaknesses To Fix Before Submission

1. Live hardware boundary must be clear.

Current Step 6 uses a generated PUF-derived key registry. Do not write as if the ESP32 already reconstructs the key from live SRAM during runtime unless that implementation is finished.

2. Inter-HD result is not ideal.

The mean Inter-HD is 0.2703, not 0.5. This should be explained as dataset bias and motivation for preprocessing, not hidden.

3. Helper-data security needs careful wording.

Do not claim helper data leaks nothing. Say it is public in the fuzzy-extractor model, but security depends on entropy, bias, and construction details.

4. Authentication is not encryption.

HMAC provides authentication and integrity. Confidentiality requires TLS or payload encryption.

5. Evaluation still lacks latency.

If time allows, add a small authentication latency test. Even a Python prototype timing table is useful, as long as it is labeled as prototype-level measurement.

6. Related work should be short but real.

For a 4-page paper, do not add a long standalone Related Work section. Instead, cite PUF, SRAM PUF, fuzzy extractor, MQTT, and HMAC directly in the Introduction and Implementation sections.

## Reference Recommendations

Use 6 to 8 references. These are appropriate for a short conference paper:

[1] OASIS Standard, "MQTT Version 3.1.1," Oct. 2014.

[2] D. E. Holcomb, W. P. Burleson, and K. Fu, "Initial SRAM state as a fingerprint and source of true random numbers for RFID tags," in Proc. RFID Security Workshop, 2007.

[3] Y. Dodis, R. Ostrovsky, L. Reyzin, and A. Smith, "Fuzzy extractors: How to generate strong keys from biometrics and other noisy data," SIAM Journal on Computing, vol. 38, no. 1, pp. 97-139, 2008.

[4] R. Maes, P. Tuyls, and I. Verbauwhede, "A soft decision helper data algorithm for SRAM PUFs," in Proc. IEEE International Symposium on Information Theory (ISIT), 2009.

[5] H. Krawczyk, M. Bellare, and R. Canetti, "HMAC: Keyed-hashing for message authentication," RFC 2104, Feb. 1997.

[6] National Institute of Standards and Technology, "The Keyed-Hash Message Authentication Code (HMAC)," FIPS PUB 198-1, July 2008.

[7] J. Delvaux, R. Peeters, D. Gu, and I. Verbauwhede, "A survey on lightweight entity authentication with strong PUFs," ACM Computing Surveys, vol. 48, no. 2, 2015.

[8] R. Maes and I. Verbauwhede, "Physically unclonable functions: A study on the state of the art and future research directions," in Towards Hardware-Intrinsic Security, Springer, 2010.

## Next Concrete Tasks

1. Insert Figure 1 after the first paragraph of Section II.
2. Insert Figure 2 after Section II-B or inside Section III.
3. Convert Table 1 and Table 2 into Word tables in Section V.
4. Add citations in Word using the reference numbers above.
5. If possible, run a small authentication latency experiment and add one sentence or a small table.
6. Ask the teacher whether the advisor should be listed as a co-author or acknowledged only.
