"""
Script de Migração: Adicionar Campos do Odoo na Tabela fretes
==============================================================

OBJETIVO:
    Adicionar campos para vincular fretes com registros do Odoo:
    - odoo_dfe_id
    - odoo_purchase_order_id
    - odoo_invoice_id
    - lancado_odoo_em
    - lancado_odoo_por

AUTOR: Sistema de Fretes
DATA: 14/11/2025

USO:
    python3 scripts/adicionar_campos_odoo_frete.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campos_odoo():
    """
    Adiciona campos do Odoo na tabela fretes
    """
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 ADICIONANDO CAMPOS DO ODOO NA TABELA fretes")
            print("=" * 80)
            print()

            campos = [
                {
                    'nome': 'odoo_dfe_id',
                    'tipo': 'INTEGER',
                    'descricao': 'ID do DFe no Odoo'
                },
                {
                    'nome': 'odoo_purchase_order_id',
                    'tipo': 'INTEGER',
                    'descricao': 'ID do Purchase Order no Odoo'
                },
                {
                    'nome': 'odoo_invoice_id',
                    'tipo': 'INTEGER',
                    'descricao': 'ID da Invoice no Odoo'
                },
                {
                    'nome': 'lancado_odoo_em',
                    'tipo': 'TIMESTAMP',
                    'descricao': 'Data/hora do lançamento no Odoo'
                },
                {
                    'nome': 'lancado_odoo_por',
                    'tipo': 'VARCHAR(100)',
                    'descricao': 'Usuário que lançou no Odoo'
                }
            ]

            for idx, campo in enumerate(campos, 1):
                print(f"{idx}️⃣ Verificando campo '{campo['nome']}'...")

                # Verificar se campo já existe
                resultado = db.session.execute(text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'fretes'
                    AND column_name = '{campo['nome']}'
                """))
                campo_existe = resultado.fetchone()

                if campo_existe:
                    print(f"   ⚠️  Campo '{campo['nome']}' já existe! Pulando...")
                    print()
                    continue

                # Adicionar campo
                print(f"   ➕ Adicionando campo '{campo['nome']}' ({campo['tipo']})...")
                db.session.execute(text(f"""
                    ALTER TABLE fretes
                    ADD COLUMN {campo['nome']} {campo['tipo']}
                """))
                db.session.commit()
                print(f"   ✅ Campo '{campo['nome']}' adicionado!")
                print()

            # Criar índices
            print("📊 Criando índices...")
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_fretes_odoo_dfe_id ON fretes(odoo_dfe_id)",
                "CREATE INDEX IF NOT EXISTS idx_fretes_odoo_po_id ON fretes(odoo_purchase_order_id)",
                "CREATE INDEX IF NOT EXISTS idx_fretes_odoo_invoice_id ON fretes(odoo_invoice_id)",
            ]

            for idx_sql in indices:
                db.session.execute(text(idx_sql))
                print(f"   ✅ {idx_sql.split()[5]}")

            db.session.commit()
            print()

            # Verificar campos criados
            print("🔍 Verificando campos criados...")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'fretes'
                AND column_name IN ('odoo_dfe_id', 'odoo_purchase_order_id', 'odoo_invoice_id',
                                    'lancado_odoo_em', 'lancado_odoo_por')
                ORDER BY column_name
            """))

            colunas = resultado.fetchall()
            print(f"   Total de campos adicionados: {len(colunas)}")
            print()
            for col in colunas:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                print(f"      ✅ {col[0]:<30} {col[1]:<20} {nullable}")
            print()

            print("=" * 80)
            print("✅ CAMPOS ADICIONADOS COM SUCESSO!")
            print("=" * 80)
            print()
            print("🚀 Próximos passos:")
            print("   1. Criar service de lançamento (LancamentoOdooService)")
            print("   2. Criar rota para lançar frete no Odoo")
            print("   3. Adicionar botão na interface web")
            print()

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    adicionar_campos_odoo()
