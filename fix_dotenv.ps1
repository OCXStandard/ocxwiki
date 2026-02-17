# Fix dotenv installation issue
Write-Host "========================================"
Write-Host "Fixing python-dotenv installation" -ForegroundColor Cyan
Write-Host "========================================"
Write-Host ""

Write-Host "Step 1: Activating virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1

Write-Host "Step 2: Uninstalling conflicting 'dotenv' package..." -ForegroundColor Yellow
python -m pip uninstall dotenv -y

Write-Host "Step 3: Reinstalling project with correct dependencies..." -ForegroundColor Yellow
uv pip install -e .[dev]

Write-Host ""
Write-Host "Step 4: Verifying installation..." -ForegroundColor Yellow
python test_dotenv.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Done! You can now run your application." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
