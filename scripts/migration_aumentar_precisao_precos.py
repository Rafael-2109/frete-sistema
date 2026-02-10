"""
Migration: Aumentar precisao de colunas de preco de Numeric(15,4) para Numeric(18,8).

Motivacao:
    - NF-e XML (vUnCom) suporta ate 10 casas decimais de preco unitario
    - Odoo usa float (Python ~15 digitos significativos) para price_unit
    - Numeric(15,4) trunca a 5a+ casa decimal ao salvar localmente
    - Ao escrever de volta ao Odoo, o valor truncado causa divergencia de preco
    - Numeric(18,8) cobre 8 casas decimais (suficiente para NF-e e Odoo)

Colunas afetadas:
    - match_nf_po_item.preco_nf
    - match_nf_po_item.preco_po
    - match_nf_po_alocacao.preco_po
    - pedido_compras.preco_produto_pedido
    - historico_pedido_compras.preco_produto_pedido

Operacao NAO-DESTRUTIVA: aumentar precisao apenas adiciona zeros nas casas adicionais.
Digitos inteiros: 18-8=10 (vs 15-4=11 original) — OK para precos.

Uso:
    source .venv/bin/activate
    python scripts/migration_aumentar_precisao_precos.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Aumenta precisao de Numeric(15,4) para Numeric(18,8) nas colunas de preco."""
    app = create_app()

    alteracoes = [
        ("match_nf_po_item", "preco_nf", "NUMERIC(18, 8)"),
        ("match_nf_po_item", "preco_po", "NUMERIC(18, 8)"),
        ("match_nf_po_alocacao", "preco_po", "NUMERIC(18, 8)"),
        ("pedido_compras", "preco_produto_pedido", "NUMERIC(18, 8)"),
        ("historico_pedido_compras", "preco_produto_pedido", "NUMERIC(18, 8)"),
    ]

    with app.app_context():
        print("=" * 60)
        print("Migration: Aumentar precisao de precos para Numeric(18,8)")
        print("=" * 60)

        # Verificar estado atual antes de alterar
        print("\nVerificando estado atual das colunas...")
        for tabela, coluna, _ in alteracoes:
            result = db.session.execute(text(
                "SELECT data_type, numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name = :tabela AND column_name = :coluna"
            ), {"tabela": tabela, "coluna": coluna}).fetchone()
            if result:
                print(f"  {tabela}.{coluna}: {result[0]}({result[1]},{result[2]})")
            else:
                print(f"  {tabela}.{coluna}: COLUNA NAO ENCONTRADA!")

        print("\nExecutando alteracoes...")
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

        # Verificar estado apos alteracao
        print("\nVerificando estado apos alteracao...")
        for tabela, coluna, _ in alteracoes:
            result = db.session.execute(text(
                "SELECT numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name = :tabela AND column_name = :coluna"
            ), {"tabela": tabela, "coluna": coluna}).fetchone()
            if result:
                status = "OK" if result[0] == 18 and result[1] == 8 else "DIVERGENTE!"
                print(f"  {tabela}.{coluna}: ({result[0]},{result[1]}) [{status}]")

        print("\n" + "=" * 60)
        print("Migration concluida com sucesso!")
        print("=" * 60)


if __name__ == '__main__':
    executar_migration()
