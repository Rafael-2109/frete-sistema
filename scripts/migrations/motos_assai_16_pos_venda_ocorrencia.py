"""Motos Assai - Migration 16: Pos-Venda (ocorrencias por chassi vendido).

Cria 2 tabelas:
  * assai_pos_venda_ocorrencia        - 1 ocorrencia (texto) por chassi
  * assai_pos_venda_ocorrencia_anexo  - N anexos S3 por ocorrencia

Categorias da ocorrencia: LOJA ou CLIENTE.
Tipos de anexo: FOTO, VIDEO, AUDIO, OUTRO. S3 keys em
`motos_assai/pos_venda/{ocorrencia_id}/`.

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
        ocorr_antes = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_pos_venda_ocorrencia'"
        )).scalar() or 0
        anexo_antes = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_pos_venda_ocorrencia_anexo'"
        )).scalar() or 0
        print(f'BEFORE: ocorrencia existe={bool(ocorr_antes)}, '
              f'anexo existe={bool(anexo_antes)}')

        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_16_pos_venda_ocorrencia.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # AFTER
        ocorr_depois = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_pos_venda_ocorrencia'"
        )).scalar() or 0
        anexo_depois = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_pos_venda_ocorrencia_anexo'"
        )).scalar() or 0

        if not ocorr_depois:
            print('ERRO: assai_pos_venda_ocorrencia nao foi criada')
            sys.exit(1)
        if not anexo_depois:
            print('ERRO: assai_pos_venda_ocorrencia_anexo nao foi criada')
            sys.exit(1)

        indices = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename IN "
            "('assai_pos_venda_ocorrencia','assai_pos_venda_ocorrencia_anexo') "
            "ORDER BY indexname"
        )).fetchall()
        print(f'OK: tabelas criadas. Indices: {[r[0] for r in indices]}')


if __name__ == '__main__':
    run()
