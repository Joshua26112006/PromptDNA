# Start the PromptDNA backend and frontend for local development (Windows).
# Usage:  ./scripts/dev.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$backend = Start-Process -PassThru -WorkingDirectory "$root\backend" `
    -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"

$frontend = Start-Process -PassThru -WorkingDirectory "$root\frontend" `
    -FilePath "npm" -ArgumentList "run", "dev"

Write-Host "backend  pid $($backend.Id)  -> http://localhost:8000/health"
Write-Host "frontend pid $($frontend.Id) -> http://localhost:3000"
Write-Host "Press Ctrl+C, then stop the two processes above."

Wait-Process -Id $backend.Id, $frontend.Id
