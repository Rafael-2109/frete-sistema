# -*- coding: utf-8 -*-
"""
Migration: Adiciona campos de inconsistência Odoo em contas_a_receber
=====================================================================

Adiciona 3 campos para rastrear divergências entre dados locais e Odoo:
- inconsistencia_odoo: tipo da inconsistência (PAGO_LOCAL_ABERTO_ODOO, etc.)
- inconsistencia_detectada_em: timestamp de quando foi detectada
- inconsistencia_resolvida_em: timestamp de quando foi resolvida

Também cria índice parcial para consultas eficientes de registros com flag ativo.

Executar: python scripts/migrations/add_inconsistencia_odoo_contas_receber.py
"""

import os
import sys

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'contas_a_receber'
          AND column_name IN ('inconsistencia_odoo', 'inconsistencia_detectada_em', 'inconsistencia_resolvida_em')
        ORDER BY column_name
    """))
    colunas_existentes = [row[0] for row in result]

    if colunas_existentes:
        print(f"[ANTES] Colunas já existem: {colunas_existentes}")
        return True  # Já migrado
    else:
        print("[ANTES] Nenhuma coluna de inconsistência encontrada — migration necessária")
        return False


def executar_migration():
    """Executa a migration: adiciona campos + índice."""
    print("\n[MIGRATION] Adicionando campos de inconsistência Odoo...")

    # 1. Campo inconsistencia_odoo (VARCHAR 50)
    db.session.execute(text("""
        ALTER TABLE contas_a_receber
        ADD COLUMN IF NOT EXISTS inconsistencia_odoo VARCHAR(50)
    """))
    print("  ✓ Campo inconsistencia_odoo adicionado")

    # 2. Campo inconsistencia_detectada_em (TIMESTAMP)
    db.session.execute(text("""
        ALTER TABLE contas_a_receber
        ADD COLUMN IF NOT EXISTS inconsistencia_detectada_em TIMESTAMP
    """))
    print("  ✓ Campo inconsistencia_detectada_em adicionado")

    # 3. Campo inconsistencia_resolvida_em (TIMESTAMP)
    db.session.execute(text("""
        ALTER TABLE contas_a_receber
        ADD COLUMN IF NOT EXISTS inconsistencia_resolvida_em TIMESTAMP
    """))
    print("  ✓ Campo inconsistencia_resolvida_em adicionado")

    # 4. Índice parcial para registros com inconsistência ativa
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_contas_a_receber_inconsistencia
        ON contas_a_receber(inconsistencia_odoo)
        WHERE inconsistencia_odoo IS NOT NULL
    """))
    print("  ✓ Índice parcial idx_contas_a_receber_inconsistencia criado")

    db.session.commit()
    print("\n[MIGRATION] Concluída com sucesso!")


def verificar_depois():
    """Verifica estado após a migration."""
    result = db.session.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'contas_a_receber'
          AND column_name IN ('inconsistencia_odoo', 'inconsistencia_detectada_em', 'inconsistencia_resolvida_em')
        ORDER BY column_name
    """))
    colunas = [(row[0], row[1]) for row in result]
    print(f"\n[DEPOIS] Colunas encontradas: {colunas}")

    # Verificar índice
    result_idx = db.session.execute(text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'contas_a_receber'
          AND indexname = 'idx_contas_a_receber_inconsistencia'
    """))
    indices = [row[0] for row in result_idx]
    print(f"[DEPOIS] Índice encontrado: {indices}")

    assert len(colunas) == 3, f"Esperado 3 colunas, encontrado {len(colunas)}"
    assert len(indices) == 1, f"Esperado 1 índice, encontrado {len(indices)}"
    print("\n✅ Verificação pós-migration OK!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        ja_migrado = verificar_antes()

        if not ja_migrado:
            executar_migration()

        verificar_depois()
