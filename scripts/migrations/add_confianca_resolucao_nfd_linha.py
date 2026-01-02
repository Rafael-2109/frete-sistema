#!/usr/bin/env python3
"""
Migracao: Adicionar campo confianca_resolucao na tabela nf_devolucao_linha

Este campo armazena o nivel de confianca (0.0 a 1.0) da resolucao
feita pelo AIResolverService (Claude Haiku 4.5).

Data: 30/12/2024
Autor: Sistema de Fretes - Modulo Devolucoes
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    """Adiciona campo confianca_resolucao na tabela nf_devolucao_linha."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna ja existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'nf_devolucao_linha'
                AND column_name = 'confianca_resolucao'
            """))

            if resultado.fetchone():
                print("Campo confianca_resolucao ja existe. Nada a fazer.")
                return True

            # Adicionar coluna
            print("Adicionando campo confianca_resolucao...")
            db.session.execute(text("""
                ALTER TABLE nf_devolucao_linha
                ADD COLUMN confianca_resolucao NUMERIC(5, 4)
            """))
            db.session.commit()

            print("Campo confianca_resolucao adicionado com sucesso!")
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
                SELECT column_name, data_type, numeric_precision, numeric_scale
                FROM information_schema.columns
                WHERE table_name = 'nf_devolucao_linha'
                AND column_name = 'confianca_resolucao'
            """))

            row = resultado.fetchone()
            if row:
                print(f"Campo encontrado:")
                print(f"  - Nome: {row[0]}")
                print(f"  - Tipo: {row[1]}")
                print(f"  - Precisao: {row[2]}")
                print(f"  - Escala: {row[3]}")
                return True
            else:
                print("Campo nao encontrado!")
                return False

        except Exception as e:
            print(f"Erro ao verificar: {e}")
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACAO: Adicionar confianca_resolucao em nf_devolucao_linha")
    print("=" * 60)

    if '--check' in sys.argv:
        verificar_migracao()
    else:
        if executar_migracao():
            print("\n" + "=" * 60)
            print("VERIFICANDO MIGRACAO...")
            verificar_migracao()
