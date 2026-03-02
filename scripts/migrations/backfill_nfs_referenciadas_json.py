"""
Migration: Backfill de nfs_referenciadas_json em carvia_operacoes
==================================================================

Popula o campo nfs_referenciadas_json nas operacoes existentes que
JA TEM junctions (carvia_operacao_nfs) vinculadas.

Operacoes SEM junctions (CTes importados antes de NFs que nunca vieram)
NAO podem ser preenchidas — seria necessario re-importar os CTe XMLs.

Prerequisito: add_nfs_referenciadas_json_operacoes.py ja executado.

Idempotencia:
- So atualiza operacoes onde nfs_referenciadas_json IS NULL
- Dados montados a partir de junctions existentes
- Pode rodar N vezes com resultado identico

Execucao:
    source .venv/bin/activate
    python scripts/migrations/backfill_nfs_referenciadas_json.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_backfill():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        print("=" * 60)
        print("Backfill: nfs_referenciadas_json em carvia_operacoes")
        print("=" * 60)

        # Estado ANTES
        result = conn.execute(text("""
            SELECT
                count(*) AS total_operacoes,
                count(nfs_referenciadas_json) AS com_json,
                (SELECT count(DISTINCT operacao_id) FROM carvia_operacao_nfs) AS com_junctions
            FROM carvia_operacoes
        """))
        row = result.fetchone()
        print(f"\n--- Estado ANTES ---")
        print(f"  Total operacoes: {row[0]}")
        print(f"  Com nfs_referenciadas_json: {row[1]}")
        print(f"  Com junctions (operacoes distintas): {row[2]}")

        # Backfill: popular JSON a partir das junctions existentes
        print("\nPopulando nfs_referenciadas_json a partir de junctions...")
        result = conn.execute(text("""
            UPDATE carvia_operacoes o
            SET nfs_referenciadas_json = sub.refs_json
            FROM (
                SELECT
                    j.operacao_id,
                    json_agg(json_build_object(
                        'chave', nf.chave_acesso_nf,
                        'numero_nf', nf.numero_nf,
                        'cnpj_emitente', nf.cnpj_emitente
                    )) AS refs_json
                FROM carvia_operacao_nfs j
                JOIN carvia_nfs nf ON nf.id = j.nf_id
                GROUP BY j.operacao_id
            ) sub
            WHERE o.id = sub.operacao_id
              AND o.nfs_referenciadas_json IS NULL
        """))
        updated = result.rowcount
        print(f"  Operacoes atualizadas: {updated}")

        db.session.commit()

        # Estado DEPOIS
        result = conn.execute(text("""
            SELECT
                count(*) AS total_operacoes,
                count(nfs_referenciadas_json) AS com_json,
                count(*) - count(nfs_referenciadas_json) AS sem_json
            FROM carvia_operacoes
        """))
        row = result.fetchone()
        print(f"\n--- Estado DEPOIS ---")
        print(f"  Total operacoes: {row[0]}")
        print(f"  Com nfs_referenciadas_json: {row[1]}")
        print(f"  Sem nfs_referenciadas_json: {row[2]}")

        # Amostra
        result = conn.execute(text("""
            SELECT id, cte_numero, nfs_referenciadas_json
            FROM carvia_operacoes
            WHERE nfs_referenciadas_json IS NOT NULL
            LIMIT 3
        """))
        rows = result.fetchall()
        if rows:
            print(f"\n--- Amostra (3 primeiras) ---")
            for r in rows:
                print(f"  op={r[0]} cte={r[1]} json={r[2]}")

        # Operacoes sem JSON e sem junctions (orfas reais)
        result = conn.execute(text("""
            SELECT count(*) FROM carvia_operacoes o
            WHERE o.nfs_referenciadas_json IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM carvia_operacao_nfs j WHERE j.operacao_id = o.id
              )
        """))
        orfas = result.scalar()
        print(f"\n  Operacoes sem JSON e sem junctions (orfas): {orfas}")
        if orfas and orfas > 0:
            print(
                "  [INFO] Essas operacoes precisariam re-importar CTe XML "
                "para recuperar as referencias de NF."
            )

        print(f"\n[SUCESSO] Backfill concluido. {updated} operacoes atualizadas.")


if __name__ == '__main__':
    run_backfill()
