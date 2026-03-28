"""
Migration: Alterar UNIQUE constraint de pallet_nf_solucoes
Data: 2026-03-28
Fix: PYTHON-FLASK-A7 (UniqueViolation em chave_nfe_solucao)

Problema: unique=True em chave_nfe_solucao impede 1:N (1 devolução → N remessas)
Solução: Trocar UNIQUE simples por UNIQUE composto (chave_nfe_solucao, nf_remessa_id)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        # Verificar estado antes
        result = db.session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'pallet_nf_solucoes'
            AND indexdef ILIKE '%chave_nfe%'
        """))
        before = result.fetchall()
        print(f"Índices com chave_nfe ANTES: {len(before)}")
        for row in before:
            print(f"  {row[0]}: {row[1]}")

        # Executar migration
        print("\n1. Removendo UNIQUE constraint simples...")
        db.session.execute(text(
            "ALTER TABLE pallet_nf_solucoes "
            "DROP CONSTRAINT IF EXISTS pallet_nf_solucoes_chave_nfe_solucao_key"
        ))

        print("2. Removendo índice UNIQUE simples (se existir)...")
        db.session.execute(text(
            "DROP INDEX IF EXISTS ix_pallet_nf_solucoes_chave_nfe_solucao"
        ))

        print("3. Criando UNIQUE composto (chave_nfe_solucao, nf_remessa_id)...")
        db.session.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_pallet_nf_solucoes_chave_remessa "
            "ON pallet_nf_solucoes (chave_nfe_solucao, nf_remessa_id) "
            "WHERE chave_nfe_solucao IS NOT NULL AND ativo = true"
        ))

        db.session.commit()

        # Verificar estado depois
        result = db.session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'pallet_nf_solucoes'
            AND indexdef ILIKE '%chave_nfe%'
        """))
        after = result.fetchall()
        print(f"\nÍndices com chave_nfe DEPOIS: {len(after)}")
        for row in after:
            print(f"  {row[0]}: {row[1]}")

        print("\n✓ Migration concluída com sucesso!")


if __name__ == '__main__':
    run()
