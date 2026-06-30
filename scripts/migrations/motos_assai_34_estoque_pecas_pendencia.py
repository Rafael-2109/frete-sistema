"""Migration 34: Estoque de Pecas + Pendencia categorizada (Spec 1 — back-end).

Cria 6 tabelas: assai_peca, assai_peca_modelo, assai_peca_compra,
assai_pendencia, assai_peca_compra_item, assai_estoque_movimento.

Idempotente (CREATE TABLE/INDEX IF NOT EXISTS). NAO consta no build.sh —
aplicar manualmente em prod (DATABASE_URL_PROD) + local (padrao 30/32/33).

Spec: docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'motos_assai_34_estoque_pecas_pendencia.sql',
)

TABELAS = [
    'assai_peca', 'assai_peca_modelo', 'assai_peca_compra',
    'assai_pendencia', 'assai_peca_compra_item', 'assai_estoque_movimento',
]


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        db.session.execute(text(sql))
        db.session.commit()

        # Validacao pos: 6 tabelas presentes
        existentes = {
            r[0] for r in db.session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY(:nomes)"
            ), {'nomes': TABELAS})
        }
        faltando = set(TABELAS) - existentes
        if faltando:
            print(f'[ERRO] Tabelas faltando: {sorted(faltando)}')
            sys.exit(1)
        print(f'[ok] Migration 34 aplicada. {len(existentes)}/6 tabelas presentes:')
        for t in TABELAS:
            print(f'  - {t}')

        idx = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE indexname = 'ix_assai_pendencia_aberta'"
        )).scalar()
        print(f'  indice parcial: {idx or "AUSENTE"}')


if __name__ == '__main__':
    main()
