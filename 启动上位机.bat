@echo off
setlocal
cd /d "%~dp0"

echo Starting PyQt upper-computer app...
if exist "C:\Software\anaconda3\python.exe" (
    "C:\Software\anaconda3\python.exe" "%~dp0pyserial_measure_app\main.py"
) else if exist "C:\Users\Embark\anaconda3\python.exe" (
    "C:\Users\Embark\anaconda3\python.exe" "%~dp0pyserial_measure_app\main.py"
) else (
    python "%~dp0pyserial_measure_app\main.py"
)

echo.
echo Upper-computer app stopped.
pause
