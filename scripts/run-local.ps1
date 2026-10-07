$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$streamlit = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Follow the README local setup steps first."
}

$banking = Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8001" -WorkingDirectory (Join-Path $projectRoot "banking-service") -PassThru -WindowStyle Hidden
$agent = Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory (Join-Path $projectRoot "agent-service") -PassThru -WindowStyle Hidden
$frontend = Start-Process -FilePath $streamlit -ArgumentList "run", "app.py", "--server.port", "8501" -WorkingDirectory (Join-Path $projectRoot "frontend") -PassThru -WindowStyle Hidden

Write-Host "Services started: banking=$($banking.Id), agent=$($agent.Id), frontend=$($frontend.Id)"
Write-Host "Open http://localhost:8501"
Write-Host "Stop them with: Stop-Process -Id $($banking.Id),$($agent.Id),$($frontend.Id)"
