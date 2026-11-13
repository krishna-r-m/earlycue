$ErrorActionPreference="Stop"
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$py="$root\backend\.venv\Scripts\python.exe"

if(-not(Test-Path $py)){
    Write-Host "Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}

docker compose -f "$root\docker-compose.yml" up -d db redis
if($LASTEXITCODE -ne 0){
    Write-Host "Docker could not start Postgres and Redis. Open Docker Desktop, wait for 'Engine running', and try again." -ForegroundColor Red
    exit 1
}

function Launch($title,$dir,$command){
    $full="`$host.UI.RawUI.WindowTitle='$title'; Set-Location '$dir'; $command"
    Start-Process powershell -ArgumentList "-NoExit","-Command",$full
}

Launch "market-pulse api" "$root\backend" "& '$py' -m uvicorn app.main:api --reload"
Launch "market-pulse worker" "$root\backend" "& '$py' -m celery -A app.celery_app:celery worker --loglevel=info --pool=solo"
Launch "market-pulse beat" "$root\backend" "& '$py' -m celery -A app.celery_app:celery beat --loglevel=info"
Launch "market-pulse frontend" "$root\frontend" "npm run dev"

Write-Host "Started api, worker, beat and frontend in separate windows." -ForegroundColor Green
Write-Host "The worker fetches news as soon as it starts. The first run downloads FinBERT (about 440 MB), so give it a few minutes."
Start-Sleep -Seconds 6
Start-Process "http://localhost:5173"
