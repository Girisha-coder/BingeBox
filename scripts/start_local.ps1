# Run BingeBox without Docker, using locally installed PostgreSQL, Python, Node.js and ffmpeg.
#
# First time (from the project folder, e.g. in the VS Code terminal):
#   powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1 -Setup
# Every time after that:
#   powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1
# The website opens at http://127.0.0.1:5173. Press Ctrl+C in the terminal to stop everything.
#
# -Setup creates .env if it is missing and sets DB_PORT to the local PostgreSQL port (-DbPort, default 5432),
# creates the database user "bingebox" and database "bingebox", runs db\*.sql, installs the Python and
# website packages, and loads the demo data. It asks once for the password of the PostgreSQL
# superuser "postgres" chosen when PostgreSQL was installed.

param(
    [switch]$Setup,
    [int]$DbPort = 5432,
    [string]$SuperUser = 'postgres'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$OnWindows = ($PSVersionTable.PSEdition -eq 'Desktop') -or $IsWindows
$VenvPython = if ($OnWindows) { Join-Path $Root '.venv\Scripts\python.exe' } else { Join-Path $Root '.venv/bin/python' }
$ApiPort = 18000
$WebPort = 5173
$WebUrl = "http://127.0.0.1:$WebPort"

function Info($text) { Write-Host $text -ForegroundColor Cyan }
function Fail($text) { Write-Host "ERROR: $text" -ForegroundColor Red; exit 1 }

function Find-Psql {
    $cmd = Get-Command psql -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    if ($OnWindows) {
        $found = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue |
            Sort-Object { $n = 0; [void][int]::TryParse($_.Directory.Parent.Name, [ref]$n); $n } -Descending | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

function Read-DotEnv {
    $values = @{}
    if (Test-Path (Join-Path $Root '.env')) {
        foreach ($line in Get-Content (Join-Path $Root '.env')) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $values[$Matches[1]] = $Matches[2] }
        }
    }
    return $values
}

function Invoke-Psql($user, $password, $database, [string[]]$extra) {
    $env:PGPASSWORD = $password
    $env:PGOPTIONS = '-c client_min_messages=warning'
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $script:Psql -X -q -w -h 127.0.0.1 -p $DbPort -U $user -d $database -v ON_ERROR_STOP=1 @extra 2>&1
        if ($LASTEXITCODE -ne 0) { throw ($out | Out-String) }
        return $out
    } finally { Remove-Item Env:PGPASSWORD, Env:PGOPTIONS -ErrorAction SilentlyContinue }
}

function Test-PortFree($port) {
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        $listener.Start(); $listener.Stop(); return $true
    } catch { return $false }
}

# ---------------------------------------------------------------- checks
$script:Psql = Find-Psql
$Python = $null
foreach ($candidate in @('python', 'py', 'python3')) {
    if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
    # Skips the Microsoft Store "python" shortcut, which exists even when Python is not installed.
    $version = ''
    try { $ErrorActionPreference = 'Continue'; $version = "$(& $candidate --version 2>&1)" } catch { } finally { $ErrorActionPreference = 'Stop' }
    if ($version -match 'Python 3\.(\d+)' -and [int]$Matches[1] -ge 10) { $Python = $candidate; break }
}
$missing = @()
if (-not $script:Psql) { $missing += 'PostgreSQL (psql not found)  -> installer: https://www.postgresql.org/download/windows/' }
if (-not $Python) { $missing += 'Python 3.10 or newer          -> winget install Python.Python.3.12' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { $missing += 'Node.js                       -> winget install OpenJS.NodeJS.LTS' }
elseif ("$(& node --version)" -match '^v(\d+)' -and [int]$Matches[1] -lt 20) { $missing += "Node.js 20 or newer (found $(& node --version)) -> winget install OpenJS.NodeJS.LTS" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { $missing += 'ffmpeg                        -> winget install Gyan.FFmpeg' }
if ($missing.Count -gt 0) {
    Write-Host 'These programs are missing. Install them, then close and reopen the terminal:' -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}

# ---------------------------------------------------------------- setup
if ($Setup) {
    Info "Using psql: $script:Psql"

    Info '1/6  Local configuration (.env)'
    if (-not (Test-Path (Join-Path $Root '.env'))) { & $Python scripts/configure.py }
    $content = Get-Content (Join-Path $Root '.env')
    $content = $content -replace '^DB_PORT=.*$', "DB_PORT=$DbPort"
    Set-Content -Path (Join-Path $Root '.env') -Value $content -Encoding ascii
    Write-Host "  DB_PORT set to $DbPort (the local PostgreSQL port)."
    $cfg = Read-DotEnv
    $AppPassword = $cfg['POSTGRES_PASSWORD']

    Info "2/6  Database user and database (asks for the '$SuperUser' password chosen when PostgreSQL was installed)"
    $superPassword = $env:BINGEBOX_SUPERUSER_PASSWORD
    if (-not $superPassword) {
        $secure = Read-Host "  Password for PostgreSQL user '$SuperUser'" -AsSecureString
        $superPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    }
    try {
        $roleExists = (Invoke-Psql $SuperUser $superPassword 'postgres' @('-tAc', "SELECT 1 FROM pg_roles WHERE rolname='bingebox'")) -join ''
    } catch { Fail "Could not connect to PostgreSQL on port $DbPort as '$SuperUser'. Check the password, and that PostgreSQL is running on that port.`n$_" }
    $verb = if ($roleExists.Trim() -eq '1') { 'ALTER' } else { 'CREATE' }
    $done = if ($verb -eq 'ALTER') { 'updated' } else { 'created' }
    Invoke-Psql $SuperUser $superPassword 'postgres' @('-c', "$verb ROLE bingebox WITH LOGIN SUPERUSER PASSWORD '$AppPassword'") | Out-Null
    $dbExists = (Invoke-Psql $SuperUser $superPassword 'postgres' @('-tAc', "SELECT 1 FROM pg_database WHERE datname='bingebox'")) -join ''
    if ($dbExists.Trim() -ne '1') { Invoke-Psql $SuperUser $superPassword 'postgres' @('-c', 'CREATE DATABASE bingebox OWNER bingebox') | Out-Null }
    Write-Host "  User and database ready ($done user bingebox)."

    Info '3/6  Tables, triggers, functions and views (db\*.sql)'
    $hasTables = (Invoke-Psql 'bingebox' $AppPassword 'bingebox' @('-tAc', "SELECT to_regclass('public.title') IS NOT NULL")) -join ''
    if ($hasTables.Trim() -eq 't') {
        Write-Host '  Already built; skipped.'
    } else {
        foreach ($file in Get-ChildItem (Join-Path $Root 'db') -Filter '*.sql' | Sort-Object Name) {
            Write-Host "  $($file.Name)"
            Invoke-Psql 'bingebox' $AppPassword 'bingebox' @('-f', $file.FullName) | Out-Null
        }
    }

    Info '4/6  Python environment and packages'
    if (-not (Test-Path $VenvPython)) { & $Python -m venv .venv }
    & $VenvPython -m pip install --quiet --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail 'pip install failed.' }

    Info '5/6  Demo data and Kaggle sample'
    $accounts = (Invoke-Psql 'bingebox' $AppPassword 'bingebox' @('-tAc', 'SELECT count(*) FROM account')) -join ''
    if ([int]$accounts.Trim() -gt 0) {
        Write-Host '  Demo data already loaded; skipped.'
    } else {
        & $VenvPython scripts/seed_demo.py | Out-Null
        if ($LASTEXITCODE -ne 0) { Fail 'seed_demo.py failed.' }
    }
    # Imported Kaggle titles are stored with original_language 'Unknown'. Skipping a repeat import also
    # keeps the tracked file data/kaggle/import-report.json unchanged.
    $kaggle = (Invoke-Psql 'bingebox' $AppPassword 'bingebox' @('-tAc', "SELECT count(*) FROM title WHERE original_language = 'Unknown'")) -join ''
    if ([int]$kaggle.Trim() -gt 0) {
        Write-Host '  Kaggle sample already imported; skipped.'
    } else {
        & $VenvPython scripts/import_kaggle.py | Out-Null
        if ($LASTEXITCODE -ne 0) { Fail 'import_kaggle.py failed.' }
    }
    Write-Host '  Data ready.'

    Info '6/6  Website packages (npm ci)'
    Push-Location (Join-Path $Root 'frontend')
    try {
        if ($OnWindows) { & npm.cmd ci --no-audit --no-fund } else { & npm ci --no-audit --no-fund }
        if ($LASTEXITCODE -ne 0) { Fail 'npm ci failed.' }
    } finally { Pop-Location }

    Write-Host ''
    Write-Host 'Setup complete. Start BingeBox with:' -ForegroundColor Green
    Write-Host '  powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1'
    exit 0
}

# ---------------------------------------------------------------- start
$cfg = Read-DotEnv
if (-not $cfg['POSTGRES_PASSWORD'] -or -not (Test-Path $VenvPython) -or -not (Test-Path (Join-Path $Root 'frontend/node_modules/vite/bin/vite.js'))) {
    Fail 'Setup has not been run yet. Run:  powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1 -Setup'
}
foreach ($port in @($ApiPort, $WebPort)) {
    if (-not (Test-PortFree $port)) {
        Fail "Port $port is already in use. If the Docker version of BingeBox is running, stop it first (docker compose stop), or close the other program using the port."
    }
}

$dbPortValue = if ($cfg['DB_PORT']) { $cfg['DB_PORT'] } else { "$DbPort" }
$env:DATABASE_URL = "postgresql://bingebox:$($cfg['POSTGRES_PASSWORD'])@127.0.0.1:$dbPortValue/bingebox"
$env:AUTH_SECRET = $cfg['AUTH_SECRET']
$env:MEDIA_ROOT = Join-Path $Root 'media'
$env:APP_ORIGIN = $WebUrl
$env:API_TARGET = "http://127.0.0.1:$ApiPort"

Info "Starting the backend on port $ApiPort ..."
$api = Start-Process -FilePath $VenvPython -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$ApiPort", '--no-access-log') `
    -WorkingDirectory (Join-Path $Root 'backend') -NoNewWindow -PassThru
try {
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        if ($api.HasExited) { break }
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/health/ready" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) { Fail 'The backend did not start. Check the messages above; is PostgreSQL running, and was -Setup completed?' }

    Info "Backend ready. Starting the website at $WebUrl (Ctrl+C stops both) ..."
    Push-Location (Join-Path $Root 'frontend')
    try {
        & node node_modules/vite/bin/vite.js --host 127.0.0.1 --port $WebPort --strictPort --open
    } finally { Pop-Location }
} finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
    Write-Host 'BingeBox stopped.'
}
