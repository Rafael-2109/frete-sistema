"""
Migration: Adicionar campo situacao_dfe_odoo em ValidacaoNfPoDfe
================================================================

OBJETIVO: Adicionar campo para armazenar a situacao da NF na SEFAZ
          (l10n_br_situacao_dfe do Odoo: AUTORIZADA, CANCELADA, INUTILIZADA)

CAMPO ADICIONADO:
    - situacao_dfe_odoo: Situacao da NF na SEFAZ (pode ser vazio)

REGRAS:
    - Vazio ou AUTORIZADA = permite lancamento
    - CANCELADA ou INUTILIZADA = bloqueia lancamento

AUTOR: Sistema de Fretes
DATA: 26/01/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def adicionar_campo_situacao_dfe():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("Migration: Adicionar campo situacao_dfe_odoo em validacao_nf_po_dfe")
            print("=" * 80)

            # 1. Verificar se campo ja existe
            print("\n1. Verificando campo existente...")

            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'validacao_nf_po_dfe'
                AND column_name = 'situacao_dfe_odoo'
            """))

            campos_existentes = [row[0] for row in resultado]

            if campos_existentes:
                print("   Campo ja existe! Migration ja foi aplicada.")
                return

            print("   Campo nao existe. Adicionando...")

            # 2. Adicionar campo
            print("\n2. Adicionando campo situacao_dfe_odoo...")

            db.session.execute(text("""
                ALTER TABLE validacao_nf_po_dfe
                ADD COLUMN IF NOT EXISTS situacao_dfe_odoo VARCHAR(20)
            """))

            db.session.commit()
            print("   Campo adicionado com sucesso!")

            # 3. Criar indice
            print("\n3. Criando indice...")

            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_validacao_nf_po_dfe_situacao
                    ON validacao_nf_po_dfe (situacao_dfe_odoo)
                    WHERE situacao_dfe_odoo IS NOT NULL
                """))
                db.session.commit()
                print("   Indice criado com sucesso!")
            except Exception as e:
                print(f"   Aviso: Indice pode ja existir: {e}")

            # 4. Verificar resultado final
            print("\n4. Verificando estrutura final...")

            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'validacao_nf_po_dfe'
                AND column_name = 'situacao_dfe_odoo'
            """))

            for row in resultado:
                nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                print(f"   {row[0]:<25} {row[1]:<15} {nullable}")

            print("\n" + "=" * 80)
            print("MIGRATION CONCLUIDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO: {e}")
            raise


if __name__ == '__main__':
    adicionar_campo_situacao_dfe()
