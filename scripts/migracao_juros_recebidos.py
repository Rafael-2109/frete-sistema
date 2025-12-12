# -*- coding: utf-8 -*-
"""
Migracao: Adicionar campos para lancamento de juros recebidos
==============================================================

Adiciona os campos necessarios para suportar lancamento de juros
separado no servico de baixa de titulos.

Novos campos na tabela baixa_titulo_item:
- juros_excel: Float (valor de juros do Excel)
- payment_juros_odoo_id: Integer (ID do pagamento de juros no Odoo)
- payment_juros_odoo_name: String(100) (nome do pagamento de juros)

Uso:
    python scripts/migracao_juros_recebidos.py

Autor: Sistema de Fretes
Data: 2025-12-12
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def migrar():
    """Executa a migracao para adicionar campos de juros."""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRACAO: Campos para lancamento de juros recebidos")
            print("=" * 60)

            # Verificar se os campos ja existem
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'baixa_titulo_item'
                AND column_name IN ('juros_excel', 'payment_juros_odoo_id', 'payment_juros_odoo_name')
            """))
            colunas_existentes = [row[0] for row in resultado.fetchall()]

            campos_adicionados = []

            # Adicionar juros_excel se nao existir
            if 'juros_excel' not in colunas_existentes:
                print("Adicionando campo: juros_excel (Float)")
                db.session.execute(text("""
                    ALTER TABLE baixa_titulo_item
                    ADD COLUMN juros_excel FLOAT DEFAULT 0
                """))
                campos_adicionados.append('juros_excel')
            else:
                print("Campo juros_excel ja existe")

            # Adicionar payment_juros_odoo_id se nao existir
            if 'payment_juros_odoo_id' not in colunas_existentes:
                print("Adicionando campo: payment_juros_odoo_id (Integer)")
                db.session.execute(text("""
                    ALTER TABLE baixa_titulo_item
                    ADD COLUMN payment_juros_odoo_id INTEGER
                """))
                campos_adicionados.append('payment_juros_odoo_id')
            else:
                print("Campo payment_juros_odoo_id ja existe")

            # Adicionar payment_juros_odoo_name se nao existir
            if 'payment_juros_odoo_name' not in colunas_existentes:
                print("Adicionando campo: payment_juros_odoo_name (String 100)")
                db.session.execute(text("""
                    ALTER TABLE baixa_titulo_item
                    ADD COLUMN payment_juros_odoo_name VARCHAR(100)
                """))
                campos_adicionados.append('payment_juros_odoo_name')
            else:
                print("Campo payment_juros_odoo_name ja existe")

            db.session.commit()

            print("-" * 60)
            if campos_adicionados:
                print(f"Campos adicionados: {', '.join(campos_adicionados)}")
            else:
                print("Nenhum campo novo adicionado (todos ja existem)")
            print("Migracao concluida com sucesso!")
            print("=" * 60)

        except Exception as e:
            print(f"Erro na migracao: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrar()
