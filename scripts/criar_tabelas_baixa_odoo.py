#!/usr/bin/env python3
"""
Script para criar as tabelas de baixa/reconciliação do Odoo.

Tabelas criadas:
1. contas_a_receber_reconciliacao - Espelha account.partial.reconcile
2. contas_a_receber_pagamento - Espelha account.payment
3. contas_a_receber_documento - Espelha account.move
4. contas_a_receber_linha_credito - Espelha account.move.line (créditos)

Autor: Sistema de Fretes
Data: 2025-11-28
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    """Cria as tabelas no banco de dados"""
    app = create_app()

    with app.app_context():
        print("="*80)
        print("CRIANDO TABELAS DE BAIXA/RECONCILIAÇÃO DO ODOO")
        print("="*80)

        # Verificar se as tabelas já existem
        tabelas = [
            'contas_a_receber_reconciliacao',
            'contas_a_receber_pagamento',
            'contas_a_receber_documento',
            'contas_a_receber_linha_credito'
        ]

        for tabela in tabelas:
            existe = db.session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{tabela}'
                )
            """)).scalar()

            if existe:
                print(f"⚠️  Tabela {tabela} já existe!")
            else:
                print(f"📋 Tabela {tabela} será criada...")

        # Criar todas as tabelas usando SQLAlchemy
        print("\n🔨 Criando tabelas via SQLAlchemy...")
        db.create_all()

        # Verificar criação
        print("\n✅ Verificando tabelas criadas:")
        for tabela in tabelas:
            existe = db.session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{tabela}'
                )
            """)).scalar()

            if existe:
                # Contar colunas
                colunas = db.session.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_name = '{tabela}'
                """)).scalar()
                print(f"   ✅ {tabela}: {colunas} colunas")
            else:
                print(f"   ❌ {tabela}: NÃO CRIADA!")

        print("\n" + "="*80)
        print("✅ PROCESSO CONCLUÍDO!")
        print("="*80)


def listar_colunas():
    """Lista todas as colunas das tabelas criadas"""
    app = create_app()

    with app.app_context():
        tabelas = [
            'contas_a_receber_reconciliacao',
            'contas_a_receber_pagamento',
            'contas_a_receber_documento',
            'contas_a_receber_linha_credito'
        ]

        for tabela in tabelas:
            print(f"\n{'='*60}")
            print(f"TABELA: {tabela}")
            print('='*60)

            colunas = db.session.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{tabela}'
                ORDER BY ordinal_position
            """)).fetchall()

            for col in colunas:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                print(f"  {col[0]}: {col[1]} ({nullable})")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabelas de baixa/reconciliação do Odoo')
    parser.add_argument('--listar', action='store_true', help='Apenas listar colunas das tabelas')

    args = parser.parse_args()

    if args.listar:
        listar_colunas()
    else:
        criar_tabelas()
