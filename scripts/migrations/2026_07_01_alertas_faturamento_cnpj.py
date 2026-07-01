"""Migration: Alertas de Faturamento por CNPJ (e-mail).

Cria 2 tabelas: alerta_faturamento_cnpj (cadastro CNPJ+emails) e
alerta_faturamento_enviado (log/idempotencia). Idempotente
(CREATE TABLE/INDEX IF NOT EXISTS).

Carga inicial dos CNPJs do Atacadao RJ: rodar em seguida
`2026_07_01_seed_alertas_faturamento_atacadao_rj.py`.

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
        db.session.commit()
        print("OK: 2 tabelas de alertas de faturamento criadas/verificadas.")


if __name__ == '__main__':
    main()
