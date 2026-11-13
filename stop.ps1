$root=Split-Path -Parent $MyInvocation.MyCommand.Path
docker compose -f "$root\docker-compose.yml" stop db redis
Write-Host "Postgres and Redis stopped. Close the api, worker, beat and frontend windows (Ctrl+C) to stop the rest."
