@echo off
REM Review Service Launcher for Windows

echo.
echo ========================================
echo    REVIEW SERVICE - Setup & Launch
echo ========================================
echo.

REM Check if venv is activated
if "%VIRTUAL_ENV%"=="" (
    echo Activating virtual environment...
    if exist ".\.venv\Scripts\activate.bat" (
        call .\.venv\Scripts\activate.bat
    ) else (
        echo Warning: Virtual environment not found at .\.venv
    )
)

REM Step 1: Install dependencies
echo.
echo [1/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Step 2: Create .env if missing
if not exist ".env" (
    echo.
    echo [2/3] Creating .env file from example...
    copy .env.example .env
    echo Created .env - please update DATABASE_URL if needed
)

REM Step 3: Start service
echo.
echo [3/3] Starting Review Service on http://localhost:8006...
echo.
python main.py

pause
