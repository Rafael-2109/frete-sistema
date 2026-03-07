"""
Migration: Remover coluna is_permanent de agent_memories.

S6: Dead Code Cleanup — is_permanent é 100% redundante com category == 'permanent'.
Evidência: memory_mcp_tool.py _classify_memory_category() sempre retorna
is_permanent=True quando category='permanent', e False caso contrário.

Verificações BEFORE:
  1. Nenhum registro com is_permanent=true E category != 'permanent' (inconsistência)
  2. Nenhum registro com is_permanent=false E category = 'permanent' (inconsistência)

Execute:
  ALTER TABLE agent_memories DROP COLUMN is_permanent

Verificação AFTER:
  Confirmar que coluna não existe mais.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    app = create_app()

    with app.app_context():
        # ── BEFORE: verificar que coluna existe ──
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_memories'
              AND column_name = 'is_permanent'
        """))
        rows = result.fetchall()

        if not rows:
            print("[SKIP] Coluna is_permanent já não existe. Nada a fazer.")
            return

        print("[BEFORE] Coluna is_permanent encontrada. Verificando consistência...")

        # Verificação 1: is_permanent=true mas category != 'permanent'
        check1 = db.session.execute(text("""
            SELECT count(*)
            FROM agent_memories
            WHERE is_permanent = true AND category != 'permanent'
        """))
        count1 = check1.scalar()
        print(f"  is_permanent=true AND category!='permanent': {count1}")

        if count1 > 0:
            print(f"[ABORT] {count1} registros inconsistentes encontrados (is_permanent=true, category!=permanent).")
            print("         Corrija manualmente antes de executar esta migration.")
            return

        # Verificação 2: is_permanent=false mas category = 'permanent'
        check2 = db.session.execute(text("""
            SELECT count(*)
            FROM agent_memories
            WHERE is_permanent = false AND category = 'permanent'
        """))
        count2 = check2.scalar()
        print(f"  is_permanent=false AND category='permanent': {count2}")

        if count2 > 0:
            print(f"[ABORT] {count2} registros inconsistentes encontrados (is_permanent=false, category=permanent).")
            print("         Corrija manualmente antes de executar esta migration.")
            return

        print("[BEFORE] Consistência OK. Prosseguindo com DROP COLUMN...")

        # ── EXECUTE: remover coluna ──
        db.session.execute(text("""
            ALTER TABLE agent_memories DROP COLUMN is_permanent
        """))
        db.session.commit()
        print("[EXECUTE] ALTER TABLE agent_memories DROP COLUMN is_permanent — OK")

        # ── AFTER: confirmar remoção ──
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_memories'
              AND column_name = 'is_permanent'
        """))
        rows = result.fetchall()

        if rows:
            print("[ERROR] Coluna is_permanent ainda existe após DROP!")
        else:
            print("[AFTER] Coluna is_permanent removida com sucesso.")


if __name__ == '__main__':
    run_migration()
