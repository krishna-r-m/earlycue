$ErrorActionPreference="Stop"
$root=Split-Path -Parent $MyInvocation.MyCommand.Path

function Step($label,[scriptblock]$cmd){
    Write-Host "==> $label" -ForegroundColor Cyan
    & $cmd
    if($LASTEXITCODE -ne 0){throw "$label failed"}
}

function Find-Python{
    foreach($v in "3.12","3.11","3.10"){
        try{
            & py "-$v" --version *> $null
            if($LASTEXITCODE -eq 0){return $v}
        }catch{}
    }
    return $null
}

$ver=Find-Python
if(-not $ver){
    Write-Host "Python 3.10, 3.11 or 3.12 was not found. Install 3.12 from python.org (tick 'Add python.exe to PATH' and keep the py launcher), then run this again." -ForegroundColor Red
    exit 1
}
if(-not(Get-Command node -ErrorAction SilentlyContinue)){
    Write-Host "Node.js was not found. Install the LTS version from nodejs.org, then run this again." -ForegroundColor Red
    exit 1
}

Set-Location "$root\backend"
if(-not(Test-Path ".venv")){
    Step "create virtual environment (Python $ver)" {& py "-$ver" -m venv .venv}
}
$py="$root\backend\.venv\Scripts\python.exe"
Step "upgrade pip" {& $py -m pip install --upgrade pip}
Step "install PyTorch (CPU)" {& $py -m pip install torch --index-url https://download.pytorch.org/whl/cpu}
Step "install backend packages" {& $py -m pip install -r requirements.txt}
Step "download spaCy model" {& $py -m spacy download en_core_web_sm}
if(-not(Test-Path ".env")){
    Copy-Item ".env.example" ".env"
    $bytes=New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $key=($bytes|ForEach-Object{$_.ToString("x2")}) -join ""
    (Get-Content ".env") -replace "^SECRET_KEY=.*","SECRET_KEY=$key" | Set-Content ".env"
    $gid=Read-Host "Google client ID for Google sign-in (press Enter to skip, see README)"
    if($gid){
        (Get-Content ".env") -replace "^GOOGLE_CLIENT_ID=.*","GOOGLE_CLIENT_ID=$($gid.Trim())" | Set-Content ".env"
    }
}

Set-Location "$root\frontend"
Step "install frontend packages" {npm install}

Write-Host ""
Write-Host "Setup finished. Start Docker Desktop, then run .\start.ps1" -ForegroundColor Green
