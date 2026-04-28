# AI Workflow for Modular Implementation

## Project Goal
- Chinese: 基於位元穩定度分析之輕量化 SRAM-PUF IoT 裝置認證系統
- English: Reliability-Aware Bit Selection for Lightweight SRAM-PUF Authentication in IoT Devices

## Collaboration Rule
Do not ask any model to build the whole system in one prompt. Work module by module with explicit acceptance criteria.

## Recommended Sequence
1. PUF Dataset Analysis
2. Bit Stability Selection
3. Fuzzy Extractor
4. HMAC Authentication
5. MQTT Communication
6. System Integration
7. Experiment Evaluation

## Prompt for Codex (Step 1)
I am building an IoT authentication system based on SRAM PUF.

I have a dataset "data/crps.csv" with columns:
uid,address,data,created_at

data is decimal byte (0-255).

Task:
1) convert each byte to 8-bit binary (MSB first)
2) group by UID and samples
3) compute per-bit stability
4) generate bit masks for thresholds 0.90/0.95/0.98/0.99
5) estimate holdout BER for each threshold
6) save artifacts:
   - artifacts/stability_summary.csv
   - artifacts/masks.json
   - artifacts/threshold_comparison.csv

Use Python with pandas and numpy.
Write modular functions and type hints.

## Prompt for Claude (Step 2-4)
Refactor and integrate existing modules into clear interfaces:
- PUFDataLoader
- StabilityAnalyzer
- BitMaskSelector
- FuzzyExtractor
- AuthEngine

Keep behavior unchanged first, then improve structure.
Add integration tests for key reconstruction and HMAC verification.
Document run commands and expected outputs.

## Output Contract (for both Codex/Claude)
Always return:
1. changed files list
2. rationale per file
3. exact run commands
4. expected outputs
5. assumptions and risks
