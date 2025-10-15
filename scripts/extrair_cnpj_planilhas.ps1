# PowerShell Script para Extrair CNPJ de Planilhas
# Data: 14/10/2025
#
# USO:
#   .\extrair_cnpj_planilhas.ps1 -Pasta "\\192.168.0.2\d\Dados\MR\Scooter\VENDA\PEDIDOS" -Output "cnpjs.xlsx"
#   .\extrair_cnpj_planilhas.ps1 -Pasta "C:\Planilhas" -Output "resultados.csv"

param(
    [Parameter(Mandatory=$true)]
    [string]$Pasta,

    [Parameter(Mandatory=$false)]
    [string]$Output = "cnpjs_encontrados.xlsx",

    [Parameter(Mandatory=$false)]
    [switch]$Debug
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "EXTRATOR DE CNPJ - WINDOWS POWERSHELL" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Verificar se pasta existe
if (-not (Test-Path $Pasta)) {
    Write-Host "ERRO: Pasta nao encontrada: $Pasta" -ForegroundColor Red
    Write-Host "`nDicas:" -ForegroundColor Yellow
    Write-Host "  - Verifique se o caminho esta correto" -ForegroundColor Yellow
    Write-Host "  - Para rede, use: \\servidor\pasta" -ForegroundColor Yellow
    Write-Host "  - Para local, use: C:\pasta" -ForegroundColor Yellow
    exit 1
}

# Obter diretório do projeto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Write-Host "Pasta do projeto: $projectRoot" -ForegroundColor Gray
Write-Host "Pasta de busca: $Pasta`n" -ForegroundColor Gray

# Montar comando Python
$pythonScript = Join-Path $projectRoot "scripts\extrair_cnpj_planilhas.py"

if (-not (Test-Path $pythonScript)) {
    Write-Host "ERRO: Script Python nao encontrado em: $pythonScript" -ForegroundColor Red
    exit 1
}

# Construir argumentos
$args = @($pythonScript, $Pasta, "--output", $Output)

if ($Debug) {
    $args += "--debug"
}

# Executar Python
Write-Host "Executando extrator..." -ForegroundColor Green
Write-Host "Comando: python3 $($args -join ' ')`n" -ForegroundColor Gray

try {
    & python3 $args

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n========================================" -ForegroundColor Green
        Write-Host "SUCESSO! Arquivo gerado: $Output" -ForegroundColor Green
        Write-Host "========================================`n" -ForegroundColor Green
    } else {
        Write-Host "`nErro ao executar script (codigo: $LASTEXITCODE)" -ForegroundColor Red
    }
} catch {
    Write-Host "`nERRO: $_" -ForegroundColor Red
    Write-Host "`nVerifique se Python3 esta instalado:" -ForegroundColor Yellow
    Write-Host "  python3 --version" -ForegroundColor Yellow
}
