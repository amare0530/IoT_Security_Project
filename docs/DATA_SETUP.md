# Data and artifact setup

| Class | Location | Git status | Purpose |
|---|---|---|---|
| Private raw captures | `data/*.csv` | ignored | Desktop-only SRAM measurements |
| Full generated outputs | `artifacts/*.csv`, `artifacts/*.json`, `artifacts/*.log` | ignored | Desktop evaluation evidence |
| Public synthetic demo | `fixtures/` | tracked | Laptop/CI demo without private data |
| Report source | Markdown and SVG under `docs/` | tracked | Collaborative editing |
| Submission copies | `docs/*.docx`, `docs/*.pdf` | ignored | Reviewed delivery assets |

Never add `data/crps.csv`, `artifacts/stability_summary.csv`, or
`artifacts/masks.json` to Git. They remain desktop-local and are not required by
the public demo.

## Desktop full evaluation

Use a new output directory for every analysis run. Do not point a new run at the
existing `artifacts/` directory.

```powershell
python analysis/stability_analysis.py --input data/crps.csv --output-dir runs/2026-09-22-full
```

Record the command, input size, thresholds, seed, and selected cohort in the
generated manifest. The raw input and complete outputs must remain ignored.

## Laptop / CI demo

```powershell
python scripts/run_offline_demo.py --output-dir demo-output
pytest -q
```

The command generates only synthetic temporary data; it never reads `data/` or
the desktop `artifacts/` directory.
