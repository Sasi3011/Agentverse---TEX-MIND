$ErrorActionPreference = "Stop"
Write-Host "Starting TEXMIND Multi-Agent Suite..." -ForegroundColor Cyan

function Stop-ListenerOnPort {
    param([int]$Port)
    $matches = netstat -ano | Select-String "127.0.0.1:$Port\s+.*LISTENING\s+(\d+)"
    foreach ($m in $matches) {
        if ($m -match "LISTENING\s+(\d+)") {
            $procId = [int]$Matches[1]
            if ($procId -gt 0) {
                Write-Host "  Freeing port $Port (PID $procId)..." -ForegroundColor Yellow
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

$ports = @(8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010, 8011, 8020)
Write-Host "Clearing stale processes on TEXMIND ports..." -ForegroundColor Yellow
foreach ($p in $ports) { Stop-ListenerOnPort -Port $p }
Start-Sleep -Seconds 1

# Start UI Server
Write-Host "Starting UI Server on port 8000..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m http.server 8000"

$agents = @(
    @{ Name="0.Master Orchestrator"; Port=8020 },
    @{ Name="1.Raw Material Intake Agent"; Port=8001 },
    @{ Name="2.Weaving Defect Detection Agent"; Port=8002 },
    @{ Name="3.Dyeing Recipe Optimization Agent"; Port=8003 },
    @{ Name="4.Effluent Compliance Agent"; Port=8004 },
    @{ Name="5.Energy Optimization Agent"; Port=8005 },
    @{ Name="6.Predictive Maintenance Agent"; Port=8006 },
    @{ Name="7.Worker Safety Agent"; Port=8007 },
    @{ Name="8.Demand Forecasting Agent"; Port=8008 },
    @{ Name="9.Supply Chain Traceability Agent"; Port=8009 },
    @{ Name="10.Sustainability & Carbon Reporting Agent"; Port=8010 },
    @{ Name="11.Notification"; Port=8011 }
)

foreach ($agent in $agents) {
    $agentName = $agent.Name
    $port = $agent.Port
    $agentDir = "agents\$agentName"

    if (Test-Path "$agentDir\main.py") {
        Write-Host "Starting $agentName on port $port..." -ForegroundColor Green
        Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port $port" -WorkingDirectory $agentDir
        Start-Sleep -Milliseconds 400
    } else {
        Write-Host "Warning: main.py not found in $agentDir. Skipping." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "All agents started." -ForegroundColor Cyan
Write-Host "  Dashboard: http://localhost:8000/ui/dashboard.html" -ForegroundColor Cyan
Write-Host "  Dyeing Agent health: http://localhost:8003/agents/dye/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to stop all processes..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "Stopping all Python processes..." -ForegroundColor Red
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Write-Host "Done."
