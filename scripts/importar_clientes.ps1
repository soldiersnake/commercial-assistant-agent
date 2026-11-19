# importar_clientes.ps1 — Importa el Excel de entrada/ y regenera
# las vistas. Lo lanza el botón "📥 Importar clientes" del panel.
# Con -Silencioso va en segundo plano (sin pausa final).

param([switch]$Silencioso)

$raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $raiz

if (-not (Test-Path "datos\corridas")) { New-Item -ItemType Directory -Path "datos\corridas" | Out-Null }
$log = "datos\corridas\importar_$(Get-Date -Format yyyyMMdd_HHmm).log"

$fich = Get-ChildItem "entrada\*.xls*", "entrada\*.csv" -ErrorAction SilentlyContinue |
    Where-Object { -not $_.PSIsContainer } | Select-Object -First 1
if (-not $fich) {
    "No hay ficheros pendientes en entrada/" | Out-File $log
    if (-not $Silencioso) { Get-Content $log; Read-Host "Enter para cerrar" }
    exit 0
}

& .\.venv\Scripts\python.exe scripts\importar_clientes.py 2>&1 | Out-File $log -Encoding utf8
& .\.venv\Scripts\python.exe scripts\sync.py 2>&1 | Out-File $log -Append -Encoding utf8

if (-not $Silencioso) {
    Get-Content $log
    Write-Host ""
    Write-Host "Log: $log"
    Read-Host "Enter para cerrar"
}
exit 0
