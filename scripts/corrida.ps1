# corrida.ps1 — Corrida del asistente en modo headless.
# Ejecuta el PROCESO DIARIO con OpenCode y registra el log.
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\corrida.ps1 [-Silencioso]

param([switch]$Silencioso)

$raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $raiz

if (-not (Test-Path "datos\corridas")) { New-Item -ItemType Directory -Path "datos\corridas" | Out-Null }
$marca = Get-Date -Format "yyyyMMdd_HHmm"
$log = "datos\corridas\corrida_$marca.log"

if (-not (Test-Path "mcp-gmail\token.json")) {
    "Falta mcp-gmail\token.json - ejecutar antes mcp-gmail\autorizar.py" | Out-File $log
    if (-not $Silencioso) { Get-Content $log; Read-Host "Enter para cerrar" }
    exit 1
}

# cerradura: no lanzar dos corridas a la vez (botón del panel + 7:00, etc.)
$cerradura = "datos\corridas\.corriendo.lock"
if (Test-Path $cerradura) {
    if (-not $Silencioso) { Write-Host "Ya hay una corrida en marcha; no se lanza otra." }
    exit 0
}
New-Item -ItemType File -Path $cerradura | Out-Null

try {
    if (-not $Silencioso) {
        Write-Host "Ejecutando el asistente (proceso diario)... esto puede tardar varios minutos."
    }

    $prompt = Get-Content "docs\agente\prompt_corrida.txt" -Raw
    $salida = & opencode run $prompt 2>&1
    $codigo = $LASTEXITCODE
    $salida | Out-File $log -Encoding utf8
    if ($codigo -ne 0) { "AVISO: opencode run termino con codigo $codigo" | Out-File $log -Append -Encoding utf8 }

    # refrescar las vistas (Excel) al terminar (anexando, sin machacar el log)
    & .\.venv\Scripts\python.exe scripts\sync.py 2>&1 | Out-File $log -Append -Encoding utf8

    if (-not $Silencioso) {
        Get-Content $log
        Write-Host ""
        Write-Host "Log completo: $log"
        Read-Host "Enter para cerrar"
    }
    exit $codigo
}
finally {
    Remove-Item $cerradura -ErrorAction SilentlyContinue
}
