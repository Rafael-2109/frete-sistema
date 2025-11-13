"""
Migration: Adicionar campos de NF no PedidoCompras
==================================================

OBJETIVO: Adicionar campos para armazenar informações e arquivos (PDF/XML)
          das Notas Fiscais de entrada vinculadas aos pedidos de compras

CAMPOS ADICIONADOS:
    - dfe_id: ID do documento fiscal no Odoo
    - nf_pdf_path: Caminho S3/local do PDF
    - nf_xml_path: Caminho S3/local do XML
    - nf_chave_acesso: Chave de acesso da NFe (44 dígitos)
    - nf_numero: Número da NF
    - nf_serie: Série da NF
    - nf_data_emissao: Data de emissão
    - nf_valor_total: Valor total da NF

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

def adicionar_campos_nf():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 MIGRATION: Adicionar campos NF em pedido_compras")
            print("=" * 80)

            # 1. Verificar se campos já existem
            print("\n1️⃣ Verificando campos existentes...")

            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name IN (
                    'dfe_id', 'nf_pdf_path', 'nf_xml_path', 'nf_chave_acesso',
                    'nf_numero', 'nf_serie', 'nf_data_emissao', 'nf_valor_total'
                )
            """))

            campos_existentes = [row[0] for row in resultado]

            if len(campos_existentes) == 8:
                print("⚠️  Todos os campos já existem! Migration já foi aplicada.")
                return

            print(f"✅ Campos encontrados: {len(campos_existentes)}/8")
            if campos_existentes:
                print(f"   Existentes: {', '.join(campos_existentes)}")

            # 2. Adicionar campos
            print("\n2️⃣ Adicionando novos campos...")

            campos_sql = [
                ("dfe_id", "VARCHAR(50)"),
                ("nf_pdf_path", "VARCHAR(500)"),
                ("nf_xml_path", "VARCHAR(500)"),
                ("nf_chave_acesso", "VARCHAR(44)"),
                ("nf_numero", "VARCHAR(20)"),
                ("nf_serie", "VARCHAR(10)"),
                ("nf_data_emissao", "DATE"),
                ("nf_valor_total", "NUMERIC(15, 2)")
            ]

            for campo, tipo in campos_sql:
                if campo not in campos_existentes:
                    print(f"   ➕ Adicionando {campo} ({tipo})...")
                    db.session.execute(text(f"""
                        ALTER TABLE pedido_compras
                        ADD COLUMN IF NOT EXISTS {campo} {tipo}
                    """))

            db.session.commit()
            print("✅ Campos adicionados com sucesso!")

            # 3. Criar índices
            print("\n3️⃣ Criando índices...")

            indices = [
                ("idx_pedido_dfe", "dfe_id"),
                ("idx_pedido_chave_acesso", "nf_chave_acesso")
            ]

            for nome_indice, campo in indices:
                try:
                    print(f"   📊 Criando índice {nome_indice}...")
                    db.session.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {nome_indice}
                        ON pedido_compras ({campo})
                    """))
                except Exception as e:
                    print(f"   ⚠️  Índice {nome_indice} pode já existir: {e}")

            db.session.commit()
            print("✅ Índices criados com sucesso!")

            # 4. Verificar resultado final
            print("\n4️⃣ Verificando estrutura final...")

            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name LIKE 'nf_%' OR column_name = 'dfe_id'
                ORDER BY column_name
            """))

            print("\n📋 Campos NF em pedido_compras:")
            for row in resultado:
                nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                print(f"   ✅ {row[0]:<20} {row[1]:<15} {nullable}")

            print("\n" + "=" * 80)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            raise

if __name__ == '__main__':
    adicionar_campos_nf()
