"""
Migration: Cancelar emissões CTe pendentes órfãs.

Jobs foram enfileirados na queue 'ssw_carvia' que nenhum worker escutava.
Registros ficaram PENDENTE eternamente. Cancelar para desbloquear mutex
e permitir nova tentativa.

Uso:
    source .venv/bin/activate
    python scripts/migrations/cancelar_emissao_cte_pendentes.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.utils.timezone import agora_utc_naive


def run():
    app = create_app()
    with app.app_context():
        # Before
        resultado = db.session.execute(db.text(
            "SELECT id, nf_id, status, etapa, criado_em "
            "FROM carvia_emissao_cte "
            "WHERE status IN ('PENDENTE', 'EM_PROCESSAMENTO') "
            "ORDER BY id"
        ))
        pendentes = resultado.fetchall()

        if not pendentes:
            print("Nenhuma emissao PENDENTE/EM_PROCESSAMENTO encontrada.")
            return

        print(f"Encontradas {len(pendentes)} emissoes para cancelar:")
        for row in pendentes:
            print(f"  ID={row[0]} NF={row[1]} status={row[2]} etapa={row[3]} criado={row[4]}")

        # Update
        agora = agora_utc_naive()
        db.session.execute(db.text("""
            UPDATE carvia_emissao_cte
            SET status = 'CANCELADO',
                erro_ssw = COALESCE(erro_ssw, '') ||
                    'Cancelado: job enfileirado em queue sem consumidor (ssw_carvia)',
                atualizado_em = :agora
            WHERE status IN ('PENDENTE', 'EM_PROCESSAMENTO')
        """), {'agora': agora})
        db.session.commit()

        # After
        resultado = db.session.execute(db.text(
            "SELECT COUNT(*) FROM carvia_emissao_cte "
            "WHERE status IN ('PENDENTE', 'EM_PROCESSAMENTO')"
        ))
        restantes = resultado.scalar()
        print(f"\nConcluido. Pendentes restantes: {restantes}")


if __name__ == '__main__':
    run()
