#!/usr/bin/env python3
"""
Migracao: Adicionar campo info_complementar na tabela nf_devolucao

Este campo armazena o texto livre das informacoes complementares (tag infCpl)
extraido do XML da NFD. Contem o motivo da devolucao informado pelo cliente.

Data: 31/12/2024
Autor: Sistema de Fretes - Modulo Devolucoes

SQL para rodar diretamente no Shell do Render:
ALTER TABLE nf_devolucao ADD COLUMN info_complementar TEXT;
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    """Adiciona campo info_complementar na tabela nf_devolucao."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna ja existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'nf_devolucao'
                AND column_name = 'info_complementar'
            """))

            if resultado.fetchone():
                print("Campo info_complementar ja existe. Nada a fazer.")
                return True

            # Adicionar coluna
            print("Adicionando campo info_complementar...")
            db.session.execute(text("""
                ALTER TABLE nf_devolucao
                ADD COLUMN info_complementar TEXT
            """))
            db.session.commit()

            print("Campo info_complementar adicionado com sucesso!")
            return True

        except Exception as e:
            print(f"Erro na migracao: {e}")
            db.session.rollback()
            return False


def verificar_migracao():
    """Verifica se a migracao foi aplicada."""
    app = create_app()
    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'nf_devolucao'
                AND column_name = 'info_complementar'
            """))

            row = resultado.fetchone()
            if row:
                print(f"Campo encontrado:")
                print(f"  - Nome: {row[0]}")
                print(f"  - Tipo: {row[1]}")
                return True
            else:
                print("Campo nao encontrado!")
                return False

        except Exception as e:
            print(f"Erro ao verificar: {e}")
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACAO: Adicionar info_complementar em nf_devolucao")
    print("=" * 60)

    if '--check' in sys.argv:
        verificar_migracao()
    else:
        if executar_migracao():
            print("\n" + "=" * 60)
            print("VERIFICANDO MIGRACAO...")
            verificar_migracao()
