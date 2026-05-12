"""Motos Assai - Migration 12: saldo_modelo (placeholder qtd planejada) + ajuste UNIQUE.

1. Cria `assai_separacao_saldo_modelo` (qtd planejada por modelo na separacao).
2. Ajusta UNIQUE de `assai_separacao`: bloqueia apenas EM_SEPARACAO (permite N FECHADAS por
   pedido x loja — fluxo de carregamentos sucessivos).

Idempotente; safe para re-execucao.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        # BEFORE
        tabela_antes = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_separacao_saldo_modelo'"
        )).scalar() or 0
        unique_antes = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'assai_separacao' AND indexname IN "
            "  ('ux_assai_separacao_pedido_loja_ativa', "
            "   'ux_assai_separacao_pedido_loja_em_separacao')"
        )).fetchall()
        print(f'BEFORE: tabela saldo_modelo existe={bool(tabela_antes)}, '
              f'UNIQUEs existentes={[r[0] for r in unique_antes]}')

        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_12_separacao_saldo_modelo.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # AFTER
        tabela_depois = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_separacao_saldo_modelo'"
        )).scalar() or 0
        unique_depois = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'assai_separacao' AND indexname IN "
            "  ('ux_assai_separacao_pedido_loja_ativa', "
            "   'ux_assai_separacao_pedido_loja_em_separacao')"
        )).fetchall()
        nomes = [r[0] for r in unique_depois]

        if not tabela_depois:
            print('ERRO: tabela assai_separacao_saldo_modelo nao foi criada')
            sys.exit(1)
        if 'ux_assai_separacao_pedido_loja_ativa' in nomes:
            print('ERRO: UNIQUE antigo ainda existe (deveria ter sido dropado)')
            sys.exit(1)
        if 'ux_assai_separacao_pedido_loja_em_separacao' not in nomes:
            print('ERRO: UNIQUE novo nao foi criado')
            sys.exit(1)

        print(f'OK: tabela saldo_modelo criada; UNIQUE atual={nomes}')


if __name__ == '__main__':
    run()
