# mgt.clearMarks is not a function - Troubleshooting

This warning is a frontend runtime warning, not a Python logic failure.
In this project it is typically triggered by the Streamlit web bundle running in a restricted WebView/browser context.

## What we changed in this repo

1. Added Streamlit runtime config:
   - `.streamlit/config.toml`
   - disables usage stats and hides frontend stack traces from UI.
2. Added a frontend Performance API polyfill in `app.py`:
   - injects no-op `performance.clearMarks`, `clearMeasures`, `mark`, `measure`
   - only used when browser/WebView does not provide these functions.
3. Pinned safer frontend dependency versions in `requirements.txt`:
   - `streamlit==1.54.0`
   - `altair==5.5.0`
   - `pydeck==0.9.0`

## If the warning still appears

1. Use a normal browser tab (Edge/Chrome), not VS Code embedded preview/Simple Browser.
2. Hard refresh the page (`Ctrl+F5`) and clear site data for `localhost`.
3. Confirm you are launching the updated app file:
   - `./.venv/Scripts/python.exe -m streamlit run app.py`
4. Disable browser extensions that override performance APIs (privacy/perf tools) and retry.
5. Recreate `.venv` only if the warning remains after steps 1-4.

## Quick verification checklist

1. Server starts with no Python exception in terminal.
2. App renders normally and authentication functions still work.
3. Browser console no longer logs `mgt.clearMarks is not a function` after hard refresh.

## Why this warning is usually non-fatal

- It is a JavaScript warning tied to performance marks cleanup in the frontend.
- Core backend authentication logic still runs.
- Treat it as a UI runtime compatibility warning unless it is accompanied by broken page rendering.
