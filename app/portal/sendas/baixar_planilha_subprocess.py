#!/usr/bin/env python3
"""
Script para baixar planilha modelo Sendas em processo separado
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


async def baixar_planilha_async() -> dict:
    """
    Baixa a planilha modelo e retorna o caminho
    """
    try:
        consumidor = ConsumirAgendasSendas()
        
        # Executar download
        arquivo = await consumidor.run_baixar_planilha()
        
        if arquivo:
            return {
                'success': True,
                'arquivo': arquivo,
                'error': None
            }
        else:
            return {
                'success': False,
                'arquivo': None,
                'error': 'Não foi possível baixar a planilha'
            }
        
    except Exception as e:
        logger.error(f"Erro no download: {e}")
        return {
            'success': False,
            'arquivo': None,
            'error': str(e)
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