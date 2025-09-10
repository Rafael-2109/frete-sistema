#!/usr/bin/env python3
"""
Script para executar upload de planilha Sendas em processo separado
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
        
        # Executar upload com mais detalhes de erro
        logger.info("🌐 Iniciando processo de upload...")
        
        try:
            resultado = await consumidor.run_upload_planilha(arquivo_planilha)
            
            if resultado:
                logger.info("✅ Upload concluído com sucesso no portal")
                return {
                    'success': True,
                    'error': None
                }
            else:
                # Tentar capturar mais detalhes do erro
                error_detail = 'Upload falhou no portal Sendas'
                
                # Verificar se há screenshots de erro
                import glob
                screenshots = glob.glob('/tmp/sendas_error_*.png')
                if screenshots:
                    latest_screenshot = sorted(screenshots)[-1]
                    error_detail += f' - Screenshot: {latest_screenshot}'
                    logger.error(f"📸 Screenshot de erro disponível: {latest_screenshot}")
                
                logger.error(f"❌ {error_detail}")
                
                return {
                    'success': False,
                    'error': error_detail
                }
                
        except TimeoutError as te:
            error_msg = f"Timeout durante upload: {str(te)}"
            logger.error(f"⏱️ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as upload_err:
            error_msg = f"Erro específico no upload: {str(upload_err)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"❌ Tipo: {type(upload_err).__name__}")
            return {
                'success': False,
                'error': error_msg
            }
        
    except Exception as e:
        error_msg = f"Erro no upload: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.error(f"❌ Tipo do erro: {type(e).__name__}")
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