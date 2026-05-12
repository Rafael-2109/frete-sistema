"""Motos Assai - Migration 15: HOTFIX para Migration 10 que falhou em prod (2026-05-12).

INCIDENTE: Sentry PYTHON-FLASK-RT em 2026-05-12 08:20 UTC mostrou
NotNullViolation em agendamento_confirmado durante backfill da Migration 10.
Causa: db.create_all() criou a tabela ANTES da migration; SQLAlchemy default=False
nao vira DEFAULT no DB.

CONSEQUENCIA: Migration 10 abortou, pedido_loja_id nao foi adicionado em
assai_pedido_venda_item, todas rotas motos_assai quebraram (PYTHON-FLASK-RV/RW).

FIX: garantir DEFAULT FALSE no DB + UPDATE de NULL para FALSE + re-rodar backfill
todo. Idempotente.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        # BEFORE: diagnostico
        nulls_loja = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda_loja "
            "WHERE agendamento_confirmado IS NULL"
        )).scalar() or 0
        nulls_sep = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_separacao "
            "WHERE agendamento_confirmado IS NULL"
        )).scalar() or 0
        items_sem_fk = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda_item "
            "WHERE pedido_loja_id IS NULL"
        )).scalar() or 0
        col_pedido_loja_id = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='assai_pedido_venda_item' AND column_name='pedido_loja_id'"
        )).scalar() or 0
        print(f'BEFORE: pvl_nulls={nulls_loja}, sep_nulls={nulls_sep}, '
              f'items_sem_fk={items_sem_fk}, col_pedido_loja_id_existe={bool(col_pedido_loja_id)}')

        # Executar SQL
        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_15_fix_default_agendamento_confirmado.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # AFTER: validar
        nulls_loja = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda_loja "
            "WHERE agendamento_confirmado IS NULL"
        )).scalar() or 0
        nulls_sep = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_separacao "
            "WHERE agendamento_confirmado IS NULL"
        )).scalar() or 0
        items_sem_fk = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda_item "
            "WHERE pedido_loja_id IS NULL"
        )).scalar() or 0
        col_default_pvl = db.session.execute(text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name='assai_pedido_venda_loja' "
            "  AND column_name='agendamento_confirmado'"
        )).scalar()
        col_default_sep = db.session.execute(text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name='assai_separacao' "
            "  AND column_name='agendamento_confirmado'"
        )).scalar()
        col_not_null = db.session.execute(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='assai_pedido_venda_item' AND column_name='pedido_loja_id'"
        )).scalar()

        print(f'AFTER: pvl_nulls={nulls_loja}, sep_nulls={nulls_sep}, '
              f'items_sem_fk={items_sem_fk}')
        print(f'AFTER: pvl_default={col_default_pvl!r}, sep_default={col_default_sep!r}, '
              f'pedido_loja_id_nullable={col_not_null!r}')

        if nulls_loja > 0 or nulls_sep > 0 or items_sem_fk > 0:
            print('ERRO: estado inconsistente apos migration 15')
            sys.exit(1)
        if col_not_null != 'NO':
            print('ERRO: pedido_loja_id ainda permite NULL')
            sys.exit(1)
        if not col_default_pvl or 'false' not in col_default_pvl.lower():
            print(f'AVISO: pvl.agendamento_confirmado default={col_default_pvl!r} (esperado false)')

        print('OK: migration 15 (HOTFIX prod) aplicada com sucesso')


if __name__ == '__main__':
    run()
