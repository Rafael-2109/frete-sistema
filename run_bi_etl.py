#!/usr/bin/env python3
"""
Script para executar o ETL do módulo BI
Pode ser executado manualmente ou via cron
"""
import os
import sys

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.bi.services import BiETLService
from app.utils.timezone import agora_utc_naive
def executar_etl():
    """Executa o processo completo de ETL"""
    app = create_app()
    
    with app.app_context():
        print(f"[{agora_utc_naive()}] Iniciando ETL do BI...")
        
        try:
            # Executa ETL completo
            sucesso = BiETLService.executar_etl_completo()
            
            if sucesso:
                print(f"[{agora_utc_naive()}] ETL concluído com sucesso!")
                return 0
            else:
                print(f"[{agora_utc_naive()}] ETL concluído com algumas falhas. Verifique os logs.")
                return 1
                
        except Exception as e:
            print(f"[{agora_utc_naive()}] Erro fatal no ETL: {str(e)}")
            return 2

if __name__ == "__main__":
    exit_code = executar_etl()
    sys.exit(exit_code)