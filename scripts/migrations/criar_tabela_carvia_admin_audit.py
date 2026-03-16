"""
Migration: Criar tabela carvia_admin_audit
==========================================

Tabela de auditoria para acoes administrativas no modulo CarVia.
Registra hard deletes, type changes, re-links e edicoes admin com snapshot completo.

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_carvia_admin_audit.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text

app = create_app()


def verificar_tabela_existe():
    """Verifica se a tabela ja existe."""
    result = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_admin_audit'
        )
    """))
    return result.scalar()


def criar_tabela():
    """Cria a tabela carvia_admin_audit."""
    db.session.execute(text("""
        CREATE TABLE carvia_admin_audit (
            id SERIAL PRIMARY KEY,
            acao VARCHAR(30) NOT NULL,
            entidade_tipo VARCHAR(50) NOT NULL,
            entidade_id INTEGER NOT NULL,
            dados_snapshot JSONB NOT NULL,
            dados_relacionados JSONB,
            motivo TEXT NOT NULL,
            executado_por VARCHAR(100) NOT NULL,
            executado_em TIMESTAMP NOT NULL,
            detalhes JSONB
        )
    """))

    # Indices
    db.session.execute(text(
        "CREATE INDEX ix_carvia_audit_acao ON carvia_admin_audit (acao)"
    ))
    db.session.execute(text(
        "CREATE INDEX ix_carvia_audit_entidade ON carvia_admin_audit (entidade_tipo, entidade_id)"
    ))
    db.session.execute(text(
        "CREATE INDEX ix_carvia_audit_executado_em ON carvia_admin_audit (executado_em)"
    ))
    db.session.execute(text(
        "CREATE INDEX ix_carvia_audit_executado_por ON carvia_admin_audit (executado_por)"
    ))

    # Check constraint
    db.session.execute(text("""
        ALTER TABLE carvia_admin_audit
            ADD CONSTRAINT ck_carvia_audit_acao
            CHECK (acao IN ('HARD_DELETE', 'TYPE_CHANGE', 'RELINK', 'FIELD_EDIT', 'IMPORT_EDIT'))
    """))

    db.session.commit()


def main():
    with app.app_context():
        if verificar_tabela_existe():
            print("[OK] Tabela carvia_admin_audit ja existe. Nada a fazer.")
            return

        print("[...] Criando tabela carvia_admin_audit...")
        criar_tabela()
        print("[OK] Tabela carvia_admin_audit criada com sucesso.")

        # Verificar
        result = db.session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'carvia_admin_audit'
            ORDER BY ordinal_position
        """))
        cols = result.fetchall()
        print(f"\n[VERIFICACAO] {len(cols)} colunas criadas:")
        for col_name, col_type in cols:
            print(f"  - {col_name}: {col_type}")


if __name__ == '__main__':
    main()
