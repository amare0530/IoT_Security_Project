# Reliability-Aware Bit Selection for Lightweight SRAM-PUF Authentication in IoT Devices

## Chinese Title
基於位元穩定度分析之輕量化 SRAM-PUF IoT 裝置認證系統

## Core Objective
Address SRAM-PUF environmental noise by using reliability-aware bit selection to improve key reconstruction success rate without increasing computational burden.

## Recommended Implementation Sequence
1. PUF Dataset Analysis
2. Bit Stability Selection
3. Fuzzy Extractor
4. HMAC Authentication
5. MQTT Communication
6. System Integration
7. Experiment Evaluation

## Repository Structure
- `data/`: input dataset (put `crps.csv` here)
- `analysis/`: dataset analysis and mask generation
- `puf/`: bit selection and fuzzy extractor modules
- `auth/`: HMAC authentication utilities
- `mqtt/`: demo device/server over MQTT
- `experiments/`: evaluation scripts and plots
- `artifacts/`: generated outputs (created at runtime)

## Step 1: Run Stability Analysis
Expected CSV columns:
- `uid`
- `address`
- `data` (decimal byte 0-255)
- `created_at`

Run:

```powershell
python analysis/stability_analysis.py --input data/crps.csv --output-dir artifacts --thresholds 0.90 0.95 0.98 0.99
```

Outputs:
- `artifacts/stability_summary.csv`
- `artifacts/masks.json`
- `artifacts/threshold_comparison.csv`

## Next Step
Use `artifacts/masks.json` as the core input for fuzzy extractor and authentication experiments.

## Reproducible collaboration workflow

- Keep `data/*.csv` and full `artifacts/*.csv` / `*.json` on the desktop. They
  are intentionally ignored and must never be committed.
- Run the public, deterministic demo on any laptop without the private dataset:

  ```powershell
  python scripts/run_offline_demo.py --output-dir demo-output
  pytest -q
  ```

- Run a desktop analysis only into a new directory, for example
  `runs/2026-09-22-full`; never overwrite historical `artifacts/` evidence.
- See `docs/DATA_SETUP.md` for data boundaries and `docs/DEMO_GUIDE.md` for the
  exhibition workflow. This repository is a dataset-based system-level prototype,
  not a completed live microcontroller SRAM implementation.

The MQTT device demo reconstructs its key with `Rep()` for each challenge and
uses it immediately for HMAC. It best-effort clears its local `bytearray`
buffer afterward. Python cannot guarantee that all immutable `bytes` copies
have been overwritten; a true memory-clearing guarantee requires an MCU
implementation in C. The unauthenticated `iot/auth/result` topic is
informational only and never controls device behavior.

The demo attack helpers are run without key material:

```powershell
python scripts/demo_attack.py forge --uid device-001
python scripts/demo_attack.py replay --uid device-001
python scripts/demo_attack.py tamper --uid device-001
python scripts/demo_attack.py expired --uid device-001
```

The `expired` helper can demonstrate an expired or missing-pending-challenge
path, but cannot produce a valid tag without the device key.

### Attack demonstration matrix

| Attack | Command | Expected server log | Expected device display | Boundary |
| --- | --- | --- | --- | --- |
| Replay | `python scripts/demo_attack.py replay --uid device-001` | `replay: nonce already used` | The matching unauthenticated result may be printed | Reuses a captured response; it cannot create a valid new tag |
| Forge | `python scripts/demo_attack.py forge --uid device-001` | `tag mismatch` | `REJECT`, then the legitimate result may be printed | Uses the real challenge nonce but a random tag |
| Tamper | `python scripts/demo_attack.py tamper --uid device-001` | `challenge mismatch` | `REJECT`, then the legitimate result may be printed | Changes the nonce while retaining the captured tag |
| Expired helper | `python scripts/demo_attack.py expired --uid device-001` | Usually `challenge mismatch` | Usually no matching result | Random nonce cannot reach timestamp validation; it does not possess a key |
| Wrong device | Use UID-A helper data with UID-B response data in the integration test | `REJECT` | No valid authentication | Demonstrates device-specific reconstruction failure |
| Response delay | Start device with `--response-delay 5` and server with `--time-window 3` | `timestamp expired` | `REJECT` | Demo-only delay; it does not give an attacker key material |

The result topic is public and unauthenticated. The device only displays a
result whose nonce matches its latest challenge; it never trusts that result
to stop, retry, or change authentication behavior.

## Two-computer Windows MQTT demo

Use computer A as both the Mosquitto broker and authentication server. Use
computer B as the device and attack terminal. Both computers must be on the
same LAN. Replace `192.168.1.10` below with computer A's LAN IPv4 address,
not `localhost`.

### Computer A: broker and server

1. Install Mosquitto on computer A and allow inbound TCP port 1883 in the
   Windows firewall for the demo network.
2. Find the LAN address:

   ```powershell
   ipconfig
   ```

   Use the active adapter's `IPv4 Address`.
3. Create a demo-only Mosquitto configuration that listens on the LAN
   interface (do not use this anonymous configuration outside the isolated
   demo network):

   ```powershell
   @("listener 1883 0.0.0.0", "allow_anonymous true") |
     Set-Content -Encoding ascii C:\mosquitto-demo.conf
   mosquitto -c C:\mosquitto-demo.conf -v
   ```

4. In a second terminal on computer A, start the server. The server needs a
   key registry containing the selected UID:

   ```powershell
   python -m mqtt.server --broker localhost --uid device-001 --key-registry demo_bundle/server/key_registry.csv
   ```

   The server's `--broker` value is the broker address from computer A.
   Computer B connects to computer A's IPv4 address.

### Computer B: device

First verify that computer B can reach computer A:

```powershell
Test-NetConnection 192.168.1.10 -Port 1883
```

Then start the device with the bundle paths and computer A's address:

```powershell
python -m mqtt.device --broker 192.168.1.10 --uid device-001 `
  --response-registry demo_bundle/device/response.json `
  --helper-registry demo_bundle/device/helper_data.json
```

Expected normal flow:

- computer B prints that the device published an HMAC response;
- computer A prints `Authentication valid=True` and publishes `ACCEPT`;
- computer B may print the matching informational `ACCEPT`.

### Attack demonstrations

Run these one at a time from computer B while the server/device terminals
remain visible:

```powershell
python scripts/demo_attack.py forge --broker 192.168.1.10 --uid device-001
python scripts/demo_attack.py replay --broker 192.168.1.10 --uid device-001
python scripts/demo_attack.py tamper --broker 192.168.1.10 --uid device-001
python scripts/demo_attack.py expired --broker 192.168.1.10 --uid device-001
```

Expected results are `REJECT tag mismatch` for forge, `REJECT replay` after a
previously accepted response for replay, and usually `REJECT challenge
mismatch` for tamper and the expired helper. The expired helper has a random
nonce and cannot reach timestamp validation without a valid pending challenge
and key.

To demonstrate a real timestamp expiry using the device response path, stop
the normal device and restart the server with a longer interval than the
delay:

```powershell
python -m mqtt.server --broker localhost --uid device-001 `
  --key-registry demo_bundle/server/key_registry.csv `
  --time-window 3 --challenge-interval 30
python -m mqtt.device --broker 192.168.1.10 --uid device-001 `
  --response-delay 5 `
  --response-registry demo_bundle/device/response.json `
  --helper-registry demo_bundle/device/helper_data.json
```

The expected server log is `REJECT timestamp expired`, not challenge mismatch.
The 30-second challenge interval prevents a newer challenge from replacing
the pending one while the device waits five seconds.

Stop each process with `Ctrl+C`. For a fresh run, restart the broker if
needed, then start the server before the device. Preserve the server, device,
and attack terminal output when diagnosing a failure. Common causes are an
incorrect LAN IP, port 1883 blocked by Windows Firewall, Mosquitto not
running, or the device accidentally using `localhost`.

## Paper-Ready Docs
- Architecture: `docs/ARCHITECTURE_PAPER_STYLE.md`
- Experiment flow: `docs/EXPERIMENT_FLOW.md`
