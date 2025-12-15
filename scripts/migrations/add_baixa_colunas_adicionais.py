# -*- coding: utf-8 -*-
"""
Migracao: Adicionar colunas de baixa adicional (desconto, acordo, devolucao)
============================================================================

Adiciona na tabela baixa_titulo_item:
- desconto_concedido_excel, acordo_comercial_excel, devolucao_excel (entrada)
- payment_desconto_odoo_id/name, payment_acordo_odoo_id/name, payment_devolucao_odoo_id/name (resultado)

Autor: Sistema
Data: 2025-12-15
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRACAO: Adicionar colunas de baixa adicional")
            print("=" * 60)

            # Campos de entrada (Excel)
            campos_excel = [
                ("desconto_concedido_excel", "FLOAT DEFAULT 0"),
                ("acordo_comercial_excel", "FLOAT DEFAULT 0"),
                ("devolucao_excel", "FLOAT DEFAULT 0"),
            ]

            # Campos de resultado (Odoo)
            campos_odoo = [
                ("payment_desconto_odoo_id", "INTEGER"),
                ("payment_desconto_odoo_name", "VARCHAR(100)"),
                ("payment_acordo_odoo_id", "INTEGER"),
                ("payment_acordo_odoo_name", "VARCHAR(100)"),
                ("payment_devolucao_odoo_id", "INTEGER"),
                ("payment_devolucao_odoo_name", "VARCHAR(100)"),
            ]

            todos_campos = campos_excel + campos_odoo

            for campo, tipo in todos_campos:
                try:
                    sql = f"ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS {campo} {tipo};"
                    db.session.execute(text(sql))
                    print(f"  [OK] Campo '{campo}' adicionado")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                        print(f"  [SKIP] Campo '{campo}' ja existe")
                    else:
                        print(f"  [ERRO] Campo '{campo}': {e}")

            db.session.commit()
            print("\n[SUCESSO] Migracao concluida!")

        except Exception as e:
            print(f"\n[ERRO] Falha na migracao: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    executar_migracao()
