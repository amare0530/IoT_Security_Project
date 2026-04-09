# Quickstart (Windows)

This guide is for running the project reliably on Windows.

## 1) Create a clean virtual environment

Use official CPython 3.11 (not MSYS Python) to avoid package wheel issues.

```powershell
py -3.11 -m venv .venv
```

## 2) Install dependencies

```powershell
./install_deps_windows.ps1
```

This script upgrades pip tooling and installs requirements with binary-wheel preference.

## 3) Start three processes

Terminal A:

```powershell
./.venv/Scripts/python.exe -m streamlit run app.py
```

Terminal B:

```powershell
./.venv/Scripts/python.exe mqtt_bridge.py
```

Terminal C:

```powershell
./.venv/Scripts/python.exe node.py
```

When Streamlit starts, open http://localhost:8501.

## 4) Verify core flow

1. Generate challenge in UI
2. Send challenge to node
3. Wait for response
4. Verify authentication result (HD and pass/fail)

## 5) Run validation scripts

```powershell
./.venv/Scripts/python.exe test_phase2_antireplay.py
./.venv/Scripts/python.exe verify_all_phases.py
./.venv/Scripts/python.exe multi_device_eer_stress.py
```

Outputs are written to artifacts/.

## Troubleshooting

1. If you see mgt.clearMarks warnings, clear VS Code problems panel and re-run the task.
2. If dependency install fails, ensure .venv was created by `py -3.11`.
3. If UI has no response, confirm both mqtt_bridge.py and node.py are running.


