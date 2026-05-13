"""Migration 24: ALTER CHECK constraints para aceitar novos status.

ATENCAO: rodar APOS Migration 21 (backfill status pedido) — caso contrario,
pedidos com status legado violarao o novo CHECK.

Spec: §2.2 ("Sem mudança de schema do enum" — assumi VARCHAR sem CHECK,
mas Migration 24 cobre caso CHECK exista).
Plano: Task 6
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_24_check_status_aceitar_novos.sql')


def main():
    app = create_app()
    with app.app_context():
        # Validacao: verificar que nao ha pedidos com status legado antes de aplicar
        legados = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda "
            "WHERE status IN ('EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL')"
        )).scalar()
        if legados > 0:
            print(f'[ABORT] {legados} pedidos com status legado. Rodar Migration 21 antes.')
            sys.exit(1)

        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        db.session.execute(text(sql))
        db.session.commit()

        print('[ok] Migration 24 aplicada (CHECK constraints atualizados)')


if __name__ == '__main__':
    main()
