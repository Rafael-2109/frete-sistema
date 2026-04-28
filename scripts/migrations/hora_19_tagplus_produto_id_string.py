"""Migration HORA 19: troca hora_tagplus_produto_map.tagplus_produto_id de
INTEGER para VARCHAR(50).

A API TagPlus aceita string no campo `produto` do POST /nfes (codigo do
produto, nao apenas o ID inteiro). Confirmado pelo operador em 2026-04-27.

Seguro porque a tabela esta vazia (0/19 modelos mapeados ate aqui). Caso
existam registros, eles sao convertidos via `USING tagplus_produto_id::text`.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(__file__), 'hora_19_tagplus_produto_id_string.sql')


def verificar(label: str):
    print(f'[{label}]')
    row = db.session.execute(db.text("""
        SELECT data_type, character_maximum_length
          FROM information_schema.columns
         WHERE table_name = 'hora_tagplus_produto_map'
           AND column_name = 'tagplus_produto_id'
    """)).first()
    if row:
        print(f'  tagplus_produto_id: type={row[0]} length={row[1]}')
    else:
        print('  tagplus_produto_id: NAO ENCONTRADO')

    qtd = db.session.execute(db.text(
        'SELECT COUNT(*) FROM hora_tagplus_produto_map'
    )).scalar()
    print(f'  registros existentes: {qtd}')


def executar_ddl():
    with open(SQL_PATH, encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))


def main():
    app = create_app()
    with app.app_context():
        verificar('BEFORE')
        executar_ddl()
        db.session.commit()
        verificar('AFTER')
        print('\nOK — migration concluida.')


if __name__ == '__main__':
    main()
