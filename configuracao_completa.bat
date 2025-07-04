@echo off
title Configuracao Claude AI - Sistema de Fretes
color 0A

echo.
echo ===============================================
echo    CONFIGURACAO COMPLETA CLAUDE AI
echo    Sistema de Fretes - Versao 1.0
echo ===============================================
echo.

REM Verificar se Python está instalado
echo [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado! Instale o Python 3.8+ primeiro.
    pause
    exit /b 1
) else (
    echo ✅ Python encontrado
)

REM Verificar se pip está funcionando
echo [2/6] Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip nao encontrado!
    pause
    exit /b 1
) else (
    echo ✅ pip encontrado
)

REM Instalar dependências necessárias
echo [3/6] Instalando dependencias...
pip install anthropic redis python-dotenv requests
if errorlevel 1 (
    echo ❌ Erro ao instalar dependencias
    pause
    exit /b 1
) else (
    echo ✅ Dependencias instaladas
)

REM Configurar variáveis de ambiente
echo [4/6] Configurando variaveis de ambiente...
call configurar_env_local.bat
if errorlevel 1 (
    echo ❌ Erro ao configurar variaveis
    pause
    exit /b 1
) else (
    echo ✅ Variaveis configuradas
)

REM Aguardar um momento para as variáveis serem processadas
echo [5/6] Aguardando processamento das variaveis...
timeout /t 3 >nul

REM Verificar configuração
echo [6/6] Verificando configuracao...
python verificar_configuracao.py
if errorlevel 1 (
    echo.
    echo ⚠️  CONFIGURACAO INCOMPLETA
    echo    Revise os erros acima
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ CONFIGURACAO COMPLETA!
    echo.
)

echo ===============================================
echo    SISTEMA PRONTO PARA USO!
echo ===============================================
echo.
echo Proximos passos:
echo.
echo 1. Feche esta janela
echo 2. Abra um NOVO terminal
echo 3. Execute: python testar_sistemas_ativados_corrigido.py
echo 4. Se tudo estiver OK, execute: python run.py
echo.
echo ===============================================
echo    ACESSO AO SISTEMA
echo ===============================================
echo.
echo Quando o sistema estiver rodando:
echo http://localhost:5000/claude-ai/
echo.
echo Pressione qualquer tecla para finalizar...
pause >nul 