"""
Migration: Renomear uf → uf_destino + adicionar uf_origem em carvia_cidades_atendidas
Tabela vazia em producao — DDL segura.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_cidades_atendidas'
        ORDER BY ordinal_position
    """))
    colunas = [r[0] for r in result]
    print(f"Colunas atuais: {colunas}")

    count = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_cidades_atendidas"
    )).scalar()
    print(f"Registros na tabela: {count}")

    return colunas


def executar():
    """Executa a migration."""
    colunas = verificar_antes()

    # 1. Renomear uf → uf_destino
    if 'uf' in colunas and 'uf_destino' not in colunas:
        db.session.execute(text(
            "ALTER TABLE carvia_cidades_atendidas RENAME COLUMN uf TO uf_destino"
        ))
        print("✓ Coluna uf renomeada para uf_destino")
    elif 'uf_destino' in colunas:
        print("→ Coluna uf_destino ja existe (skip)")
    else:
        print("⚠ Coluna uf nao encontrada e uf_destino tambem nao")

    # 2. Adicionar uf_origem (default SP para dados existentes)
    if 'uf_origem' not in colunas:
        db.session.execute(text(
            "ALTER TABLE carvia_cidades_atendidas "
            "ADD COLUMN uf_origem VARCHAR(2) DEFAULT 'SP'"
        ))
        db.session.execute(text(
            "UPDATE carvia_cidades_atendidas SET uf_origem = 'SP' "
            "WHERE uf_origem IS NULL"
        ))
        print("✓ Coluna uf_origem adicionada")
    else:
        print("→ Coluna uf_origem ja existe (skip)")

    # 3. Dropar unique antigo e indice antigo
    db.session.execute(text(
        "ALTER TABLE carvia_cidades_atendidas "
        "DROP CONSTRAINT IF EXISTS uq_carvia_cidade_tabela"
    ))
    db.session.execute(text("DROP INDEX IF EXISTS ix_carvia_cidade_uf"))
    print("✓ Constraint e indice antigos removidos")

    # 4. Criar unique novo e indices
    db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_carvia_cidade_tabela_origem'
            ) THEN
                ALTER TABLE carvia_cidades_atendidas
                    ADD CONSTRAINT uq_carvia_cidade_tabela_origem
                    UNIQUE (codigo_ibge, nome_tabela, uf_origem);
            END IF;
        END $$
    """))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_carvia_cidade_uf_destino "
        "ON carvia_cidades_atendidas (uf_destino)"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_carvia_cidade_uf_origem "
        "ON carvia_cidades_atendidas (uf_origem)"
    ))
    print("✓ Nova constraint e indices criados")

    # 5. NOT NULL em uf_origem (tabela vazia)
    db.session.execute(text(
        "ALTER TABLE carvia_cidades_atendidas "
        "ALTER COLUMN uf_origem SET NOT NULL"
    ))
    print("✓ uf_origem definido como NOT NULL")

    db.session.commit()
    print("\n✓ Migration concluida com sucesso!")


def verificar_depois():
    """Verifica estado apos migration."""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_cidades_atendidas'
        ORDER BY ordinal_position
    """))
    colunas = [r[0] for r in result]
    print(f"\nColunas apos migration: {colunas}")

    assert 'uf_destino' in colunas, "uf_destino nao encontrada!"
    assert 'uf_origem' in colunas, "uf_origem nao encontrada!"
    assert 'uf' not in colunas, "coluna uf ainda existe!"
    print("✓ Verificacao OK")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        executar()
        verificar_depois()
