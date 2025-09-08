#!/usr/bin/env python3
"""
Script para usar o Playwright Codegen com sessão autenticada do Portal Sendas
Faz login primeiro e depois abre o codegen para gravar as ações
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from sendas_playwright import SendasPortal
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def preparar_sessao_autenticada():
    """
    Faz login no portal e salva o storage state para usar no codegen
    """
    logger.info("=" * 60)
    logger.info("PREPARANDO SESSÃO AUTENTICADA PARA CODEGEN")
    logger.info("=" * 60)
    
    # Criar portal e fazer login
    portal = SendasPortal(headless=False)
    
    try:
        # Iniciar navegador
        if not await portal.iniciar_navegador():
            logger.error("❌ Falha ao iniciar navegador")
            return False
        
        # Fazer login
        logger.info("🔐 Fazendo login no portal...")
        if not await portal.fazer_login():
            logger.error("❌ Falha no login")
            return False
        
        logger.info("✅ Login realizado com sucesso!")
        
        # Salvar storage state (cookies + localStorage)
        await portal.salvar_storage_state()
        logger.info(f"💾 Sessão salva em: {portal.state_file}")
        
        # Fechar navegador
        await portal.fechar()
        
        return portal.state_file
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        await portal.fechar()
        return False


def executar_codegen(storage_state_file):
    """
    Executa o playwright codegen com a sessão autenticada
    """
    logger.info("\n" + "=" * 60)
    logger.info("🎬 INICIANDO PLAYWRIGHT CODEGEN")
    logger.info("=" * 60)
    
    # URL inicial (plataforma Trizy)
    url_inicial = "https://plataforma.trizy.com.br/"
    
    # Arquivo de saída para o código gerado
    output_file = "sendas_agendamento_gerado.py"
    
    # Comando do codegen com storage state
    comando = [
        "playwright",
        "codegen",
        "--load-storage", storage_state_file,  # Carregar sessão autenticada
        "--target", "python-async",  # Gerar código Python assíncrono
        "--output", output_file,  # Arquivo de saída
        url_inicial  # URL inicial
    ]
    
    logger.info("📝 INSTRUÇÕES PARA GRAVAÇÃO:")
    logger.info("=" * 60)
    logger.info("1. O navegador abrirá JÁ AUTENTICADO")
    logger.info("2. Navegue até a área de AGENDAMENTO")
    logger.info("3. Localize e clique no botão de DOWNLOAD da planilha")
    logger.info("4. O Playwright Inspector mostrará o código gerado em tempo real")
    logger.info("5. Quando terminar, FECHE o navegador")
    logger.info(f"6. O código será salvo em: {output_file}")
    logger.info("=" * 60)
    logger.info("\n🚀 Abrindo navegador com codegen...")
    logger.info(f"Comando: {' '.join(comando)}\n")
    
    try:
        # Executar codegen
        result = subprocess.run(comando, check=True)
        
        if result.returncode == 0:
            logger.info("\n" + "=" * 60)
            logger.info("✅ GRAVAÇÃO CONCLUÍDA COM SUCESSO!")
            logger.info("=" * 60)
            logger.info(f"📁 Código gerado salvo em: {output_file}")
            
            # Mostrar o código gerado
            if os.path.exists(output_file):
                logger.info("\n📋 CÓDIGO GERADO:")
                logger.info("-" * 40)
                with open(output_file, 'r') as f:
                    print(f.read())
                logger.info("-" * 40)
            
            return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro ao executar codegen: {e}")
        return False
    
    except FileNotFoundError:
        logger.error("❌ Playwright não está instalado ou não está no PATH")
        logger.info("💡 Instale com: pip install playwright && playwright install chromium")
        return False


async def main():
    """
    Função principal
    """
    # Passo 1: Fazer login e salvar sessão
    storage_state = await preparar_sessao_autenticada()
    
    if not storage_state:
        logger.error("❌ Não foi possível preparar a sessão autenticada")
        return
    
    # Passo 2: Executar codegen com a sessão
    logger.info(f"\n🔄 Usando sessão salva: {storage_state}")
    
    # Pequena pausa para garantir que o arquivo foi salvo
    await asyncio.sleep(1)
    
    # Executar o codegen
    if executar_codegen(storage_state):
        logger.info("\n✨ Processo concluído com sucesso!")
        logger.info("📝 Agora você pode usar o código gerado para automatizar o download da planilha")
    else:
        logger.error("\n❌ Processo falhou")


if __name__ == "__main__":
    # Verificar se o playwright está instalado
    try:
        subprocess.run(["playwright", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ Playwright CLI não encontrado!")
        logger.info("📦 Instalando playwright...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run(["playwright", "install", "chromium"], check=True)
        logger.info("✅ Playwright instalado!")
    
    # Executar
    asyncio.run(main())