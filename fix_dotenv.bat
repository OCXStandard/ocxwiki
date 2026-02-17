@echo off
REM Fix dotenv installation issue
echo ========================================
echo Fixing python-dotenv installation
echo ========================================
echo.

echo Step 1: Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Please run: uv venv
    exit /b 1
)

echo Step 2: Uninstalling conflicting 'dotenv' package...
python -m pip uninstall dotenv -y

echo Step 3: Reinstalling project with correct dependencies...
uv pip install -e .[dev]

echo.
echo Step 4: Verifying installation...
python test_dotenv.py

echo.
echo ========================================
echo Done! You can now run your application.
echo ========================================
pause
