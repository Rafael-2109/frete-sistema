# -*- coding: utf-8 -*-
"""
Migração: Alterar constraint de statement_id para unique composto
=================================================================

PROBLEMA:
- O campo statement_id tinha unique=True, impedindo que o mesmo extrato
  tivesse lotes de entrada (recebimentos) E saída (pagamentos).

SOLUÇÃO:
- Remover constraint unique simples de statement_id
- Adicionar constraint unique composta (statement_id + tipo_transacao)

EXECUÇÃO LOCAL:
    source $([ -d venv ] && echo venv || echo .venv)/bin/activate
    python scripts/migrations/alterar_constraint_extrato_lote.py

EXECUÇÃO NO RENDER (Shell):
    Copiar e colar o SQL abaixo diretamente no Shell do banco.

Data: 2025-12-13
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    """Executa a migração para alterar constraint de extrato_lote."""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRAÇÃO: Alterar constraint de extrato_lote")
            print("=" * 60)

            # Verificar constraints existentes
            print("\n1. Verificando constraints existentes...")
            resultado = db.session.execute(text("""
                SELECT conname, contype
                FROM pg_constraint
                WHERE conrelid = 'extrato_lote'::regclass
                AND contype = 'u'
            """))
            constraints = resultado.fetchall()
            print(f"   Constraints unique encontradas: {[c[0] for c in constraints]}")

            # Remover constraint unique simples de statement_id (se existir)
            print("\n2. Removendo constraint unique simples de statement_id...")
            try:
                # O nome padrão gerado pelo SQLAlchemy para unique
                db.session.execute(text("""
                    ALTER TABLE extrato_lote
                    DROP CONSTRAINT IF EXISTS extrato_lote_statement_id_key
                """))
                print("   - Constraint 'extrato_lote_statement_id_key' removida (ou não existia)")
            except Exception as e:
                print(f"   - Aviso: {e}")

            # Verificar se a nova constraint já existe
            print("\n3. Verificando se nova constraint já existe...")
            resultado = db.session.execute(text("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_extrato_lote_statement_tipo'
            """))
            existe = resultado.fetchone()

            if existe:
                print("   - Constraint 'uq_extrato_lote_statement_tipo' já existe!")
            else:
                # Adicionar nova constraint unique composta
                print("\n4. Adicionando constraint unique composta (statement_id + tipo_transacao)...")
                db.session.execute(text("""
                    ALTER TABLE extrato_lote
                    ADD CONSTRAINT uq_extrato_lote_statement_tipo
                    UNIQUE (statement_id, tipo_transacao)
                """))
                print("   - Constraint 'uq_extrato_lote_statement_tipo' adicionada!")

            db.session.commit()

            # Verificar resultado
            print("\n5. Verificando constraints finais...")
            resultado = db.session.execute(text("""
                SELECT conname, contype
                FROM pg_constraint
                WHERE conrelid = 'extrato_lote'::regclass
                AND contype = 'u'
            """))
            constraints = resultado.fetchall()
            print(f"   Constraints unique: {[c[0] for c in constraints]}")

            print("\n" + "=" * 60)
            print("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)

        except Exception as e:
            print(f"\nERRO: {e}")
            db.session.rollback()
            raise


# SQL para executar diretamente no Shell do Render
SQL_RENDER = """
-- =============================================================================
-- SQL PARA EXECUÇÃO NO RENDER (copiar e colar no Shell do banco)
-- =============================================================================

-- 1. Remover constraint unique simples (se existir)
ALTER TABLE extrato_lote
DROP CONSTRAINT IF EXISTS extrato_lote_statement_id_key;

-- 2. Adicionar constraint unique composta
ALTER TABLE extrato_lote
ADD CONSTRAINT uq_extrato_lote_statement_tipo
UNIQUE (statement_id, tipo_transacao);

-- 3. Verificar resultado
SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'extrato_lote'::regclass
AND contype = 'u';
"""


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SQL PARA RENDER:")
    print("=" * 60)
    print(SQL_RENDER)
    print("\n")

    resposta = input("Executar migração localmente? (s/n): ").strip().lower()
    if resposta == 's':
        executar_migracao()
    else:
        print("Migração cancelada.")
