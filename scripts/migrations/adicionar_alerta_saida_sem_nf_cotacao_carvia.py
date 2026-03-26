"""
Migration: Adicionar campos de alerta saida sem NF em carvia_cotacoes
=====================================================================

Novos campos:
- alerta_saida_sem_nf BOOLEAN NOT NULL DEFAULT FALSE
- alerta_saida_sem_nf_em TIMESTAMP NULLABLE
- alerta_saida_embarque_id INTEGER NULLABLE

Permite persistir alerta quando embarque sai pela portaria com itens CarVia
que ainda nao possuem NF. Alerta e limpo ao anexar NF ao pedido.
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

        tabela = 'carvia_cotacoes'
        campos = {
            'alerta_saida_sem_nf': "BOOLEAN NOT NULL DEFAULT FALSE",
            'alerta_saida_sem_nf_em': 'TIMESTAMP',
            'alerta_saida_embarque_id': 'INTEGER',
        }

        print(f"\n=== Migration: Alerta saida sem NF em {tabela} ===\n")

        # Before: verificar estado atual
        print("--- BEFORE ---")
        for campo in campos:
            existe = verificar_campo_existe(conn, tabela, campo)
            print(f"  {campo}: {'JA EXISTE' if existe else 'NAO EXISTE'}")

        # Aplicar alteracoes
        print("\n--- APLICANDO ---")
        for campo, tipo in campos.items():
            if not verificar_campo_existe(conn, tabela, campo):
                sql = f"ALTER TABLE {tabela} ADD COLUMN {campo} {tipo}"
                conn.execute(text(sql))
                print(f"  + {campo} ({tipo})")
            else:
                print(f"  ~ {campo} ja existe (skip)")

        # Criar indice parcial para cotacoes com alerta ativo
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_cotacoes_alerta_saida
            ON carvia_cotacoes (id) WHERE alerta_saida_sem_nf = TRUE
        """))
        print("  + indice ix_carvia_cotacoes_alerta_saida (parcial)")

        db.session.commit()

        # After: verificar resultado (nova conexao apos commit)
        conn2 = db.session.connection()
        print("\n--- AFTER ---")
        for campo in campos:
            existe = verificar_campo_existe(conn2, tabela, campo)
            status = 'OK' if existe else 'FALHA'
            print(f"  {campo}: {status}")

        # Contar alertas existentes (esperado: 0)
        result = conn2.execute(text(
            "SELECT COUNT(*) FROM carvia_cotacoes WHERE alerta_saida_sem_nf = TRUE"
        ))
        count = result.scalar()
        print(f"\n  Cotacoes com alerta ativo: {count}")

        print("\n=== Migration concluida com sucesso ===\n")


if __name__ == '__main__':
    main()
