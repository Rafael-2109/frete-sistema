"""
Migration: Adicionar status_pagamento em carvia_faturas_transportadora
======================================================================

Adiciona 3 colunas para controle de pagamento (independente de status_conferencia):
  - status_pagamento VARCHAR(20) NOT NULL DEFAULT 'PENDENTE'
  - pago_por VARCHAR(100)
  - pago_em TIMESTAMP

Execucao:
    source .venv/bin/activate
    python scripts/migrations/adicionar_status_pagamento_fatura_transportadora.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se coluna ja existe na tabela."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def verificar_indice_existe(conn, nome_indice):
    """Verifica se indice ja existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = :nome
        )
    """), {'nome': nome_indice})
    return result.scalar()


def verificar_antes(conn):
    """Estado antes da migration."""
    print("\n=== VERIFICACAO PRE-MIGRATION ===")

    tem_status = verificar_coluna_existe(conn, 'carvia_faturas_transportadora', 'status_pagamento')
    tem_pago_por = verificar_coluna_existe(conn, 'carvia_faturas_transportadora', 'pago_por')
    tem_pago_em = verificar_coluna_existe(conn, 'carvia_faturas_transportadora', 'pago_em')
    tem_indice = verificar_indice_existe(conn, 'ix_carvia_fat_transp_status_pgto')

    print(f"  status_pagamento existe: {tem_status}")
    print(f"  pago_por existe:         {tem_pago_por}")
    print(f"  pago_em existe:          {tem_pago_em}")
    print(f"  indice existe:           {tem_indice}")

    return {
        'status_pagamento': tem_status,
        'pago_por': tem_pago_por,
        'pago_em': tem_pago_em,
        'indice': tem_indice,
    }


def executar_migration(conn, estado):
    """Executa as alteracoes."""
    print("\n=== EXECUTANDO MIGRATION ===")

    if not estado['status_pagamento']:
        print("  Adicionando coluna status_pagamento...")
        conn.execute(text("""
            ALTER TABLE carvia_faturas_transportadora
            ADD COLUMN status_pagamento VARCHAR(20) NOT NULL DEFAULT 'PENDENTE'
        """))
        print("  -> OK")
    else:
        print("  status_pagamento ja existe, pulando.")

    if not estado['pago_por']:
        print("  Adicionando coluna pago_por...")
        conn.execute(text("""
            ALTER TABLE carvia_faturas_transportadora
            ADD COLUMN pago_por VARCHAR(100)
        """))
        print("  -> OK")
    else:
        print("  pago_por ja existe, pulando.")

    if not estado['pago_em']:
        print("  Adicionando coluna pago_em...")
        conn.execute(text("""
            ALTER TABLE carvia_faturas_transportadora
            ADD COLUMN pago_em TIMESTAMP
        """))
        print("  -> OK")
    else:
        print("  pago_em ja existe, pulando.")

    if not estado['indice']:
        print("  Criando indice ix_carvia_fat_transp_status_pgto...")
        conn.execute(text("""
            CREATE INDEX ix_carvia_fat_transp_status_pgto
            ON carvia_faturas_transportadora (status_pagamento)
        """))
        print("  -> OK")
    else:
        print("  indice ja existe, pulando.")


def verificar_depois(conn):
    """Estado apos a migration."""
    print("\n=== VERIFICACAO POS-MIGRATION ===")

    tem_status = verificar_coluna_existe(conn, 'carvia_faturas_transportadora', 'status_pagamento')
    tem_pago_por = verificar_coluna_existe(conn, 'carvia_faturas_transportadora', 'pago_por')
    tem_pago_em = verificar_coluna_existe(conn, 'carvia_faturas_transportadora', 'pago_em')
    tem_indice = verificar_indice_existe(conn, 'ix_carvia_fat_transp_status_pgto')

    print(f"  status_pagamento existe: {tem_status}")
    print(f"  pago_por existe:         {tem_pago_por}")
    print(f"  pago_em existe:          {tem_pago_em}")
    print(f"  indice existe:           {tem_indice}")

    tudo_ok = all([tem_status, tem_pago_por, tem_pago_em, tem_indice])
    print(f"\n  {'MIGRATION COMPLETA' if tudo_ok else 'FALHA — verificar erros acima'}")
    return tudo_ok


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            estado = verificar_antes(conn)

            ja_completa = all(estado.values())
            if ja_completa:
                print("\n  Todas as colunas e indice ja existem. Nada a fazer.")
                return

            executar_migration(conn, estado)
            verificar_depois(conn)

    print("\nMigration finalizada.")


if __name__ == '__main__':
    main()
