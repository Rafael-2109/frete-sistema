"""Motos Assai - Migration 10: cabecalho pedido x loja com 4 campos de agendamento.

Cria `assai_pedido_venda_loja` com expedicao/agendamento/protocolo/agendamento_confirmado.
Backfill a partir de itens existentes e adiciona FK em `assai_pedido_venda_item`.

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
        # Verificacao BEFORE
        before_lojas = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_pedido_venda_loja'"
        )).scalar() or 0
        before_fk = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'assai_pedido_venda_item' "
            "  AND column_name = 'pedido_loja_id'"
        )).scalar() or 0
        print(f'BEFORE: tabela assai_pedido_venda_loja existe={bool(before_lojas)}, '
              f'pedido_loja_id em items existe={bool(before_fk)}')

        # H6: diagnostico pre-migration — detectar items orfaos antes de criar a FK.
        # Item com loja_id apontando para loja inexistente (FK violada por dado
        # legado) faria SET NOT NULL falhar silenciosamente. Detectar e abortar
        # com mensagem clara.
        orfaos = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda_item it "
            "WHERE NOT EXISTS ("
            "    SELECT 1 FROM assai_loja l WHERE l.id = it.loja_id"
            ")"
        )).scalar() or 0
        if orfaos > 0:
            sample = db.session.execute(text(
                "SELECT id, pedido_id, loja_id FROM assai_pedido_venda_item it "
                "WHERE NOT EXISTS ("
                "    SELECT 1 FROM assai_loja l WHERE l.id = it.loja_id"
                ") LIMIT 5"
            )).fetchall()
            print(f'ERRO: {orfaos} item(s) em assai_pedido_venda_item com loja_id orfa '
                  f'(loja deletada/nao existe). Backfill nao pode criar cabecalho.')
            print(f'  Amostra: {[(r[0], r[1], r[2]) for r in sample]}')
            print('  Acao: deletar items orfaos ou recriar lojas referenciadas antes de rodar a migration.')
            sys.exit(1)

        # Executar SQL
        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_10_pedido_venda_loja.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # Verificacao AFTER
        tabela_existe = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_pedido_venda_loja'"
        )).scalar() or 0
        cabecalhos = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda_loja"
        )).scalar() or 0
        items_sem_fk = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda_item WHERE pedido_loja_id IS NULL"
        )).scalar() or 0
        cols_4_campos = db.session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'assai_pedido_venda_loja' "
            "  AND column_name IN ('expedicao','agendamento','protocolo','agendamento_confirmado') "
            "ORDER BY column_name"
        )).fetchall()

        cols = [r[0] for r in cols_4_campos]
        expected = ['agendamento', 'agendamento_confirmado', 'expedicao', 'protocolo']

        print(f'AFTER: tabela existe={bool(tabela_existe)}, '
              f'cabecalhos criados={cabecalhos}, '
              f'items sem FK={items_sem_fk}')

        if not tabela_existe:
            print('ERRO: tabela assai_pedido_venda_loja nao foi criada')
            sys.exit(1)
        if cols != expected:
            print(f'ERRO: colunas esperadas {expected}, encontradas {cols}')
            sys.exit(1)
        if items_sem_fk > 0:
            print(f'ERRO: {items_sem_fk} items sem pedido_loja_id apos backfill')
            sys.exit(1)

        print('OK: migration 10 aplicada com sucesso')


if __name__ == '__main__':
    run()
