@echo off
TITLE Logistics Dashboard Launcher

echo ===================================================
echo      LOGISTICS PRICING DASHBOARD LAUNCHER
echo ===================================================

:: 1. Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

:: 2. Install Dependencies (CRITICAL STEP)
echo [INFO] Installing/Updating required libraries...
echo This might take a minute...
python -m pip install pandas openpyxl pyarrow streamlit numpy fpdf

:: 3. Check if Data exists
IF NOT EXIST "logistics_data.parquet" (
    echo [INFO] Data file not optimized yet. Running converter...
    echo This may take a few minutes for the 1GB file.
    python convert_data.py
)

:: 4. Run Dashboard
echo [SUCCESS] Starting Dashboard...
echo Your browser should open automatically.
python -m streamlit run dashboard.py

pause
