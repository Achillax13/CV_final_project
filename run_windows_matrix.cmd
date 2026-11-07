@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing. Follow README.md first.
  exit /b 1
)
if not exist "results" mkdir "results"
echo Running 54 formal experiments on CUDA. See results\windows_matrix.log.
".venv\Scripts\python.exe" -u run_matrix.py --sizes 224 320 --device cuda --output results/runs_windows > "results\windows_matrix.log" 2>&1
if errorlevel 1 (
  echo Experiment matrix stopped. See results\windows_matrix.log.
  exit /b 1
)
".venv\Scripts\python.exe" summarize_results.py --root results/runs_windows --output results/summary_windows >> "results\windows_matrix.log" 2>&1
if errorlevel 1 (
  echo Experiments finished, but summary failed. See results\windows_matrix.log.
  exit /b 1
)
echo Experiments and summary finished. See results\summary_windows.
exit /b 0
