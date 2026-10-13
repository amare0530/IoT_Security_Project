# Paper-Style System Architecture

## Title
Reliability-Aware Bit Selection for Lightweight SRAM-PUF Authentication in IoT Devices

## High-Level Layers

```text
+--------------------------------------------------------------+
| Layer 3: IoT Authentication                                  |
|  - Challenge/Nonce                                           |
|  - HMAC-SHA256 Response                                      |
|  - MQTT/HTTP Transport                                       |
+---------------------------^----------------------------------+
                            |
+---------------------------|----------------------------------+
| Layer 2: Key Generation   |                                  |
|  - FuzzyExtractor.Gen()   | Enroll: R -> (K, HD)             |
|  - FuzzyExtractor.Rep()   | Verify: R' + HD -> K'            |
+---------------------------^----------------------------------+
                            |
+---------------------------|----------------------------------+
| Layer 1: PUF Data Processing                                 |
|  - CSV -> Bitstream                                           |
|  - Bit Stability Analysis                                     |
|  - Stable Bit Mask Selection                                 |
+--------------------------------------------------------------+
```

## Data Artifacts

- Input: `data/crps.csv`
- Output 1: `artifacts/stability_summary.csv`
- Output 2: `artifacts/masks.json`
- Output 3: `artifacts/threshold_comparison.csv`

## Enrollment Flow

1. Collect repeated SRAM startup responses for each UID.
2. Compute bit-wise stability scores.
3. Select stable positions using threshold `t` (e.g., 0.90/0.95/0.98/0.99).
4. Apply mask and run `Gen()` to produce:
   - secret key `K` (device-side, volatile)
   - helper data `HD` (server-stored)
5. Server stores only:
   - `Hash(K)`
   - `HD`
   - `Mask`

## Authentication Flow

1. Device sends `UID`.
2. Server sends `challenge C` + `nonce N`.
3. Device reads SRAM response `R'`, applies mask, runs `Rep(R', HD)` to reconstruct `K'`.
4. Device sends `HMAC(K', C || N)`.
5. Server verifies by recomputing expected tag from enrolled key material.

## Security Notes

- Do not store plaintext key `K` on server.
- Bind authentication payload to both challenge and nonce.
- Use replay protection (nonce expiration + single-use challenge IDs).
- Keep helper-data leakage model explicit in report.

## Prototype boundary

The implemented MQTT path loads a generated PUF-derived test key registry for
system integration. It validates challenge, nonce/timestamp replay protection,
HMAC verification, and MQTT payload exchange. It does **not** yet acquire a
live SRAM response or execute `Rep()` on a microcontroller. A production design
must replace registry lookup with device-side reconstruction and protect the
server enrollment record.
