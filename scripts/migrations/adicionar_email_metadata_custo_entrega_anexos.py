"""
Migration: Adicionar campos de metadados de email em carvia_custo_entrega_anexos
================================================================================

Novos campos (todos nullable — populados apenas para arquivos .msg/.eml):
- email_remetente VARCHAR(255)
- email_assunto VARCHAR(500)
- email_data_envio TIMESTAMP
- email_conteudo_preview VARCHAR(500)

Permite armazenar metadados extraidos de emails anexados a custos de entrega,
similar ao modelo EmailAnexado usado por DespesaExtra.
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

        tabela = 'carvia_custo_entrega_anexos'
        campos = {
            'email_remetente': 'VARCHAR(255)',
            'email_assunto': 'VARCHAR(500)',
            'email_data_envio': 'TIMESTAMP',
            'email_conteudo_preview': 'VARCHAR(500)',
        }

        print(f"\n=== Migration: Email metadata em {tabela} ===\n")

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

        db.session.commit()

        # After: verificar resultado (nova conexao apos commit)
        conn2 = db.session.connection()
        print("\n--- AFTER ---")
        for campo in campos:
            existe = verificar_campo_existe(conn2, tabela, campo)
            status = 'OK' if existe else 'FALHA'
            print(f"  {campo}: {status}")

        print("\n=== Migration concluida com sucesso ===\n")


if __name__ == '__main__':
    main()
