@echo off
setlocal

cd /d "%~dp0"
title Word Prediction

set "PYTHON_CMD="
if exist "C:\Anaconda\python.exe" set "PYTHON_CMD=C:\Anaconda\python.exe"
if not defined PYTHON_CMD if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON_CMD=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON_CMD if exist "C:\Software\anaconda3\python.exe" set "PYTHON_CMD=C:\Software\anaconda3\python.exe"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

set "SCRIPT=word_recognition\predict.py"
set "EXPORT_DIR=..\exports"

set "PYTHON_OK="
if /i "%PYTHON_CMD%"=="python" (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_OK=1"
) else (
    if exist "%PYTHON_CMD%" set "PYTHON_OK=1"
)

if not defined PYTHON_OK (
    echo Error: Python not found.
    echo Tried: %PYTHON_CMD%
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo Error: Script not found: %SCRIPT%
    pause
    exit /b 1
)

if not "%~1"=="" goto predict_arg
goto interactive

:predict_arg
if not exist "%~f1" (
    echo Error: CSV file not found:
    echo %~f1
    pause
    exit /b 1
)

echo Running prediction for:
echo %~f1
echo.
"%PYTHON_CMD%" "%SCRIPT%" "%~f1"
echo.
pause
exit /b %errorlevel%

:interactive
dir /b "%EXPORT_DIR%\*.csv" >nul 2>nul
if errorlevel 1 (
    echo Error: No CSV files found in %EXPORT_DIR%
    pause
    exit /b 1
)

echo Available CSV files in %EXPORT_DIR%:
echo.
dir /b "%EXPORT_DIR%\*.csv"
echo.
set /p "FILE=Enter CSV file name: "

if "%FILE%"=="" (
    echo Error: Empty input.
    pause
    exit /b 1
)

if not exist "%EXPORT_DIR%\%FILE%" (
    echo Error: CSV file not found:
    echo %EXPORT_DIR%\%FILE%
    pause
    exit /b 1
)

echo Running prediction for:
echo %EXPORT_DIR%\%FILE%
echo.
"%PYTHON_CMD%" "%SCRIPT%" "%EXPORT_DIR%\%FILE%"
echo.
pause
exit /b %errorlevel%
