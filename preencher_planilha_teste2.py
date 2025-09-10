#!/usr/bin/env python3
"""
Script para preencher a planilha modelo do Sendas
"""

import os
import sys
from datetime import date
import logging

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.portal.sendas.preencher_planilha import PreencherPlanilhaSendas

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,  # Mudando para DEBUG para ver mais detalhes
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Função principal"""
    
    # Configurações
    arquivo_origem = 'app/portal/sendas/downloads/20250907/sendas_agendamentos_20250907_124108_planilha-modelo.xlsx'
    arquivo_destino = 'app/portal/sendas/downloads/agendamento_teste_2.xlsx'
    cnpj = '06.057.223/0233-84'
    data_agendamento = date(2025, 9, 11)  # 11/09/2025
    
    logger.info('🚀 Iniciando preenchimento da planilha modelo...')
    logger.info(f'📂 Arquivo origem: {arquivo_origem}')
    logger.info(f'💾 Arquivo destino: {arquivo_destino}')
    logger.info(f'🏢 CNPJ: {cnpj}')
    logger.info(f'📅 Data agendamento: {data_agendamento.strftime("%d/%m/%Y")}')
    logger.info('=' * 60)
    
    try:
        # Criar app
        app = create_app()
        
        with app.app_context():
            # Criar preenchedor
            preenchedor = PreencherPlanilhaSendas()
            
            # Preencher planilha
            resultado = preenchedor.preencher_planilha(
                arquivo_origem=arquivo_origem,
                cnpj=cnpj,
                data_agendamento=data_agendamento,
                arquivo_destino=arquivo_destino
            )
            
            if resultado:
                logger.info(f'\n✅ Planilha preenchida com sucesso!')
                logger.info(f'📄 Arquivo salvo: {resultado}')
                
                # Verificar se arquivo foi criado
                if os.path.exists(resultado):
                    tamanho = os.path.getsize(resultado)
                    logger.info(f'📊 Tamanho do arquivo: {tamanho:,} bytes')
                else:
                    logger.error('❌ Arquivo não foi criado')
            else:
                logger.error('❌ Erro ao preencher planilha - nenhum dado encontrado')
                
    except Exception as e:
        logger.error(f'❌ Erro ao executar: {e}')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()