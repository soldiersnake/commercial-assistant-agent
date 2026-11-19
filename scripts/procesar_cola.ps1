# procesar_cola.ps1 — Procesa SOLO la cola de órdenes del panel.
# Lo lanza automáticamente el servidor del panel tras cada acción
# "responder". Con cerradura para no duplicar procesados.

param([switch]$Silencioso)

$raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $raiz

if (-not (Test-Path "datos\corridas")) { New-Item -ItemType Directory -Path "datos\corridas" | Out-Null }
$cerradura = "datos\corridas\.procesando.lock"
if (Test-Path $cerradura) {
    # otra cola en marcha: la orden espera a la corrida programada
    if (-not $Silencioso) { Write-Host "Ya hay una cola en proceso; la orden se procesará en la siguiente corrida." }
    exit 0
}

$pendientes = Get-ChildItem "datos\acciones\ACC-*.json" -ErrorAction SilentlyContinue |
    Where-Object { (Get-Content $_.FullName -Raw | ConvertFrom-Json).estado -eq "pendiente_agente" }
if (-not $pendientes) {
    if (-not $Silencioso) { Write-Host "No hay órdenes pendientes." }
    exit 0
}

New-Item -ItemType File -Path $cerradura | Out-Null
try {
    $marca = Get-Date -Format "yyyyMMdd_HHmm"
    $log = "datos\corridas\cola_$marca.log"
    if (-not $Silencioso) {
        Write-Host "Procesando $($pendientes.Count) orden(es) del panel... (1-2 min)"
    }
    $prompt = Get-Content "docs\agente\prompt_cola.txt" -Raw
    $salida = & opencode run $prompt 2>&1
    $salida | Out-File $log -Encoding utf8
    & .\.venv\Scripts\python.exe scripts\sync.py 2>&1 | Out-File $log -Append -Encoding utf8
    if (-not $Silencioso) {
        Get-Content $log
        Write-Host "Log: $log"
        Read-Host "Enter para cerrar"
    }
}
finally {
    Remove-Item $cerradura -ErrorAction SilentlyContinue
}
