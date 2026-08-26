# Starts the Flask backend and the React (Vite) frontend, each in its own
# terminal window, and opens the app in your browser.
#
# Usage (from the heat-loss-modelling-app folder):
#   .\run.ps1
#
# Closing either window stops that server.

$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvPython = Join-Path $backendDir "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Backend virtual environment not found at $venvPython. Run 'python -m venv venv' and install requirements.txt in backend\ first."
    exit 1
}

Write-Host "Starting backend (Flask) on http://localhost:5000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backendDir'; & '$venvPython' -m flask --app run run --port 5000"

Write-Host "Starting frontend (Vite) on http://localhost:5173 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontendDir'; npm run dev"

Write-Host "Waiting for the frontend to come up..."
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Backend:  http://localhost:5000"
Write-Host "Frontend: http://localhost:5173"
Write-Host "Two new terminal windows were opened - close them to stop the servers."
