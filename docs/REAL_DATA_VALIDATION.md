# Real Data Validation Results - Zenodo TIMA SRAM-PUF

**Date**: 2025-01-XX  
**Goal**: Move beyond document games to actual technical validation  
**Source**: Zenodo TIMA Laboratory, DOI: 10.1038/s41597-023-02225-9

---

## Test Setup

**Data**: Simulated Zenodo SRAM-Based PUF format (3 records from 2 devices)
- Format: CSV with uid, pic, address, data (decimal array), created_at
- Real structure: SRAM readouts from STM32 Nucleo boards
- Challenge: 32-bit address (0x20000000)
- Response: 512-byte SRAM content as comma-separated decimals (0-255)

**Adapter**: public_puf_adapter.py (after format support fix)

---

## Test Results

### PASSED: Format Recognition
- CSV parsing: OK (field names: board_type, uid, pic, address, data, created_at)
- Field mapping: OK (uid→device_id, pic→session_id, address→challenge, data→response)
- Encoding: Successfully converted decimal array format (e.g., "202,203,204..." → hex "cacdce...")

### PASSED: Normalization Pipeline
- Input: 3 raw CSV rows with Zenodo field names
- Output: 3 normalized rows with standard schema
- Device IDs preserved: 470A3154FFFF300081090052, 180A3154FFFF300081090053
- Timestamps: ISO format (2023-01-10 14:23:45)

### PASSED: SQLite Storage
- Created authentication_history.db
- Inserted 3 records into crp_records table
- Response stored as hex string (176 characters = 88 bytes)
- Verified: device_id, challenge, session_id all readable

---

## DISCOVERED TECHNICAL ISSUES

### Issue 1: Incomplete Response Data

**Problem**: 
- Zenodo format claimed: 512 bytes per readout
- Test data truncated: Only 80 bytes (160 comma-separated decimals shown, partial)
- Adapter processed this without validation

**Evidence**:
```
Sample Zenodo row response length (actual): 176 hex chars = 88 bytes
Expected for full SRAM readout: ~1024 hex chars = 512 bytes
Discrepancy: ~82% missing data per readout
```

**Impact**: 
- Each CRP pair is incomplete
- PUF metrics calculated on 88-byte chunks will be unreliable
- Uniqueness and reliability benchmarks will be inflated (smaller space = higher apparent entropy)

**Action Required**: 
- Verify actual Zenodo CSV contains full 512-byte SRAM dumps
- If not: Document that TIMA dataset uses subsampled regions
- If yes: Test script to be rerun with complete data

---

### Issue 2: Challenge Space (Address Field)

**Problem**:
- STM32 SRAM addresses: 32-bit range (0x20000000 - 0x20007FFF typical)
- Zenodo samples show address increments: 0x00, 0x200, 0x400 ...
- These are byte offsets within a single board's address space

**Evidence**:
```
Device 470A3154: address 0x20000000, 0x20000200 (512-byte increments)
Device 180A3154: address 0x20000000 (overlapping address space)
```

**Implication**:
- Challenge diversity is LOW: same addresses repeated per device
- True CRP pairs: (device_id, address) → SRAM content at that address
- Real attack scenario: Can attacker predict content at untested addresses?
- **Not covered in Phase 1 tests**: Only 2-3 addresses per device tested

**Action Required**:
- Characterize address coverage in Zenodo dataset
- Design address exploration strategy (if not already tested with subset)
- Report margin requires testing across FULL address space

---

### Issue 3: Error Correction Code (ECC) Not Modeled

**Problem**:
- Real STM32 SRAM does NOT include built-in ECC for SRAM (only Flash)
- Zenodo raw data: Direct SRAM readouts, no error correction
- Current system: SHA-256 detection but no error tolerance

**Evidence**:
```
Test data shows: response values 0-255 uniformly
No pattern indicating syndrome/redundancy information
```

**Implication**:
- PUF responses are STRONGLY dependent on exact power delivery
- Temperature variation (±2°C): Already tested in Phase 2
- Supply noise (±50mV): Phase 2 shows 5-10% bit flip rate
- Environmental variation: **Not tested with real Zenodo data**

**Known Limitation**:
> Margin 87 bits is theoretical. Reality check: with 8-bit error rate at 10%,
> effective margin drops to ~26 bits per 256-bit output (87 - 61 = 26)

**Action Required**:
- Run uniqueness_benchmark on actual Zenodo subset
- Measure inter-device Hamming distances
- Measure intra-device error rates under temperature/voltage stress
- If error rate >15%: Implement Hamming or BCH ECC

---

### Issue 4: Device Population (N=84 Boards)

**Problem**:
- Zenodo dataset: 84 STM32 boards total
- Phase 1 baseline: Tested on 5 devices (10% of dataset)
- Current system claims: "Scalable to N devices"
- Reality: Code untested on full dataset

**Evidence**:
```
Phase 1: 5 devices, 25 CRPs each → 125 total authentications
Phase 1 claimed: "Statistical margin preserved"
Reality: No inter-device uniqueness metric on 84-device population
```

**Implications**:
- Margin claimed for N=5 doesn't transfer to N=84
- False acceptance rate (FAR) scales with population
- Threshold selection at 87-bit margin may be too optimistic

**Action Required**:
- Extract full 84-device subset from Zenodo
- Recalculate failure statistics with real population
- Verify FAR < 10^-6 holds at N=84

---

## Recommendations for Next Phase

### Immediate (This Week)
1. **Validate Zenodo Download**: Confirm full 512-byte response records
2. **Run Real Benchmark**: 
   ```
   python uniqueness_benchmark.py --source zenodo --subset 84-devices
   ```
3. **Error Analysis**: Measure error rates under realistic conditions

### Short Term (This Month)
1. **ECC Implementation**: Design Hamming(512,487) or BCH corrector
2. **Address Coverage**: Test margin across full SRAM map
3. **Population Scaling**: Verify metrics at N=84

### Documentation
1. Update `docs/reports/ADVISOR_BRIEF_2026-04-07.md` with real data validation
2. Record all failure modes and remediation in technical report

---

## Status

- ✓ Adapter supports Zenodo format
- ✓ Field mapping verified
- ✓ SQLite integration works
- ⚠ **Real data validation NOT YET STARTED** (test data incomplete)
- ✗ Population-scale testing not performed
- ✗ Margin claim (87 bits) not verified on real Zenodo data

---

## Next Command

```bash
# When real Zenodo data is available:
python public_puf_adapter.py \
  --input zenodo_crp_data_full.csv \
  --dataset-name zenodo-tima-full \
  --output-db validation_zenodo_full.db

# Then run benchmark:
python uniqueness_benchmark.py \
  --input validation_zenodo_full.db \
  --devices 84 \
  --output artifacts/zenodo_benchmark_results.json
```

---

**Author Note**: This report captures what actually happens when real data meets theoretical claims. The goal is to identify gaps early, not to validate assumptions.
