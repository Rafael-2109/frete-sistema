# -*- coding: utf-8 -*-
"""
Migration: Adicionar campos de favorecido ao extrato_item
=========================================================

8 novas colunas para resolver favorecido em pagamentos de saída.

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_campos_favorecido_extrato_item.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se uma coluna existe na tabela."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def verificar_indice_existe(conn, nome_indice):
    """Verifica se um índice existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = :nome
        )
    """), {'nome': nome_indice})
    return result.scalar()


def executar():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        # =====================================================================
        # BEFORE: Verificar estado atual
        # =====================================================================
        colunas_novas = [
            ('odoo_partner_id', 'INTEGER'),
            ('odoo_partner_name', 'VARCHAR(255)'),
            ('odoo_partner_cnpj', 'VARCHAR(20)'),
            ('favorecido_cnpj', 'VARCHAR(20)'),
            ('favorecido_nome', 'VARCHAR(255)'),
            ('favorecido_metodo', 'VARCHAR(30)'),
            ('favorecido_confianca', 'INTEGER'),
            ('categoria_pagamento', 'VARCHAR(30)'),
        ]

        indices_novos = [
            ('idx_extrato_item_favorecido_cnpj', 'favorecido_cnpj'),
            ('idx_extrato_item_categoria_pag', 'categoria_pagamento'),
            ('idx_extrato_item_odoo_partner', 'odoo_partner_id'),
        ]

        print("=" * 60)
        print("MIGRATION: Campos de Favorecido em extrato_item")
        print("=" * 60)

        # =====================================================================
        # EXECUTE: Adicionar colunas
        # =====================================================================
        for coluna, tipo in colunas_novas:
            if verificar_coluna_existe(conn, 'extrato_item', coluna):
                print(f"  [OK] Coluna '{coluna}' ja existe")
            else:
                conn.execute(text(
                    f"ALTER TABLE extrato_item ADD COLUMN {coluna} {tipo}"
                ))
                print(f"  [+] Coluna '{coluna}' ({tipo}) adicionada")

        # =====================================================================
        # EXECUTE: Criar indices
        # =====================================================================
        for nome_idx, coluna in indices_novos:
            if verificar_indice_existe(conn, nome_idx):
                print(f"  [OK] Indice '{nome_idx}' ja existe")
            else:
                conn.execute(text(
                    f"CREATE INDEX {nome_idx} ON extrato_item ({coluna})"
                ))
                print(f"  [+] Indice '{nome_idx}' criado")

        db.session.commit()

        # =====================================================================
        # AFTER: Verificar resultado
        # =====================================================================
        print("\n--- Verificacao pos-migration ---")
        for coluna, tipo in colunas_novas:
            existe = verificar_coluna_existe(conn, 'extrato_item', coluna)
            status = "OK" if existe else "FALHA"
            print(f"  [{status}] {coluna}")

        for nome_idx, _ in indices_novos:
            existe = verificar_indice_existe(conn, nome_idx)
            status = "OK" if existe else "FALHA"
            print(f"  [{status}] {nome_idx}")

        print("\nMigration concluida com sucesso!")


if __name__ == '__main__':
    executar()
