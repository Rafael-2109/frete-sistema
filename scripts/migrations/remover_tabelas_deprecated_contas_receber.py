#!/usr/bin/env python3
"""
Script para Remover Tabelas Deprecated de Contas a Receber
============================================================

Remove as tabelas que eram usadas apenas pela rota órfã api_listar_baixas
e pelo script antigo de importação de baixas.

TABELAS A REMOVER:
1. contas_a_receber_pagamento - ContasAReceberPagamento
2. contas_a_receber_documento - ContasAReceberDocumento
3. contas_a_receber_linha_credito - ContasAReceberLinhaCredito

COLUNAS A REMOVER (de contas_a_receber_reconciliacao):
- payment_id (FK para tabela que será removida)
- documento_id (FK para tabela que será removida)
- Campos legados: debit_amount_currency, credit_amount_currency, etc.

MOTIVO:
O novo modal comparativo usa apenas ContasAReceberReconciliacao.
As outras tabelas eram para exibição detalhada que nunca foi implementada.

IMPORTANTE: Execute este script ANTES de remover os models do código.

Data: 2025-11-28
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime


def verificar_tabelas_existem():
    """Verifica quais tabelas existem antes de tentar remover"""
    tabelas_para_verificar = [
        'contas_a_receber_pagamento',
        'contas_a_receber_documento',
        'contas_a_receber_linha_credito'
    ]

    existentes = []

    for tabela in tabelas_para_verificar:
        resultado = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = '{tabela}'
            );
        """))
        existe = resultado.scalar()
        if existe:
            existentes.append(tabela)
            print(f"   ✅ {tabela} - EXISTE")
        else:
            print(f"   ⚪ {tabela} - não existe")

    return existentes


def verificar_colunas_deprecated():
    """Verifica quais colunas deprecated existem em contas_a_receber_reconciliacao"""
    colunas_deprecated = [
        'payment_id',           # FK para tabela que será removida
        'documento_id',         # FK para tabela que será removida
        'debit_amount_currency',
        'credit_amount_currency',
        'debit_currency',
        'credit_currency',
        'full_reconcile_id',    # Não usado no modal
        'exchange_move_id',     # Não usado no modal
        'company_name',         # Redundante
        'odoo_create_uid',
        'odoo_create_user',
        'odoo_write_uid',
        'odoo_write_user'
    ]

    existentes = []

    for coluna in colunas_deprecated:
        resultado = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'contas_a_receber_reconciliacao'
                AND column_name = '{coluna}'
            );
        """))
        existe = resultado.scalar()
        if existe:
            existentes.append(coluna)

    return existentes


def contar_registros(tabela):
    """Conta registros em uma tabela"""
    try:
        resultado = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
        return resultado.scalar()
    except Exception:
        return 0


def remover_fks_reconciliacao():
    """Remove FKs de payment_id e documento_id antes de dropar as tabelas"""
    print("\n📋 Removendo FKs da tabela contas_a_receber_reconciliacao...")

    # Listar constraints da tabela
    resultado = db.session.execute(text("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'contas_a_receber_reconciliacao'::regclass
        AND contype = 'f'
    """))

    constraints = [row[0] for row in resultado]

    for constraint in constraints:
        if 'payment' in constraint.lower() or 'documento' in constraint.lower():
            print(f"   Removendo FK: {constraint}")
            db.session.execute(text(f"""
                ALTER TABLE contas_a_receber_reconciliacao
                DROP CONSTRAINT IF EXISTS "{constraint}"
            """))

    db.session.commit()
    print("   ✅ FKs removidas")


def remover_colunas_deprecated():
    """Remove colunas deprecated de contas_a_receber_reconciliacao"""
    colunas_existentes = verificar_colunas_deprecated()

    if not colunas_existentes:
        print("\n⚪ Nenhuma coluna deprecated encontrada em contas_a_receber_reconciliacao")
        return

    print(f"\n📋 Removendo {len(colunas_existentes)} colunas deprecated de contas_a_receber_reconciliacao...")

    for coluna in colunas_existentes:
        try:
            db.session.execute(text(f"""
                ALTER TABLE contas_a_receber_reconciliacao
                DROP COLUMN IF EXISTS {coluna}
            """))
            print(f"   ✅ Coluna {coluna} removida")
        except Exception as e:
            print(f"   ❌ Erro ao remover {coluna}: {e}")
            db.session.rollback()

    db.session.commit()


def remover_tabelas(tabelas):
    """Remove as tabelas deprecated"""
    if not tabelas:
        print("\n⚪ Nenhuma tabela para remover")
        return

    print(f"\n📋 Removendo {len(tabelas)} tabelas deprecated...")

    for tabela in tabelas:
        try:
            # Verificar se tem registros
            count = contar_registros(tabela)
            print(f"\n   Tabela: {tabela}")
            print(f"   Registros: {count}")

            # Dropar tabela
            db.session.execute(text(f"DROP TABLE IF EXISTS {tabela} CASCADE"))
            db.session.commit()
            print(f"   ✅ Tabela {tabela} removida com sucesso")

        except Exception as e:
            print(f"   ❌ Erro ao remover {tabela}: {e}")
            db.session.rollback()


def main():
    """Função principal"""
    print("=" * 70)
    print("REMOÇÃO DE TABELAS DEPRECATED - CONTAS A RECEBER")
    print("=" * 70)
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    app = create_app()

    with app.app_context():
        # 1. Verificar tabelas existentes
        print("\n📊 Verificando tabelas existentes...")
        tabelas_existentes = verificar_tabelas_existem()

        if not tabelas_existentes:
            print("\n✅ Nenhuma tabela deprecated encontrada. Nada a fazer.")
            return

        # 2. Mostrar resumo
        print(f"\n📋 RESUMO:")
        print(f"   Tabelas a remover: {len(tabelas_existentes)}")
        for tabela in tabelas_existentes:
            count = contar_registros(tabela)
            print(f"     - {tabela}: {count} registros")

        # 3. Remover FKs da reconciliacao
        remover_fks_reconciliacao()

        # 4. Remover colunas deprecated
        remover_colunas_deprecated()

        # 5. Remover tabelas
        remover_tabelas(tabelas_existentes)

        # 6. Resumo final
        print("\n" + "=" * 70)
        print("✅ REMOÇÃO CONCLUÍDA")
        print("=" * 70)
        print(f"\nFim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n⚠️  PRÓXIMOS PASSOS:")
        print("   1. Remova as classes do models.py:")
        print("      - ContasAReceberPagamento")
        print("      - ContasAReceberDocumento")
        print("      - ContasAReceberLinhaCredito")
        print("   2. Remova a rota api_listar_baixas de contas_receber_api.py")
        print("   3. Atualize o script importar_baixas_odoo.py")


if __name__ == '__main__':
    main()
