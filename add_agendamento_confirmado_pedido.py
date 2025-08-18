#!/usr/bin/env python3
"""
Script para adicionar campo agendamento_confirmado na tabela pedidos
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def add_agendamento_confirmado_to_pedidos():
    """Adiciona campo agendamento_confirmado na tabela pedidos"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Adicionar campo agendamento_confirmado em pedidos
            query = text("""
                ALTER TABLE pedidos 
                ADD COLUMN IF NOT EXISTS agendamento_confirmado BOOLEAN DEFAULT FALSE;
            """)
            
            db.session.execute(query)
            db.session.commit()
            
            print("✅ Campo agendamento_confirmado adicionado com sucesso na tabela pedidos!")
            
            # Sincronizar dados existentes de Separacao para Pedido
            sync_query = text("""
                UPDATE pedidos p
                SET agendamento_confirmado = s.agendamento_confirmado
                FROM (
                    SELECT DISTINCT separacao_lote_id, agendamento_confirmado
                    FROM separacao
                    WHERE separacao_lote_id IS NOT NULL
                ) s
                WHERE p.separacao_lote_id = s.separacao_lote_id
                AND p.separacao_lote_id IS NOT NULL;
            """)
            
            result = db.session.execute(sync_query)
            db.session.commit()
            
            print(f"✅ Sincronizados {result.rowcount} pedidos com dados de separação!")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    add_agendamento_confirmado_to_pedidos()