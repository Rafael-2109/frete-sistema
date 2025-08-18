#!/usr/bin/env python3
"""
Script para adicionar/verificar campos de agendamento na tabela pedidos
Garante que pedidos tenha: expedicao, agendamento, protocolo, agendamento_confirmado
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def add_campos_agendamento_to_pedidos():
    """Adiciona/verifica campos de agendamento na tabela pedidos"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar quais campos já existem
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'pedidos' 
                AND column_name IN ('expedicao', 'agendamento', 'protocolo', 'agendamento_confirmado')
            """)
            
            existing_columns = db.session.execute(check_query).fetchall()
            existing_names = [col[0] for col in existing_columns]
            
            print(f"✅ Campos já existentes: {existing_names}")
            
            # Adicionar campos que não existem
            if 'expedicao' not in existing_names:
                print("📝 Adicionando campo expedicao...")
                db.session.execute(text("""
                    ALTER TABLE pedidos 
                    ADD COLUMN IF NOT EXISTS expedicao DATE
                """))
                print("✅ Campo expedicao adicionado!")
            
            if 'agendamento' not in existing_names:
                print("📝 Adicionando campo agendamento...")
                db.session.execute(text("""
                    ALTER TABLE pedidos 
                    ADD COLUMN IF NOT EXISTS agendamento DATE
                """))
                print("✅ Campo agendamento adicionado!")
            
            if 'protocolo' not in existing_names:
                print("📝 Adicionando campo protocolo...")
                db.session.execute(text("""
                    ALTER TABLE pedidos 
                    ADD COLUMN IF NOT EXISTS protocolo VARCHAR(50)
                """))
                print("✅ Campo protocolo adicionado!")
            
            if 'agendamento_confirmado' not in existing_names:
                print("📝 Adicionando campo agendamento_confirmado...")
                db.session.execute(text("""
                    ALTER TABLE pedidos 
                    ADD COLUMN IF NOT EXISTS agendamento_confirmado BOOLEAN DEFAULT FALSE
                """))
                print("✅ Campo agendamento_confirmado adicionado!")
            
            db.session.commit()
            
            # Sincronizar dados existentes de Separacao para Pedido
            print("\n🔄 Sincronizando dados existentes...")
            sync_query = text("""
                UPDATE pedidos p
                SET 
                    expedicao = COALESCE(p.expedicao, s.expedicao),
                    agendamento = COALESCE(p.agendamento, s.agendamento),
                    protocolo = COALESCE(p.protocolo, s.protocolo),
                    agendamento_confirmado = COALESCE(p.agendamento_confirmado, s.agendamento_confirmado)
                FROM (
                    SELECT DISTINCT 
                        separacao_lote_id, 
                        expedicao,
                        agendamento,
                        protocolo,
                        agendamento_confirmado
                    FROM separacao
                    WHERE separacao_lote_id IS NOT NULL
                ) s
                WHERE p.separacao_lote_id = s.separacao_lote_id
                AND p.separacao_lote_id IS NOT NULL
            """)
            
            result = db.session.execute(sync_query)
            db.session.commit()
            
            print(f"✅ Sincronizados {result.rowcount} pedidos com dados de separação!")
            
            # Verificar constraint única
            print("\n🔍 Verificando constraint única...")
            constraint_query = text("""
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'pedidos'::regclass
                AND conname = 'uix_num_pedido_exped_agend_prot'
            """)
            
            constraint_exists = db.session.execute(constraint_query).fetchone()
            
            if not constraint_exists:
                print("⚠️ Constraint única não existe. Considere adicionar se necessário.")
            else:
                print("✅ Constraint única já existe!")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    add_campos_agendamento_to_pedidos()