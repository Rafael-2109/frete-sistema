"""
Migration: Aumentar precisao de colunas de quantidade no recebimento fisico
de Numeric(15,3) para Numeric(18,6).

Motivacao:
    - Odoo usa 5 casas decimais para product_qty (digits='Product Unit of Measure')
    - DFe/NF-e XML usa ate 4 casas decimais (qCom)
    - Numeric(15,3) trunca a 4a+ casa decimal ao salvar localmente
    - Ao comparar com Odoo, o valor truncado causa divergencia

Colunas afetadas:
    - picking_recebimento_produto.product_uom_qty
    - picking_recebimento_move_line.quantity
    - picking_recebimento_move_line.reserved_uom_qty

Operacao NAO-DESTRUTIVA: aumentar precisao apenas adiciona zeros nas casas adicionais.

Uso:
    source .venv/bin/activate
    python scripts/migration_aumentar_precisao_quantidades_recebimento.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Aumenta precisao de Numeric(15,3) para Numeric(18,6) nas colunas de quantidade do recebimento fisico."""
    app = create_app()

    alteracoes = [
        ("picking_recebimento_produto", "product_uom_qty", "NUMERIC(18, 6)"),
        ("picking_recebimento_move_line", "quantity", "NUMERIC(18, 6)"),
        ("picking_recebimento_move_line", "reserved_uom_qty", "NUMERIC(18, 6)"),
    ]

    with app.app_context():
        print("=" * 60)
        print("Migration: Aumentar precisao de quantidades do recebimento fisico")
        print("  Numeric(15,3) -> Numeric(18,6)")
        print("=" * 60)

        # Verificar estado atual
        print("\n--- Estado ANTES ---")
        for tabela, coluna, _ in alteracoes:
            result = db.session.execute(text(
                "SELECT numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name = :tabela AND column_name = :coluna"
            ), {"tabela": tabela, "coluna": coluna})
            row = result.fetchone()
            if row:
                print(f"  {tabela}.{coluna}: Numeric({row[0]},{row[1]})")
            else:
                print(f"  {tabela}.{coluna}: COLUNA NAO ENCONTRADA!")

        # Executar ALTERs
        print("\n--- Executando ALTERs ---")
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

        # Verificar estado final
        print("\n--- Estado APOS ---")
        for tabela, coluna, _ in alteracoes:
            result = db.session.execute(text(
                "SELECT numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name = :tabela AND column_name = :coluna"
            ), {"tabela": tabela, "coluna": coluna})
            row = result.fetchone()
            if row:
                print(f"  {tabela}.{coluna}: Numeric({row[0]},{row[1]})")

        # Verificar se restam colunas Numeric(15,3) nas tabelas picking_recebimento_*
        print("\n--- Verificacao: Colunas Numeric(15,3) restantes em picking_recebimento_* ---")
        result = db.session.execute(text(
            "SELECT table_name, column_name, numeric_precision, numeric_scale "
            "FROM information_schema.columns "
            "WHERE table_name LIKE 'picking_recebimento%%' "
            "  AND numeric_precision = 15 AND numeric_scale = 3 "
            "ORDER BY table_name, column_name"
        ))
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  ALERTA: {row[0]}.{row[1]}: Numeric({row[2]},{row[3]})")
        else:
            print("  Nenhuma coluna Numeric(15,3) restante. OK!")

        print("\n" + "=" * 60)
        print("Migration concluida com sucesso!")
        print("=" * 60)


if __name__ == '__main__':
    executar_migration()
