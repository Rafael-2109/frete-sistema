"""
Migration: Adicionar campo cte_pdf_path em carvia_operacoes e carvia_subcontratos.

Armazena o path do PDF original importado (DACTE PDF), complementando o cte_xml_path
que so armazena XMLs. Permite download do documento fonte para conferencia.

Executar: python scripts/migrations/adicionar_cte_pdf_path_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # Verificar se ja existem
        result = conn.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'carvia_operacoes' AND column_name = 'cte_pdf_path'
        """))
        if result.fetchone():
            print("[OK] carvia_operacoes.cte_pdf_path ja existe.")
        else:
            conn.execute(db.text("""
                ALTER TABLE carvia_operacoes
                ADD COLUMN cte_pdf_path VARCHAR(500)
            """))
            conn.commit()
            print("[+] carvia_operacoes.cte_pdf_path adicionado.")

        result = conn.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'carvia_subcontratos' AND column_name = 'cte_pdf_path'
        """))
        if result.fetchone():
            print("[OK] carvia_subcontratos.cte_pdf_path ja existe.")
        else:
            conn.execute(db.text("""
                ALTER TABLE carvia_subcontratos
                ADD COLUMN cte_pdf_path VARCHAR(500)
            """))
            conn.commit()
            print("[+] carvia_subcontratos.cte_pdf_path adicionado.")

        conn.close()
        print("\nMigration concluida.")


if __name__ == '__main__':
    run()
