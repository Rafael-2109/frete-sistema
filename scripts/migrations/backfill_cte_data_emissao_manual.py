"""
Backfill: cte_data_emissao para CTes CarVia criados manualmente
================================================================

Data fix (sem DDL) — preenche cte_data_emissao onde NULL usando
a maior data_emissao das NFs vinculadas via junction carvia_operacao_nfs.

Idempotente: so atualiza registros com cte_data_emissao IS NULL
que possuem NFs vinculadas com data_emissao preenchida.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def backfill_cte_data_emissao():
    """Preenche cte_data_emissao em operacoes manuais a partir das NFs vinculadas."""

    # Buscar operacoes sem cte_data_emissao que tem NFs com data_emissao
    resultado = db.session.execute(text("""
        SELECT
            o.id,
            o.cte_numero,
            MAX(nf.data_emissao) AS max_data_emissao,
            COUNT(nf.id) AS qtd_nfs
        FROM carvia_operacoes o
        JOIN carvia_operacao_nfs j ON j.operacao_id = o.id
        JOIN carvia_nfs nf ON nf.id = j.nf_id
        WHERE o.cte_data_emissao IS NULL
          AND nf.data_emissao IS NOT NULL
        GROUP BY o.id, o.cte_numero
        ORDER BY o.id
    """))

    rows = resultado.fetchall()

    if not rows:
        print("Nenhuma operacao para atualizar. Todas ja possuem cte_data_emissao ou nao tem NFs com data.")
        return

    print(f"Encontradas {len(rows)} operacoes para atualizar:")
    print(f"{'ID':>6} | {'CTe':>10} | {'NFs':>4} | {'Data Emissao'}")
    print("-" * 50)

    for row in rows:
        print(f"{row.id:>6} | {row.cte_numero or 'N/A':>10} | {row.qtd_nfs:>4} | {row.max_data_emissao}")

    # Executar UPDATE em batch
    updated = db.session.execute(text("""
        UPDATE carvia_operacoes o
        SET cte_data_emissao = sub.max_data_emissao
        FROM (
            SELECT
                j.operacao_id,
                MAX(nf.data_emissao) AS max_data_emissao
            FROM carvia_operacao_nfs j
            JOIN carvia_nfs nf ON nf.id = j.nf_id
            WHERE nf.data_emissao IS NOT NULL
            GROUP BY j.operacao_id
        ) sub
        WHERE o.id = sub.operacao_id
          AND o.cte_data_emissao IS NULL
    """))

    db.session.commit()
    print(f"\n{updated.rowcount} operacoes atualizadas com sucesso.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Before
        before = db.session.execute(text(
            "SELECT COUNT(*) FROM carvia_operacoes WHERE cte_data_emissao IS NULL"
        )).scalar()
        print(f"BEFORE: {before} operacoes com cte_data_emissao NULL\n")

        backfill_cte_data_emissao()

        # After
        after = db.session.execute(text(
            "SELECT COUNT(*) FROM carvia_operacoes WHERE cte_data_emissao IS NULL"
        )).scalar()
        print(f"\nAFTER: {after} operacoes com cte_data_emissao NULL")
