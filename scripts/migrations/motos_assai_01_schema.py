"""
Migration: Schema completo do módulo Motos Assaí (16 tabelas)
==============================================================
Executar: python scripts/migrations/motos_assai_01_schema.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


TABELAS_ESPERADAS = [
    'assai_cd', 'assai_loja', 'assai_modelo', 'assai_modelo_alias',
    'assai_moto', 'assai_moto_evento',
    'assai_pedido_venda', 'assai_pedido_venda_item',
    'assai_compra_motochefe', 'assai_compra_motochefe_pedido',
    'assai_recibo_motochefe', 'assai_recibo_item',
    'assai_separacao', 'assai_separacao_item',
    'assai_nf_qpa', 'assai_nf_qpa_item',
]


def criar_schema():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        existentes_antes = set(inspector.get_table_names())
        a_criar = [t for t in TABELAS_ESPERADAS if t not in existentes_antes]

        if not a_criar:
            print("Todas as tabelas já existem. Nada a fazer.")
            return

        print(f"Criando {len(a_criar)} tabelas: {a_criar}")

        sql_path = os.path.join(os.path.dirname(__file__), 'motos_assai_01_schema.sql')
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql = f.read()

        db.session.execute(text(sql))
        db.session.commit()

        inspector = inspect(db.engine)
        existentes_depois = set(inspector.get_table_names())
        criadas = [t for t in TABELAS_ESPERADAS if t in existentes_depois and t not in existentes_antes]
        faltando = [t for t in TABELAS_ESPERADAS if t not in existentes_depois]

        print(f"Criadas: {criadas}")
        if faltando:
            print(f"ERRO: tabelas não criadas: {faltando}")
            sys.exit(1)
        print("OK: schema completo.")


if __name__ == '__main__':
    criar_schema()
