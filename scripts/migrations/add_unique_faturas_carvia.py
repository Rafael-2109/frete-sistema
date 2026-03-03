"""
Migration: Adicionar unique constraints em faturas CarVia
=========================================================

Previne duplicatas na importacao de faturas PDF:
- carvia_faturas_cliente: UNIQUE(numero_fatura, cnpj_cliente)
- carvia_faturas_transportadora: UNIQUE(numero_fatura, transportadora_id)

IMPORTANTE: Executar fix_carvia_faturas_duplicadas.py ANTES desta migration,
pois o unique index falhara se duplicatas ainda existirem.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/add_unique_faturas_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        print("=" * 70)
        print("Migration: ADD UNIQUE CONSTRAINTS em faturas CarVia")
        print("=" * 70)

        # --- 1. carvia_faturas_cliente ---
        print("\n--- carvia_faturas_cliente ---")

        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'carvia_faturas_cliente'
              AND indexname = 'uq_fatura_cliente_num_cnpj'
        """))
        existe_cliente = result.fetchone()

        if existe_cliente:
            print("[OK] Index uq_fatura_cliente_num_cnpj ja existe. Nada a fazer.")
        else:
            # Verificar se ha duplicatas que impediriam o index
            dupes = conn.execute(text("""
                SELECT numero_fatura, cnpj_cliente, count(*) as qtd
                FROM carvia_faturas_cliente
                GROUP BY numero_fatura, cnpj_cliente
                HAVING count(*) > 1
            """)).fetchall()

            if dupes:
                print(f"[ERRO] {len(dupes)} grupo(s) de duplicatas encontrado(s)!")
                print("       Execute fix_carvia_faturas_duplicadas.py primeiro.")
                for d in dupes:
                    print(f"       numero={d.numero_fatura} cnpj={d.cnpj_cliente} qtd={d.qtd}")
                return

            print("Criando unique index uq_fatura_cliente_num_cnpj...")
            conn.execute(text("""
                CREATE UNIQUE INDEX uq_fatura_cliente_num_cnpj
                    ON carvia_faturas_cliente (numero_fatura, cnpj_cliente)
            """))
            print("[SUCESSO] Index uq_fatura_cliente_num_cnpj criado.")

        # --- 2. carvia_faturas_transportadora ---
        print("\n--- carvia_faturas_transportadora ---")

        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'carvia_faturas_transportadora'
              AND indexname = 'uq_fatura_transp_num_transp'
        """))
        existe_transp = result.fetchone()

        if existe_transp:
            print("[OK] Index uq_fatura_transp_num_transp ja existe. Nada a fazer.")
        else:
            # Verificar duplicatas
            dupes = conn.execute(text("""
                SELECT numero_fatura, transportadora_id, count(*) as qtd
                FROM carvia_faturas_transportadora
                GROUP BY numero_fatura, transportadora_id
                HAVING count(*) > 1
            """)).fetchall()

            if dupes:
                print(f"[ERRO] {len(dupes)} grupo(s) de duplicatas encontrado(s)!")
                for d in dupes:
                    print(f"       numero={d.numero_fatura} transp_id={d.transportadora_id} qtd={d.qtd}")
                return

            print("Criando unique index uq_fatura_transp_num_transp...")
            conn.execute(text("""
                CREATE UNIQUE INDEX uq_fatura_transp_num_transp
                    ON carvia_faturas_transportadora (numero_fatura, transportadora_id)
            """))
            print("[SUCESSO] Index uq_fatura_transp_num_transp criado.")

        db.session.commit()

        # --- Verificacao final ---
        print("\n--- Verificacao final ---")
        indices = conn.execute(text("""
            SELECT indexname, tablename FROM pg_indexes
            WHERE indexname IN ('uq_fatura_cliente_num_cnpj', 'uq_fatura_transp_num_transp')
            ORDER BY indexname
        """)).fetchall()

        for idx in indices:
            print(f"  [OK] {idx.indexname} em {idx.tablename}")

        if len(indices) == 2:
            print("\n[SUCESSO] Ambos unique indexes criados.")
        else:
            print(f"\n[AVISO] Apenas {len(indices)}/2 indexes encontrados.")


if __name__ == '__main__':
    run_migration()
