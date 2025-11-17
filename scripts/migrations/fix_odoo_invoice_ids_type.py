"""
Script para corrigir tipo do campo odoo_invoice_ids de VARCHAR(20) para TEXT
Executar localmente com venv ativado

Problema: Campo definido como VARCHAR(20) está causando erro ao salvar arrays JSON
Solução: Alterar para TEXT para comportar múltiplos IDs

Executar com:
python3 scripts/migrations/fix_odoo_invoice_ids_type.py
"""

import sys
import os

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def fix_odoo_invoice_ids_type():
    """Altera tipo do campo odoo_invoice_ids de VARCHAR(20) para TEXT"""

    app = create_app()

    with app.app_context():
        try:
            # Verificar tipo atual
            print("🔍 Verificando tipo atual do campo...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name = 'odoo_invoice_ids'
            """))

            row = result.fetchone()
            if row:
                print(f"   Tipo atual: {row[1]}({row[2] if row[2] else ''})")

            # Alterar para TEXT
            print("\n🔧 Alterando tipo do campo para TEXT...")
            db.session.execute(text("""
                ALTER TABLE conhecimento_transporte
                ALTER COLUMN odoo_invoice_ids TYPE TEXT
            """))

            db.session.commit()
            print("✅ Campo odoo_invoice_ids alterado para TEXT com sucesso!")

            # Verificar novamente
            print("\n🔍 Verificando tipo após alteração...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name = 'odoo_invoice_ids'
            """))

            row = result.fetchone()
            if row:
                print(f"   Tipo novo: {row[1]}({row[2] if row[2] else ''})")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao alterar campo: {str(e)}")
            return False

if __name__ == '__main__':
    print("=" * 70)
    print("CORREÇÃO DE TIPO DO CAMPO odoo_invoice_ids")
    print("=" * 70)
    print("\nProblema: ValueError - value too long for type character varying(20)")
    print("Solução: Alterar campo odoo_invoice_ids de VARCHAR(20) para TEXT\n")

    resposta = input("Deseja prosseguir? (s/n): ")

    if resposta.lower() == 's':
        sucesso = fix_odoo_invoice_ids_type()

        if sucesso:
            print("\n" + "=" * 70)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("❌ MIGRAÇÃO FALHOU - Verifique os erros acima")
            print("=" * 70)
    else:
        print("\n❌ Operação cancelada pelo usuário")
