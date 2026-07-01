"""Migration: Alertas de Faturamento por CNPJ (e-mail + Teams).

Cria 3 tabelas: alerta_faturamento_cnpj, alerta_faturamento_config,
alerta_faturamento_enviado. Idempotente (CREATE TABLE/INDEX IF NOT EXISTS).
Semeia 1 linha de config (get-or-create).

Spec: docs/superpowers/specs/2026-07-01-alertas-faturamento-cnpj-design.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

SQL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '2026_07_01_alertas_faturamento_cnpj.sql',
)


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            db.session.execute(text(f.read()))
        # Semear config única
        existe = db.session.execute(
            text("SELECT COUNT(*) FROM alerta_faturamento_config")
        ).scalar()
        if not existe:
            db.session.execute(text(
                "INSERT INTO alerta_faturamento_config "
                "(teams_ativo, email_ativo) VALUES (FALSE, TRUE)"
            ))
        db.session.commit()
        print("OK: 3 tabelas de alertas de faturamento criadas/verificadas.")


if __name__ == '__main__':
    main()
