#!/usr/bin/env python3
"""
Script para baixar planilha modelo Sendas em processo separado
Evita conflito de contexto com Flask
"""

import sys
import os
import asyncio
import json
import traceback
import logging

# Adicionar o diretório atual ao path para garantir imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consumir_agendas import ConsumirAgendasSendas

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def baixar_planilha_async() -> dict:
    """
    Baixa a planilha modelo e retorna o caminho
    """
    try:
        # Forçar variável de ambiente para garantir headless em produção
        # Este script roda em subprocess separado
        is_render = os.getenv('RENDER') is not None
        is_render_path = '/opt/render' in os.getcwd()
        
        if is_render or is_render_path:
            os.environ['IS_PRODUCTION'] = 'true'
            logger.info(f"🚀 Ambiente PRODUÇÃO detectado - RENDER={is_render}, PATH={is_render_path}")
            logger.info(f"📁 CWD: {os.getcwd()}")
        else:
            logger.info(f"💻 Ambiente DESENVOLVIMENTO - CWD: {os.getcwd()}")
        
        # Verificar credenciais antes de criar consumidor
        usuario = os.getenv('SENDAS_USUARIO')
        senha = os.getenv('SENDAS_SENHA')
        logger.info(f"🔐 Credenciais: usuário={'CONFIGURADO' if usuario else 'NÃO CONFIGURADO'}, senha={'CONFIGURADA' if senha else 'NÃO CONFIGURADA'}")
        
        if not usuario or not senha:
            return {
                'success': False,
                'arquivo': None,
                'error': 'Credenciais SENDAS_USUARIO e SENDAS_SENHA não configuradas'
            }
        
        consumidor = ConsumirAgendasSendas()
        logger.info("✅ ConsumirAgendasSendas criado com sucesso")
        
        # Executar download
        logger.info("📥 Iniciando download da planilha...")
        arquivo = await consumidor.run_baixar_planilha()
        
        if arquivo:
            logger.info(f"✅ Download concluído: {arquivo}")
            return {
                'success': True,
                'arquivo': arquivo,
                'error': None
            }
        else:
            logger.error("❌ run_baixar_planilha retornou None")
            return {
                'success': False,
                'arquivo': None,
                'error': 'run_baixar_planilha retornou None - verificar logs do playwright'
            }
        
    except ValueError as ve:
        # Erro de credenciais
        logger.error(f"❌ Erro de configuração: {ve}")
        return {
            'success': False,
            'arquivo': None,
            'error': f'Erro de configuração: {str(ve)}'
        }
    except Exception as e:
        logger.error(f"❌ Erro no download: {e}")
        logger.error(f"❌ Tipo do erro: {type(e).__name__}")
        logger.error(f"❌ Stack trace:\n{traceback.format_exc()}")
        return {
            'success': False,
            'arquivo': None,
            'error': f'{type(e).__name__}: {str(e)}'
        }


def main():
    """
    Função principal
    """
    logger.info("Iniciando download da planilha modelo Sendas")
    
    # Executar download
    resultado = asyncio.run(baixar_planilha_async())
    
    # Retornar resultado como JSON
    print(json.dumps(resultado))
    sys.exit(0 if resultado['success'] else 1)


if __name__ == "__main__":
    main()