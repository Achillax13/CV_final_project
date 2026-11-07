@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" -u run_matrix.py --sizes 224 --bank-vectors 4096 --device cuda --output results/runs_windows > "results\windows_fixed_bank.log" 2>&1
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" summarize_results.py --root results/runs_windows --output results/summary_windows >> "results\windows_fixed_bank.log" 2>&1
exit /b %errorlevel%
