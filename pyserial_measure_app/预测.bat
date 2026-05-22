@echo off
cd /d "%~dp0"
title 词语识别预测

:: 查找 Anaconda Python
set PYTHON_CMD=
if exist "C:\Anaconda\python.exe" set PYTHON_CMD=C:\Anaconda\python.exe
if exist "%USERPROFILE%\anaconda3\python.exe" set PYTHON_CMD=%USERPROFILE%\anaconda3\python.exe
if "%PYTHON_CMD%"=="" set PYTHON_CMD=python

set EXPORT_DIR=..\exports

:: 检查是否拖入了文件
if not "%1"=="" (
    "%PYTHON_CMD%" word_recognition\predict.py "%~f1"
    echo.
    pause
    exit /b 0
)

:: 无参数，弹出选择
echo 可用 CSV 文件（%EXPORT_DIR%\）：
echo.
dir "%EXPORT_DIR%\*.csv" /b 2>nul
if errorlevel 1 (
    echo 未找到 CSV 文件，请先录数据到 exports 目录
    pause
    exit /b 1
)

echo.
set /p FILE="请输入CSV文件名: "
if "%FILE%"=="" (
    echo 输入无效
    pause
    exit /b 1
)

echo.
echo 正在预测 %FILE% ...
"%PYTHON_CMD%" word_recognition\predict.py "%EXPORT_DIR%\%FILE%"

echo.
pause
