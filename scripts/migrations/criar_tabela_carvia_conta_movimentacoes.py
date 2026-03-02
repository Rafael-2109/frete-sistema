"""
Migration: Criar tabela carvia_conta_movimentacoes
===================================================

Registra movimentacoes financeiras da conta CarVia.
Saldo e calculado por SUM (nao armazenado).

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_carvia_conta_movimentacoes.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(db.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'carvia_conta_movimentacoes'
        )
    """)).scalar()

    if result:
        print("[INFO] Tabela carvia_conta_movimentacoes ja existe. Migration sera idempotente.")
        return True
    else:
        print("[INFO] Tabela carvia_conta_movimentacoes NAO existe. Sera criada.")
        return False


def executar():
    """Cria tabela carvia_conta_movimentacoes."""
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_conta_movimentacoes (
            id SERIAL PRIMARY KEY,
            tipo_doc VARCHAR(30) NOT NULL,
            doc_id INTEGER NOT NULL,
            tipo_movimento VARCHAR(10) NOT NULL,
            valor NUMERIC(15, 2) NOT NULL,
            descricao VARCHAR(500),
            criado_por VARCHAR(100) NOT NULL,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT uq_carvia_mov_tipo_doc UNIQUE (tipo_doc, doc_id),
            CONSTRAINT ck_carvia_mov_tipo CHECK (tipo_movimento IN ('CREDITO', 'DEBITO')),
            CONSTRAINT ck_carvia_mov_valor CHECK (valor > 0)
        )
    """))

    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_mov_criado_em
        ON carvia_conta_movimentacoes (criado_em)
    """))

    db.session.commit()
    print("[OK] Tabela carvia_conta_movimentacoes criada com sucesso.")


def verificar_depois():
    """Verifica estado apos a migration."""
    result = db.session.execute(db.text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'carvia_conta_movimentacoes'
        ORDER BY ordinal_position
    """)).fetchall()

    print(f"\n[VERIFICACAO] Tabela carvia_conta_movimentacoes — {len(result)} colunas:")
    for col_name, data_type in result:
        print(f"  - {col_name}: {data_type}")

    # Verificar constraints
    constraints = db.session.execute(db.text("""
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_name = 'carvia_conta_movimentacoes'
        ORDER BY constraint_name
    """)).fetchall()

    print(f"\n[VERIFICACAO] Constraints: {len(constraints)}")
    for name, ctype in constraints:
        print(f"  - {name}: {ctype}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        ja_existe = verificar_antes()
        if not ja_existe:
            executar()
        verificar_depois()
        print("\n[DONE] Migration concluida.")
