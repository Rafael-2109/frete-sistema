#!/usr/bin/env python3
"""
Script para ativar os triggers SQL otimizados no sistema de estoque.
Substitui os triggers antigos que causavam problemas de flush.

Uso:
    python ativar_triggers_otimizados.py
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.triggers_sql_otimizado import (
    ativar_triggers_otimizados,
    desativar_triggers_antigos
)
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Função principal para ativar os triggers otimizados"""
    
    print("\n" + "="*60)
    print("ATIVAÇÃO DE TRIGGERS SQL OTIMIZADOS")
    print("="*60)
    
    # Criar aplicação Flask
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Desativar triggers antigos
            print("\n[1/3] Desativando triggers antigos...")
            desativar_triggers_antigos()
            print("✅ Triggers antigos desativados")
            
            # 2. Ativar triggers otimizados
            print("\n[2/3] Ativando triggers SQL otimizados...")
            ativar_triggers_otimizados()
            print("✅ Triggers otimizados ativados")
            
            # 3. Verificar conexão com banco
            print("\n[3/3] Verificando conexão com banco de dados...")
            
            # Testar uma query simples
            result = db.session.execute(db.text("SELECT 1"))
            if result:
                print("✅ Conexão com banco OK")
            
            # Verificar se as tabelas necessárias existem
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            tabelas_necessarias = [
                'estoque_tempo_real',
                'movimentacao_prevista',
                'movimentacao_estoque',
                'pre_separacao_item',
                'separacao',
                'programacao_producao'
            ]
            
            print("\nVerificando tabelas:")
            todas_ok = True
            for tabela in tabelas_necessarias:
                if inspector.has_table(tabela):
                    print(f"  ✅ {tabela}")
                else:
                    print(f"  ❌ {tabela} (não encontrada)")
                    todas_ok = False
            
            if not todas_ok:
                print("\n⚠️  ATENÇÃO: Algumas tabelas não foram encontradas.")
                print("Execute as migrações antes de continuar:")
                print("  python init_estoque_tempo_real.py")
                return False
            
            print("\n" + "="*60)
            print("✅ TRIGGERS SQL OTIMIZADOS ATIVADOS COM SUCESSO!")
            print("="*60)
            
            print("\nPróximos passos:")
            print("1. Reinicie a aplicação para aplicar as mudanças")
            print("2. Monitore os logs para verificar o funcionamento")
            print("3. Teste uma operação de movimentação de estoque")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            logger.error(f"Erro ao ativar triggers: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)