"""Migration 28: cria tabela `assai_cce` (Carta de Correcao como entidade).

Motivacao: CCe pode chegar ANTES da NF correspondente. Precisa persistir com
flag `tem_nf` e ser aplicada via match reverso quando a NF for importada.

Spec interno: feature CCe avulsa (2026-05-13).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'motos_assai_28_cce_entidade.sql',
)


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        # Pre-check: tabela ja existe?
        existe = db.session.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'assai_cce'"
        )).first()
        if existe:
            print('[skip] Tabela assai_cce ja existe — migration idempotente, aplicando indexes/constraints.')

        db.session.execute(text(sql))
        db.session.commit()

        # Validacao pos
        count = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_cce"
        )).scalar()
        print(f'[ok] Migration 28 aplicada. assai_cce tem {count} registros.')

        # Indexes criados
        idx = db.session.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'assai_cce' ORDER BY indexname"
        )).fetchall()
        for row in idx:
            print(f'  - {row[0]}')


if __name__ == '__main__':
    main()
