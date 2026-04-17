"""
Migration: Coluna `ativo` em carvia_cliente_enderecos + recriacao de indices parciais
Data: 16/04/2026

Objetivo:
  1. Adicionar coluna `ativo BOOLEAN NOT NULL DEFAULT TRUE` (soft delete).
  2. Recriar unique partial indices para incluir AND ativo = TRUE (senao registro
     desativado continua bloqueando cadastro correto).

Uso:
    source .venv/bin/activate && python scripts/migrations/carvia_endereco_ativo.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_estado_antes():
    """Verifica estado atual antes da migration."""
    col_result = db.session.execute(text("""
        SELECT column_name, is_nullable, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'carvia_cliente_enderecos'
          AND column_name = 'ativo'
    """))
    col_rows = col_result.fetchall()
    ativo_existe = bool(col_rows)

    idx_result = db.session.execute(text("""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'carvia_cliente_enderecos'
          AND indexname IN ('uq_carvia_end_cliente_cnpj_tipo', 'uq_carvia_end_origem_global')
        ORDER BY indexname
    """))
    idx_rows = idx_result.fetchall()

    print("\n  Estado ANTES:")
    print(f"    Coluna 'ativo' existe: {ativo_existe}")
    if col_rows:
        for name, nullable, dtype, default in col_rows:
            print(f"      {name}: nullable={nullable}, type={dtype}, default={default}")
    print(f"    Indices parciais atuais:")
    for name, defn in idx_rows:
        print(f"      {name}: {defn}")

    return ativo_existe


def verificar_estado_depois():
    """Verifica estado final."""
    col_result = db.session.execute(text("""
        SELECT column_name, is_nullable, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'carvia_cliente_enderecos'
          AND column_name = 'ativo'
    """))
    col_rows = col_result.fetchall()

    idx_result = db.session.execute(text("""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = 'carvia_cliente_enderecos'
          AND indexname IN (
              'uq_carvia_end_cliente_cnpj_tipo',
              'uq_carvia_end_origem_global',
              'ix_carvia_endereco_ativo'
          )
        ORDER BY indexname
    """))
    idx_rows = idx_result.fetchall()

    count_result = db.session.execute(text("""
        SELECT COUNT(*) FROM carvia_cliente_enderecos WHERE ativo = TRUE
    """))
    total_ativos = count_result.scalar()

    print("\n  Estado DEPOIS:")
    print(f"    Coluna 'ativo':")
    for name, nullable, dtype, default in col_rows:
        print(f"      {name}: nullable={nullable}, type={dtype}, default={default}")
    print(f"    Enderecos marcados como ativos: {total_ativos}")
    print(f"    Indices parciais:")
    for name, defn in idx_rows:
        print(f"      {name}:")
        print(f"        {defn}")


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("Migration: Coluna ativo + indices parciais com ativo=TRUE")
            print("=" * 60)

            ativo_existe = verificar_estado_antes()

            # 1. Adicionar coluna ativo
            if not ativo_existe:
                print("\n[1/5] Adicionando coluna ativo (DEFAULT TRUE)...")
                db.session.execute(text("""
                    ALTER TABLE carvia_cliente_enderecos
                      ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT TRUE
                """))
            else:
                print("\n[1/5] Coluna ativo ja existe, pulando.")

            # 2. Dropar indices antigos
            print("[2/5] Dropando indices antigos (uq_carvia_end_cliente_cnpj_tipo, uq_carvia_end_origem_global)...")
            db.session.execute(text("DROP INDEX IF EXISTS uq_carvia_end_cliente_cnpj_tipo"))
            db.session.execute(text("DROP INDEX IF EXISTS uq_carvia_end_origem_global"))

            # 3. Recriar uq_carvia_end_cliente_cnpj_tipo com ativo=TRUE
            print("[3/5] Recriando uq_carvia_end_cliente_cnpj_tipo com AND ativo = TRUE...")
            db.session.execute(text("""
                CREATE UNIQUE INDEX uq_carvia_end_cliente_cnpj_tipo
                  ON carvia_cliente_enderecos (cliente_id, cnpj, tipo)
                  WHERE cnpj IS NOT NULL AND cliente_id IS NOT NULL AND ativo = TRUE
            """))

            # 4. Recriar uq_carvia_end_origem_global com ativo=TRUE
            print("[4/5] Recriando uq_carvia_end_origem_global com AND ativo = TRUE...")
            db.session.execute(text("""
                CREATE UNIQUE INDEX uq_carvia_end_origem_global
                  ON carvia_cliente_enderecos (cnpj)
                  WHERE tipo = 'ORIGEM' AND cliente_id IS NULL AND cnpj IS NOT NULL AND ativo = TRUE
            """))

            # 5. Index auxiliar para localizar inativos
            print("[5/5] Criando ix_carvia_endereco_ativo (parcial para inativos)...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_carvia_endereco_ativo
                  ON carvia_cliente_enderecos (ativo)
                  WHERE ativo = FALSE
            """))

            db.session.commit()
            verificar_estado_depois()

            print("\n" + "=" * 60)
            print("Migration concluida com sucesso!")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO: {e}")
            raise


if __name__ == '__main__':
    executar_migration()
