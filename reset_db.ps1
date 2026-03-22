
# reset_db.ps1 — Reset e Seed para "Haras do Paredão"
# Exemplo de uso (PowerShell, na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File .\reset_db.ps1 -Seed
#   .\reset_db.ps1 -ProjectRoot "C:\_GestaoHipica\GATEAGORA" -Superuser "Admin" -Email "gateagora@gmail.com" -Password "Gate$2024" -Seed -PurgeMigrations

param(
    [string]$ProjectRoot = "C:\_GestaoHipica\GATEAGORA",
    [string]$VenvActivate = "$ProjectRoot\venv\Scripts\Activate.ps1",
    [string]$Superuser = "Admin",
    [string]$Email = "gateagora@gmail.com",
    [string]$Password = "Gate$2024",
    [switch]$PurgeMigrations,
    [switch]$WipeMedia,
    [switch]$Seed
)

Write-Host "==> Reset DB (Haras do Paredão)" -ForegroundColor Cyan

if (-not (Test-Path $ProjectRoot)) { Write-Error "ProjectRoot not found: $ProjectRoot"; exit 1 }
Set-Location $ProjectRoot

if (Test-Path $VenvActivate) { . $VenvActivate } else { Write-Warning "Venv not found at $VenvActivate" }

# Apaga banco SQLite
$db = Join-Path $ProjectRoot "db.sqlite3"
if (Test-Path $db) { Remove-Item $db -Force; Write-Host "Deleted db.sqlite3" -ForegroundColor Yellow } else { Write-Host "No db.sqlite3 (ok)" }

# (Opcional) Apaga migrations da app local
if ($PurgeMigrations) {
    $mig = Join-Path $ProjectRoot "gateagora\migrations"
    if (Test-Path $mig) {
        Get-ChildItem $mig -Filter *.py | Where-Object { $_.Name -ne "__init__.py" } | Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem $mig -Filter *.pyc -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "Purged app migrations (gateagora)" -ForegroundColor Yellow
    }
}

# (Opcional) Limpa pasta media
if ($WipeMedia) {
    $mediaDir = Join-Path $ProjectRoot "media"
    if (Test-Path $mediaDir) { Remove-Item $mediaDir -Recurse -Force; Write-Host "Wiped media/" -ForegroundColor Yellow }
}

# Recria schema
python manage.py makemigrations
if ($LASTEXITCODE -ne 0) { Write-Error "makemigrations failed"; exit 1 }

python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { Write-Error "migrate failed"; exit 1 }

# Cria superuser sem prompt
$env:DJANGO_SUPERUSER_USERNAME = $Superuser
$env:DJANGO_SUPERUSER_EMAIL = $Email
$env:DJANGO_SUPERUSER_PASSWORD = $Password
python manage.py createsuperuser --noinput
if ($LASTEXITCODE -ne 0) { Write-Warning "createsuperuser may have failed (user may exist)." }

if ($Seed) {
    $seed = Join-Path $ProjectRoot "gerar_dados_paredao.py"
    if (Test-Path $seed) {
        Write-Host "Seeding Haras do Paredão..." -ForegroundColor Cyan
        python manage.py shell < "$seed"
        if ($LASTEXITCODE -ne 0) { Write-Warning "Seeding finished with warnings/errors." }
    } else {
        Write-Warning "Seed file not found: $seed"
    }
}

Write-Host "==> Done" -ForegroundColor Green
