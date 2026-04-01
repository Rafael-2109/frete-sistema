"""
Migration: Adicionar campos de condicao de pagamento e responsavel do frete
===========================================================================

Novos campos (em 3 tabelas: carvia_cotacoes, carvia_operacoes, carvia_fretes):
- condicao_pagamento VARCHAR(20) NULLABLE  (A_VISTA | PRAZO)
- prazo_dias INTEGER NULLABLE              (1-30 se PRAZO)
- responsavel_frete VARCHAR(30) NULLABLE   (100_REMETENTE | 100_DESTINATARIO | 50_50 | PERSONALIZADO)
- percentual_remetente NUMERIC(5,2) NULLABLE
- percentual_destinatario NUMERIC(5,2) NULLABLE

Controle financeiro: registrar quem paga o frete e condicao de pagamento.
Fatura continua com valor total e 1 tomador (sem split).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_campo_existe(conn, tabela, campo):
    """Verifica se um campo existe na tabela."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :campo
        )
    """), {'tabela': tabela, 'campo': campo})
    return result.scalar()


def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        tabelas = ['carvia_cotacoes', 'carvia_operacoes', 'carvia_fretes']
        campos = {
            'condicao_pagamento': 'VARCHAR(20)',
            'prazo_dias': 'INTEGER',
            'responsavel_frete': 'VARCHAR(30)',
            'percentual_remetente': 'NUMERIC(5,2)',
            'percentual_destinatario': 'NUMERIC(5,2)',
        }

        print("\n=== Migration: Condicao Pagamento + Responsavel Frete ===\n")

        for tabela in tabelas:
            print(f"--- {tabela} ---")

            # Before
            print("  BEFORE:")
            for campo in campos:
                existe = verificar_campo_existe(conn, tabela, campo)
                print(f"    {campo}: {'JA EXISTE' if existe else 'NAO EXISTE'}")

            # Aplicar
            print("  APLICANDO:")
            for campo, tipo in campos.items():
                if not verificar_campo_existe(conn, tabela, campo):
                    sql = f"ALTER TABLE {tabela} ADD COLUMN {campo} {tipo}"
                    conn.execute(text(sql))
                    print(f"    + {campo} ({tipo})")
                else:
                    print(f"    ~ {campo} ja existe (skip)")

            # After
            print("  AFTER:")
            for campo in campos:
                existe = verificar_campo_existe(conn, tabela, campo)
                status = 'OK' if existe else 'FALHA'
                print(f"    {campo}: {status}")
            print()

        db.session.commit()
        print("=== Migration concluida com sucesso ===\n")


if __name__ == '__main__':
    main()
