"""
Migration: Aumentar precisao de colunas de quantidade de Numeric(15,3) para Numeric(15,6).

Motivacao:
    - Odoo usa 5 casas decimais para product_qty (digits='Product Unit of Measure')
    - DFe/NF-e XML usa ate 4 casas decimais (qCom)
    - Numeric(15,3) trunca a 4a+ casa decimal ao salvar localmente
    - Ao escrever de volta ao Odoo, o valor truncado causa divergencia

Colunas afetadas:
    - match_nf_po_item.qtd_nf
    - match_nf_po_item.qtd_po
    - match_nf_po_alocacao.qtd_alocada
    - recebimento_lf_lote.quantidade
    - recebimento_lote.quantidade
    - pedido_compras.qtd_produto_pedido
    - pedido_compras.qtd_recebida
    - historico_pedido_compras.qtd_produto_pedido
    - historico_pedido_compras.qtd_recebida

Operacao NAO-DESTRUTIVA: aumentar precisao apenas adiciona zeros nas casas adicionais.

Uso:
    source .venv/bin/activate
    python scripts/migration_aumentar_precisao_quantidades.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Aumenta precisao de Numeric(15,3) para Numeric(15,6) nas colunas de quantidade."""
    app = create_app()

    alteracoes = [
        ("match_nf_po_item", "qtd_nf", "NUMERIC(18, 6)"),
        ("match_nf_po_item", "qtd_po", "NUMERIC(18, 6)"),
        ("match_nf_po_alocacao", "qtd_alocada", "NUMERIC(18, 6)"),
        ("recebimento_lf_lote", "quantidade", "NUMERIC(18, 6)"),
        ("recebimento_lote", "quantidade", "NUMERIC(18, 6)"),
        ("pedido_compras", "qtd_produto_pedido", "NUMERIC(18, 6)"),
        ("pedido_compras", "qtd_recebida", "NUMERIC(18, 6)"),
        ("historico_pedido_compras", "qtd_produto_pedido", "NUMERIC(18, 6)"),
        ("historico_pedido_compras", "qtd_recebida", "NUMERIC(18, 6)"),
    ]

    with app.app_context():
        print("=" * 60)
        print("Migration: Aumentar precisao de quantidades para Numeric(15,6)")
        print("=" * 60)

        for tabela, coluna, tipo in alteracoes:
            sql = f"ALTER TABLE {tabela} ALTER COLUMN {coluna} TYPE {tipo};"
            print(f"\n  Executando: {sql}")
            try:
                db.session.execute(text(sql))
                print(f"  OK: {tabela}.{coluna} -> {tipo}")
            except Exception as e:
                print(f"  ERRO: {tabela}.{coluna} -> {e}")
                db.session.rollback()
                raise

        db.session.commit()
        print("\n" + "=" * 60)
        print("Migration concluida com sucesso!")
        print("=" * 60)


if __name__ == '__main__':
    executar_migration()
