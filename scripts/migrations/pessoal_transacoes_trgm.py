"""
Migration: extensao pg_trgm + indice GIN em pessoal_transacoes.historico_completo.

Acelera buscas ILIKE '%texto%' na tabela de transacoes pessoais.
Parte da Fase 1 (busca global e filtros avancados) do modulo pessoal.

Executar: python scripts/migrations/pessoal_transacoes_trgm.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


INDICE_NOME = 'idx_pessoal_transacoes_hist_completo_trgm'


def _indice_existe():
    rows = db.session.execute(text("""
        SELECT 1
          FROM pg_indexes
         WHERE schemaname = 'public'
           AND tablename = 'pessoal_transacoes'
           AND indexname = :nome
    """), {'nome': INDICE_NOME}).fetchall()
    return bool(rows)


def _extensao_existe():
    rows = db.session.execute(text("""
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    """)).fetchall()
    return bool(rows)


def migrar():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("MIGRATION: pessoal_transacoes pg_trgm")
        print("=" * 60)

        ext_antes = _extensao_existe()
        idx_antes = _indice_existe()
        print(f"\n[BEFORE] extensao pg_trgm: {ext_antes}")
        print(f"[BEFORE] indice {INDICE_NOME}: {idx_antes}")

        if not ext_antes:
            print("\n[1/2] Criando extensao pg_trgm...")
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        else:
            print("\n[1/2] Extensao pg_trgm ja existe.")

        if not idx_antes:
            print("\n[2/2] Criando indice GIN trigram...")
            db.session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {INDICE_NOME}
                  ON pessoal_transacoes
                  USING gin (historico_completo gin_trgm_ops);
            """))
        else:
            print("\n[2/2] Indice ja existe.")

        db.session.commit()

        print("\n" + "=" * 60)
        print(f"[AFTER] extensao pg_trgm: {_extensao_existe()}")
        print(f"[AFTER] indice {INDICE_NOME}: {_indice_existe()}")
        print("=" * 60)
        print("\nMigration concluida!")


if __name__ == '__main__':
    migrar()
