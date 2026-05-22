@echo off
cd /d "c:\上位机\1-12通道上位机（新2026.4.13）"
echo DermaSpectra Backend starting...
echo   端口: 5001
echo   按 Ctrl+C 停止
echo.
C:\Anaconda\python.exe server.py
pause
