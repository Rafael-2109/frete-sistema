"""
Migration: Origens globais + destinos provisorios
Data: 30/03/2026
Descricao: Permite origens compartilhadas (cliente_id NULL) e destinos
           provisorios sem CNPJ (cnpj NULL, provisorio=TRUE).

Alteracoes em carvia_cliente_enderecos:
  1. cliente_id -> nullable (origens globais nao tem cliente)
  2. cnpj -> nullable (destinos provisorios)
  3. Nova coluna provisorio BOOLEAN
  4. Constraints parciais substituem unique antiga

Uso:
    source .venv/bin/activate && python scripts/migrations/carvia_origens_globais_provisorio.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_estado_antes():
    """Verifica estado atual da tabela antes da migration."""
    result = db.session.execute(text("""
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_name = 'carvia_cliente_enderecos'
          AND column_name IN ('cliente_id', 'cnpj', 'provisorio')
        ORDER BY column_name
    """))
    rows = result.fetchall()
    print("\n  Estado ANTES:")
    for col, nullable, dtype in rows:
        print(f"    {col}: nullable={nullable}, type={dtype}")
    # Verificar se coluna provisorio ja existe
    cols = [r[0] for r in rows]
    return 'provisorio' in cols


def verificar_estado_depois():
    """Verifica estado final."""
    result = db.session.execute(text("""
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_name = 'carvia_cliente_enderecos'
          AND column_name IN ('cliente_id', 'cnpj', 'provisorio')
        ORDER BY column_name
    """))
    rows = result.fetchall()
    print("\n  Estado DEPOIS:")
    for col, nullable, dtype in rows:
        print(f"    {col}: nullable={nullable}, type={dtype}")

    # Verificar indices
    result2 = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_cliente_enderecos'
          AND indexname LIKE '%carvia_end%'
        ORDER BY indexname
    """))
    indices = [r[0] for r in result2.fetchall()]
    print(f"\n  Indices parciais criados: {indices}")


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("Migration: Origens globais + destinos provisorios")
            print("=" * 60)

            provisorio_existe = verificar_estado_antes()

            # 1. Tornar cliente_id nullable
            print("\n[1/7] Tornando cliente_id nullable...")
            db.session.execute(text("""
                ALTER TABLE carvia_cliente_enderecos
                  ALTER COLUMN cliente_id DROP NOT NULL
            """))

            # 2. Tornar cnpj nullable
            print("[2/7] Tornando cnpj nullable...")
            db.session.execute(text("""
                ALTER TABLE carvia_cliente_enderecos
                  ALTER COLUMN cnpj DROP NOT NULL
            """))

            # 3. Adicionar coluna provisorio
            if not provisorio_existe:
                print("[3/7] Adicionando coluna provisorio...")
                db.session.execute(text("""
                    ALTER TABLE carvia_cliente_enderecos
                      ADD COLUMN provisorio BOOLEAN NOT NULL DEFAULT FALSE
                """))
            else:
                print("[3/7] Coluna provisorio ja existe, pulando.")

            # 4. Drop unique constraint antiga
            print("[4/7] Removendo unique constraint antiga...")
            db.session.execute(text("""
                ALTER TABLE carvia_cliente_enderecos
                  DROP CONSTRAINT IF EXISTS uq_carvia_cliente_endereco
            """))

            # 5. Unique parcial: destinos por cliente
            print("[5/7] Criando unique parcial (cliente+cnpj+tipo)...")
            db.session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_end_cliente_cnpj_tipo
                  ON carvia_cliente_enderecos (cliente_id, cnpj, tipo)
                  WHERE cnpj IS NOT NULL AND cliente_id IS NOT NULL
            """))

            # 6. Unique parcial: origens globais
            print("[6/7] Criando unique parcial (origens globais)...")
            db.session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_end_origem_global
                  ON carvia_cliente_enderecos (cnpj)
                  WHERE tipo = 'ORIGEM' AND cliente_id IS NULL AND cnpj IS NOT NULL
            """))

            # 7. Index para busca de origens globais
            print("[7/7] Criando index para origens globais...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_carvia_end_origem_global
                  ON carvia_cliente_enderecos (tipo, provisorio)
                  WHERE cliente_id IS NULL
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
