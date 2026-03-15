"""
Migration: Criar tabelas de categoria de moto para precificacao por unidade
Data: 2026-03-15
Descricao:
  - carvia_categorias_moto: Tipos/categorias de moto (Leve, Pesada, Scooter)
  - carvia_precos_categoria_moto: Preco fixo por unidade por tabela x categoria
  - carvia_modelos_moto.categoria_moto_id: FK para associar modelo a categoria
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_categorias_moto'"
        ")"
    ))
    existe_categorias = result.scalar()

    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_precos_categoria_moto'"
        ")"
    ))
    existe_precos = result.scalar()

    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = 'carvia_modelos_moto' "
        "  AND column_name = 'categoria_moto_id'"
        ")"
    ))
    existe_fk = result.scalar()

    print(f"[ANTES] carvia_categorias_moto existe: {existe_categorias}")
    print(f"[ANTES] carvia_precos_categoria_moto existe: {existe_precos}")
    print(f"[ANTES] carvia_modelos_moto.categoria_moto_id existe: {existe_fk}")

    return existe_categorias, existe_precos, existe_fk


def executar_migration(conn):
    """Executa DDL"""
    # 1. Tabela de categorias
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_categorias_moto (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(50) NOT NULL UNIQUE,
            descricao TEXT,
            ordem INTEGER NOT NULL DEFAULT 0,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100) NOT NULL
        )
    """))
    print("[OK] carvia_categorias_moto criada")

    # 2. FK em modelos_moto (tabela pode nao existir em banco local/teste)
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_modelos_moto'"
        ")"
    ))
    if not result.scalar():
        print("[SKIP] carvia_modelos_moto nao existe — FK sera criada quando a tabela existir")
    else:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = 'carvia_modelos_moto' "
            "  AND column_name = 'categoria_moto_id'"
            ")"
        ))
        if not result.scalar():
            conn.execute(db.text("""
                ALTER TABLE carvia_modelos_moto
                    ADD COLUMN categoria_moto_id INTEGER
                    REFERENCES carvia_categorias_moto(id)
            """))
            print("[OK] carvia_modelos_moto.categoria_moto_id adicionado")
        else:
            print("[SKIP] carvia_modelos_moto.categoria_moto_id ja existe")

    # 3. Tabela de precos (depende de carvia_tabelas_frete)
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_tabelas_frete'"
        ")"
    ))
    if not result.scalar():
        print("[SKIP] carvia_tabelas_frete nao existe — precos_categoria_moto sera criada depois")
    else:
        conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS carvia_precos_categoria_moto (
                id SERIAL PRIMARY KEY,
                tabela_frete_id INTEGER NOT NULL
                    REFERENCES carvia_tabelas_frete(id) ON DELETE CASCADE,
                categoria_moto_id INTEGER NOT NULL
                    REFERENCES carvia_categorias_moto(id) ON DELETE CASCADE,
                valor_unitario NUMERIC(15,2) NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL,
                CONSTRAINT uq_carvia_preco_cat_moto
                    UNIQUE (tabela_frete_id, categoria_moto_id)
            )
        """))
        print("[OK] carvia_precos_categoria_moto criada")

        # Indices da tabela de precos
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_preco_cat_moto_tabela
                ON carvia_precos_categoria_moto(tabela_frete_id)
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_preco_cat_moto_cat
                ON carvia_precos_categoria_moto(categoria_moto_id)
        """))
        print("[OK] Indices precos criados")

    # 4. Indice em modelos_moto (se tabela e coluna existem)
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = 'carvia_modelos_moto' "
        "  AND column_name = 'categoria_moto_id'"
        ")"
    ))
    if result.scalar():
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_modelos_moto_cat
                ON carvia_modelos_moto(categoria_moto_id)
        """))
        print("[OK] Indice modelos_moto.categoria_moto_id criado")
    else:
        print("[SKIP] Indice modelos_moto — coluna nao existe")


def verificar_depois(conn):
    """Verifica estado apos migration"""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_categorias_moto'"
        ")"
    ))
    print(f"[DEPOIS] carvia_categorias_moto existe: {result.scalar()}")

    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_precos_categoria_moto'"
        ")"
    ))
    print(f"[DEPOIS] carvia_precos_categoria_moto existe: {result.scalar()}")

    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = 'carvia_modelos_moto' "
        "  AND column_name = 'categoria_moto_id'"
        ")"
    ))
    print(f"[DEPOIS] carvia_modelos_moto.categoria_moto_id existe: {result.scalar()}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: Criar tabelas categoria moto")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
