"""
Migration: Backfill de linking cross-documento CarVia
======================================================

Popula FKs em registros existentes:
1. carvia_fatura_cliente_itens: resolve operacao_id e nf_id por cte_numero e nf_numero
2. carvia_fatura_transportadora_itens: gera itens a partir de subcontratos vinculados

PRE-REQUISITO: carvia_linking_v1_schema.py deve ter sido executado ANTES.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/carvia_linking_v2_backfill.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_tabela_existe(conn, tabela):
    """Verifica se tabela existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :tabela
        )
    """), {'tabela': tabela})
    return result.scalar()


def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se coluna existe na tabela."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def run_backfill():
    app = create_app()
    with app.app_context():

        print("=" * 60)
        print("Migration: CarVia Linking v2 — Backfill")
        print("=" * 60)

        # Verificar pre-requisitos
        conn = db.session.connection()
        if not verificar_coluna_existe(conn, 'carvia_fatura_cliente_itens', 'operacao_id'):
            print("[ERRO] Coluna operacao_id nao existe em carvia_fatura_cliente_itens.")
            print("       Execute carvia_linking_v1_schema.py primeiro.")
            return

        if not verificar_tabela_existe(conn, 'carvia_fatura_transportadora_itens'):
            print("[ERRO] Tabela carvia_fatura_transportadora_itens nao existe.")
            print("       Execute carvia_linking_v1_schema.py primeiro.")
            return

        from app.carvia.services.linking_service import LinkingService
        linker = LinkingService()

        print("\n--- Backfill completo ---")
        stats = linker.backfill_todas_faturas()

        print(f"\n  Faturas cliente processadas: {stats['faturas_cliente']}")
        print(f"  Operacoes resolvidas: {stats['operacoes_resolvidas']}")
        print(f"  NFs resolvidas: {stats['nfs_resolvidas']}")
        print(f"  Faturas transportadora processadas: {stats['faturas_transportadora']}")
        print(f"  Itens transportadora criados: {stats['itens_transportadora_criados']}")

        db.session.commit()

        # Verificacao final
        print("\n--- Verificacao final ---")

        # Contar itens com FKs populadas
        result = conn.execute(text("""
            SELECT
                count(*) AS total,
                count(operacao_id) AS com_operacao,
                count(nf_id) AS com_nf
            FROM carvia_fatura_cliente_itens
        """))
        row = result.fetchone()
        print(f"  carvia_fatura_cliente_itens: total={row[0]}, com_operacao={row[1]}, com_nf={row[2]}")

        result = conn.execute(text("""
            SELECT count(*) FROM carvia_fatura_transportadora_itens
        """))
        count = result.scalar()
        print(f"  carvia_fatura_transportadora_itens: total={count}")

        print("\n[SUCESSO] Backfill concluido!")


if __name__ == '__main__':
    run_backfill()
