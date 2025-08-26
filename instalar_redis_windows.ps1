# =====================================================
# SCRIPT DE INSTALAÇÃO DO REDIS E SISTEMA ASSÍNCRONO
# Para Windows com PowerShell
# =====================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 INSTALAÇÃO DO SISTEMA ASSÍNCRONO" -ForegroundColor Green
Write-Host "   Redis + RQ para Windows" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se está rodando como Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "⚠️  ATENÇÃO: Execute este script como Administrador!" -ForegroundColor Yellow
    Write-Host "   Clique com botão direito no PowerShell e selecione 'Executar como Administrador'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Pressione Enter para continuar mesmo assim..."
}

# =====================================================
# 1. INSTALAR CHOCOLATEY (se não tiver)
# =====================================================

Write-Host "1️⃣ Verificando Chocolatey..." -ForegroundColor Yellow

try {
    $chocoVersion = choco --version 2>$null
    Write-Host "✅ Chocolatey já instalado: v$chocoVersion" -ForegroundColor Green
} catch {
    Write-Host "📦 Instalando Chocolatey..." -ForegroundColor Yellow
    
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    
    try {
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        Write-Host "✅ Chocolatey instalado com sucesso!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erro ao instalar Chocolatey" -ForegroundColor Red
        Write-Host "   Instale manualmente em: https://chocolatey.org/install" -ForegroundColor Yellow
    }
}

Write-Host ""

# =====================================================
# 2. INSTALAR REDIS VIA CHOCOLATEY
# =====================================================

Write-Host "2️⃣ Instalando Redis..." -ForegroundColor Yellow

# Verificar se Redis já está instalado
$redisInstalled = Get-Command redis-server -ErrorAction SilentlyContinue

if ($redisInstalled) {
    Write-Host "✅ Redis já instalado" -ForegroundColor Green
    redis-server --version
} else {
    Write-Host "📦 Instalando Redis via Chocolatey..." -ForegroundColor Yellow
    
    try {
        choco install redis-64 -y
        Write-Host "✅ Redis instalado com sucesso!" -ForegroundColor Green
        
        # Adicionar ao PATH se necessário
        $redisPath = "C:\ProgramData\chocolatey\lib\redis-64\redis-server.exe"
        if (Test-Path $redisPath) {
            Write-Host "   Redis instalado em: $redisPath" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "❌ Erro ao instalar Redis via Chocolatey" -ForegroundColor Red
        Write-Host ""
        Write-Host "ALTERNATIVA: Instalar Redis via WSL2" -ForegroundColor Yellow
        Write-Host "1. Instale o WSL2: wsl --install" -ForegroundColor Cyan
        Write-Host "2. No Ubuntu/WSL: sudo apt update && sudo apt install redis-server" -ForegroundColor Cyan
    }
}

Write-Host ""

# =====================================================
# 3. OPÇÃO ALTERNATIVA: MEMURAI (Redis para Windows)
# =====================================================

Write-Host "3️⃣ Alternativa: Memurai (Redis otimizado para Windows)" -ForegroundColor Yellow
Write-Host "   Se o Redis não funcionar bem, você pode usar o Memurai:" -ForegroundColor Cyan
Write-Host "   Download: https://www.memurai.com/get-memurai" -ForegroundColor Cyan
Write-Host ""

# =====================================================
# 4. INSTALAR DEPENDÊNCIAS PYTHON
# =====================================================

Write-Host "4️⃣ Instalando dependências Python..." -ForegroundColor Yellow

# Verificar se pip está instalado
try {
    $pipVersion = pip --version
    Write-Host "✅ pip encontrado: $pipVersion" -ForegroundColor Green
    
    Write-Host "📦 Instalando redis e rq..." -ForegroundColor Yellow
    
    # Instalar pacotes
    pip install redis==5.0.8 rq==1.16.1 rq-dashboard==0.6.1
    
    Write-Host "✅ Dependências Python instaladas!" -ForegroundColor Green
} catch {
    Write-Host "❌ pip não encontrado!" -ForegroundColor Red
    Write-Host "   Certifique-se de que Python está instalado e no PATH" -ForegroundColor Yellow
}

Write-Host ""

# =====================================================
# 5. CRIAR ARQUIVO .ENV LOCAL
# =====================================================

Write-Host "5️⃣ Configurando variáveis de ambiente..." -ForegroundColor Yellow

$envFile = ".env"
$redisUrlLocal = "REDIS_URL=redis://localhost:6379/0"

# Verificar se .env existe
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    
    if ($envContent -notmatch "REDIS_URL") {
        Write-Host "📝 Adicionando REDIS_URL ao .env..." -ForegroundColor Yellow
        Add-Content -Path $envFile -Value "`n# Redis Queue Configuration`n$redisUrlLocal"
        Write-Host "✅ REDIS_URL adicionado!" -ForegroundColor Green
    } else {
        Write-Host "✅ REDIS_URL já configurado no .env" -ForegroundColor Green
    }
} else {
    Write-Host "📝 Criando arquivo .env..." -ForegroundColor Yellow
    @"
# Redis Queue Configuration
$redisUrlLocal

# Portal Atacadão (adicione suas credenciais)
ATACADAO_USUARIO=rafael@nacomgoya.com.br
ATACADAO_SENHA=Rafafa6250*
"@ | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "✅ Arquivo .env criado!" -ForegroundColor Green
    Write-Host "⚠️  Lembre-se de adicionar suas credenciais do Atacadão!" -ForegroundColor Yellow
}

Write-Host ""

# =====================================================
# 6. CRIAR SCRIPT DE INICIALIZAÇÃO
# =====================================================

Write-Host "6️⃣ Criando scripts de inicialização..." -ForegroundColor Yellow

# Script para iniciar Redis
$redisScript = @"
@echo off
echo ========================================
echo Iniciando Redis Server...
echo ========================================
redis-server
pause
"@

$redisScript | Out-File -FilePath "iniciar_redis.bat" -Encoding ASCII
Write-Host "✅ Criado: iniciar_redis.bat" -ForegroundColor Green

# Script para iniciar Worker
$workerScript = @"
@echo off
echo ========================================
echo Iniciando Worker Atacadao...
echo ========================================
python worker_atacadao.py
pause
"@

$workerScript | Out-File -FilePath "iniciar_worker.bat" -Encoding ASCII
Write-Host "✅ Criado: iniciar_worker.bat" -ForegroundColor Green

# Script para iniciar tudo
$tudoScript = @"
@echo off
echo ========================================
echo INICIANDO SISTEMA COMPLETO
echo ========================================
echo.
echo 1. Iniciando Redis...
start "Redis Server" cmd /c iniciar_redis.bat
timeout /t 3 /nobreak > nul

echo 2. Iniciando Worker...
start "Worker Atacadao" cmd /c iniciar_worker.bat
timeout /t 3 /nobreak > nul

echo 3. Iniciando Aplicacao Flask...
start "Flask App" cmd /c "python app.py"

echo.
echo ========================================
echo ✅ SISTEMA INICIADO!
echo ========================================
echo.
echo Janelas abertas:
echo - Redis Server
echo - Worker Atacadao
echo - Flask Application
echo.
echo Para parar: Feche cada janela ou use Ctrl+C
echo.
pause
"@

$tudoScript | Out-File -FilePath "iniciar_sistema_completo.bat" -Encoding ASCII
Write-Host "✅ Criado: iniciar_sistema_completo.bat" -ForegroundColor Green

Write-Host ""

# =====================================================
# 7. APLICAR MIGRAÇÃO NO BANCO LOCAL
# =====================================================

Write-Host "7️⃣ Migração do Banco de Dados..." -ForegroundColor Yellow
Write-Host "   Para SQLite local, a migração não é necessária" -ForegroundColor Cyan
Write-Host "   O campo job_id será criado automaticamente pelo SQLAlchemy" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Para PostgreSQL no Render:" -ForegroundColor Yellow
Write-Host "   Use o arquivo: RENDER_MIGRATION_ASYNC.sql" -ForegroundColor Cyan

Write-Host ""

# =====================================================
# 8. TESTAR REDIS
# =====================================================

Write-Host "8️⃣ Testando Redis..." -ForegroundColor Yellow

try {
    # Iniciar Redis em background para teste
    $redisProcess = Start-Process redis-server -PassThru -WindowStyle Hidden -ErrorAction SilentlyContinue
    
    Start-Sleep -Seconds 2
    
    # Testar conexão
    Write-Host "   Testando conexão com Redis..." -ForegroundColor Cyan
    
    $testPython = @"
import redis
try:
    r = redis.from_url('redis://localhost:6379/0')
    r.ping()
    print('✅ Redis funcionando corretamente!')
except Exception as e:
    print(f'❌ Erro ao conectar ao Redis: {e}')
"@
    
    $testPython | python
    
    # Parar processo de teste
    if ($redisProcess -and -not $redisProcess.HasExited) {
        Stop-Process -Id $redisProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
} catch {
    Write-Host "⚠️  Não foi possível testar Redis automaticamente" -ForegroundColor Yellow
    Write-Host "   Execute manualmente: redis-cli ping" -ForegroundColor Cyan
}

Write-Host ""

# =====================================================
# INSTRUÇÕES FINAIS
# =====================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ INSTALAÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 PRÓXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. INICIAR O SISTEMA:" -ForegroundColor Cyan
Write-Host "   Opção A: Executar 'iniciar_sistema_completo.bat'" -ForegroundColor White
Write-Host "   Opção B: Abrir 3 terminais e executar:" -ForegroundColor White
Write-Host "      Terminal 1: redis-server" -ForegroundColor Gray
Write-Host "      Terminal 2: python worker_atacadao.py" -ForegroundColor Gray
Write-Host "      Terminal 3: python app.py" -ForegroundColor Gray
Write-Host ""
Write-Host "2. CONFIGURAR CREDENCIAIS:" -ForegroundColor Cyan
Write-Host "   Edite o arquivo .env e adicione:" -ForegroundColor White
Write-Host "   ATACADAO_USUARIO=seu_usuario" -ForegroundColor Gray
Write-Host "   ATACADAO_SENHA=sua_senha" -ForegroundColor Gray
Write-Host ""
Write-Host "3. TESTAR SISTEMA ASSÍNCRONO:" -ForegroundColor Cyan
Write-Host "   Acesse: http://localhost:5000" -ForegroundColor White
Write-Host "   Faça um agendamento e observe o processamento em background" -ForegroundColor White
Write-Host ""
Write-Host "4. MONITORAR FILAS (OPCIONAL):" -ForegroundColor Cyan
Write-Host "   Execute: rq-dashboard" -ForegroundColor White
Write-Host "   Acesse: http://localhost:9181" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📚 DOCUMENTAÇÃO COMPLETA:" -ForegroundColor Yellow
Write-Host "   REDIS_QUEUE_GUIA.md" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Pressione Enter para finalizar..."