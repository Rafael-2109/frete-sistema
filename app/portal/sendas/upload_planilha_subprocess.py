#!/usr/bin/env python3
"""
Script para executar upload de planilha Sendas em processo separado
Evita conflito de contexto com Flask
"""

import sys
import os
import asyncio
import json

# Adicionar o diretório atual ao path para garantir imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consumir_agendas import ConsumirAgendasSendas
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fazer_upload_async(arquivo_planilha: str) -> dict:
    """
    Executa upload da planilha e retorna resultado
    """
    try:
        # Verificar arquivo antes de tudo
        if not os.path.exists(arquivo_planilha):
            error_msg = f"Arquivo não encontrado: {arquivo_planilha}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        
        if not os.access(arquivo_planilha, os.R_OK):
            error_msg = f"Arquivo não é legível: {arquivo_planilha}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        
        logger.info(f"📁 Arquivo verificado: {arquivo_planilha}")
        logger.info(f"📁 Tamanho: {os.path.getsize(arquivo_planilha)} bytes")
        
        consumidor = ConsumirAgendasSendas()
        
        # Executar upload
        resultado = await consumidor.run_upload_planilha(arquivo_planilha)
        
        return {
            'success': resultado,
            'error': None if resultado else 'Upload falhou no portal Sendas'
        }
        
    except Exception as e:
        error_msg = f"Erro no upload: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.error(f"❌ Tipo do erro: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Stack trace:\n{traceback.format_exc()}")
        return {
            'success': False,
            'error': error_msg
        }


def main():
    """
    Função principal - recebe caminho do arquivo como argumento
    """
    if len(sys.argv) != 2:
        error_result = {'success': False, 'error': 'Caminho do arquivo não fornecido'}
        print(json.dumps(error_result))
        sys.exit(1)
    
    arquivo_planilha = sys.argv[1]
    logger.info(f"🚀 Iniciando upload da planilha: {arquivo_planilha}")
    
    try:
        # Executar upload
        resultado = asyncio.run(fazer_upload_async(arquivo_planilha))
    except Exception as e:
        logger.error(f"❌ Erro fatal ao executar upload: {e}")
        resultado = {
            'success': False,
            'error': f'Erro fatal: {str(e)}'
        }
    
    # Retornar resultado como JSON
    print(json.dumps(resultado))
    sys.exit(0 if resultado['success'] else 1)


if __name__ == "__main__":
    main()