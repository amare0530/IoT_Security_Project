# Public demo fixture

`demo_data.py` deterministically produces two synthetic SRAM-like devices with
twelve captures each. It is not derived from `data/crps.csv` or any other private
capture. Each response contains 2,816 bits, matching the default fuzzy-extractor
configuration of 256 key bits with repetition 11.

Use `python scripts/run_offline_demo.py`. The script writes all temporary inputs
and outputs to a caller-selected directory; it never reads or modifies `data/`
or the desktop `artifacts/` directory.
