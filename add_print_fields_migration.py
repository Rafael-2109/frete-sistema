#!/usr/bin/env python3
"""
Script para adicionar campos de controle de impressão na tabela pedidos
Execute com: python add_print_fields_migration.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def add_print_fields():
    """Adiciona campos de controle de impressão na tabela pedidos"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔧 ADICIONANDO CAMPOS DE CONTROLE DE IMPRESSÃO")
        print("="*60)
        
        try:
            # Verificar se os campos já existem
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'pedidos' 
                AND column_name IN ('separacao_impressa', 'separacao_impressa_em', 'separacao_impressa_por')
            """))
            
            existing_columns = [row[0] for row in result]
            
            if 'separacao_impressa' not in existing_columns:
                print("\n✅ Adicionando campo 'separacao_impressa'...")
                db.session.execute(text("""
                    ALTER TABLE pedidos 
                    ADD COLUMN separacao_impressa BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("   Campo adicionado com sucesso!")
            else:
                print("\n⚠️ Campo 'separacao_impressa' já existe")
            
            if 'separacao_impressa_em' not in existing_columns:
                print("\n✅ Adicionando campo 'separacao_impressa_em'...")
                db.session.execute(text("""
                    ALTER TABLE pedidos 
                    ADD COLUMN separacao_impressa_em TIMESTAMP NULL
                """))
                print("   Campo adicionado com sucesso!")
            else:
                print("\n⚠️ Campo 'separacao_impressa_em' já existe")
            
            if 'separacao_impressa_por' not in existing_columns:
                print("\n✅ Adicionando campo 'separacao_impressa_por'...")
                db.session.execute(text("""
                    ALTER TABLE pedidos 
                    ADD COLUMN separacao_impressa_por VARCHAR(100) NULL
                """))
                print("   Campo adicionado com sucesso!")
            else:
                print("\n⚠️ Campo 'separacao_impressa_por' já existe")
            
            # Commit das alterações
            db.session.commit()
            
            print("\n" + "="*60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*60)
            print("""
            Campos adicionados na tabela 'pedidos':
            - separacao_impressa (BOOLEAN): Indica se foi impresso
            - separacao_impressa_em (TIMESTAMP): Data/hora da impressão
            - separacao_impressa_por (VARCHAR): Usuário que imprimiu
            
            Funcionalidades implementadas:
            1. Indicador visual ao lado de cada item no embarque
            2. Marcação automática ao imprimir separação individual
            3. Marcação automática ao imprimir completo
            4. Tooltip com informações de impressão
            """)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro durante migração: {e}")
            return False

if __name__ == "__main__":
    try:
        if add_print_fields():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)