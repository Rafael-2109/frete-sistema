"""
Migration: Memory System v2 — Taxonomia + Feedback Loop

Adiciona campos ao agent_memories:
- category (VARCHAR 20): permanent, structural, operational, contextual, cold
- is_permanent (BOOLEAN): memorias que nunca decaem
- is_cold (BOOLEAN): tier frio (sem injecao automatica)
- usage_count (INTEGER): vezes injetada
- effective_count (INTEGER): vezes usada na resposta
- correction_count (INTEGER): vezes corrigida pelo usuario
- has_potential_conflict (BOOLEAN): contradicao detectada

Backfill classifica memorias existentes por heuristica de path + content.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    app = create_app()

    with app.app_context():
        # ── Before: verificar estado atual ──
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_memories'
            ORDER BY ordinal_position
        """))
        existing_columns = {row[0] for row in result}
        print(f"[BEFORE] Colunas existentes: {sorted(existing_columns)}")

        new_columns = {
            'category', 'is_permanent', 'is_cold',
            'usage_count', 'effective_count', 'correction_count',
            'has_potential_conflict',
        }
        missing = new_columns - existing_columns
        if not missing:
            print("[SKIP] Todas as colunas v2 já existem. Nada a fazer.")
            return

        print(f"[MIGRATE] Colunas a adicionar: {sorted(missing)}")

        # ── DDL: adicionar colunas ──
        ddl_map = {
            'category': "ALTER TABLE agent_memories ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'operational'",
            'is_permanent': "ALTER TABLE agent_memories ADD COLUMN is_permanent BOOLEAN NOT NULL DEFAULT FALSE",
            'is_cold': "ALTER TABLE agent_memories ADD COLUMN is_cold BOOLEAN NOT NULL DEFAULT FALSE",
            'usage_count': "ALTER TABLE agent_memories ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0",
            'effective_count': "ALTER TABLE agent_memories ADD COLUMN effective_count INTEGER NOT NULL DEFAULT 0",
            'correction_count': "ALTER TABLE agent_memories ADD COLUMN correction_count INTEGER NOT NULL DEFAULT 0",
            'has_potential_conflict': "ALTER TABLE agent_memories ADD COLUMN has_potential_conflict BOOLEAN NOT NULL DEFAULT FALSE",
        }

        for col, ddl in ddl_map.items():
            if col in missing:
                print(f"  ADD COLUMN {col}...")
                db.session.execute(text(ddl))

        # Índice em category
        if 'category' in missing:
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_agent_memories_category ON agent_memories (category)"
            ))

        db.session.commit()
        print("[DDL] Colunas adicionadas com sucesso.")

        # ── Backfill: classificar memorias existentes ──
        print("[BACKFILL] Classificando memorias existentes...")

        # user.xml e preferences.xml → permanent
        r1 = db.session.execute(text("""
            UPDATE agent_memories
            SET category = 'permanent', is_permanent = TRUE
            WHERE path IN ('/memories/user.xml', '/memories/preferences.xml')
              AND category = 'operational'
        """))
        print(f"  permanent (user/prefs): {r1.rowcount}")

        # corrections/ com keywords estruturais → structural
        r2 = db.session.execute(text("""
            UPDATE agent_memories
            SET category = 'structural'
            WHERE category = 'operational'
              AND path LIKE '/memories/corrections/%'
              AND (
                lower(content) LIKE '%timeout%'
                OR lower(content) LIKE '%campo%'
                OR lower(content) LIKE '%fk%'
                OR lower(content) LIKE '%constraint%'
                OR lower(content) LIKE '%empresa%'
                OR lower(content) LIKE '%odoo%'
                OR lower(content) LIKE '%%nao existe%%'
              )
        """))
        print(f"  structural (corrections keywords): {r2.rowcount}")

        # corrections/ com keywords permanentes → permanent
        r3 = db.session.execute(text("""
            UPDATE agent_memories
            SET category = 'permanent', is_permanent = TRUE
            WHERE category IN ('operational', 'structural')
              AND path LIKE '/memories/corrections/%'
              AND (
                lower(content) LIKE '%scope%'
                OR lower(content) LIKE '%escopo%'
                OR lower(content) LIKE '%permiss%'
                OR lower(content) LIKE '%regra%'
                OR lower(content) LIKE '%proibido%'
                OR lower(content) LIKE '%obrigat%'
              )
        """))
        print(f"  permanent (corrections scope): {r3.rowcount}")

        # context/ → contextual
        r4 = db.session.execute(text("""
            UPDATE agent_memories
            SET category = 'contextual'
            WHERE category = 'operational'
              AND path LIKE '/memories/context/%'
        """))
        print(f"  contextual (context/): {r4.rowcount}")

        # Remaining corrections/ → structural (default)
        r5 = db.session.execute(text("""
            UPDATE agent_memories
            SET category = 'structural'
            WHERE category = 'operational'
              AND path LIKE '/memories/corrections/%'
        """))
        print(f"  structural (remaining corrections): {r5.rowcount}")

        # Índice parcial para não-frias
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_agent_memories_not_cold
                ON agent_memories (user_id, category)
                WHERE is_cold = FALSE
        """))

        db.session.commit()

        # ── After: verificar ──
        result = db.session.execute(text("""
            SELECT category, count(*), sum(case when is_permanent then 1 else 0 end) as permanent_count
            FROM agent_memories
            WHERE is_directory = FALSE
            GROUP BY category
            ORDER BY category
        """))
        print("\n[AFTER] Distribuição por categoria:")
        for row in result:
            print(f"  {row[0]}: {row[1]} memorias ({row[2]} permanentes)")

        print("\n[DONE] Migration v2 taxonomia+feedback concluída.")


if __name__ == '__main__':
    run_migration()
