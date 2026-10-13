@echo off
cd /d "%~dp0"
echo This computer will host the demo on the local network.
echo Find this computer's IPv4 address with: ipconfig
python scripts\run_identity_lab.py --host 0.0.0.0 --auto-local-data
pause
