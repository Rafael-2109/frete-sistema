"""
Migration: Limpeza de memorias baseada na auditoria de 2026-03-23

Contexto:
- Auditoria revelou 46 diretorios fantasma (29% do total) com content=NULL
- Termos genericos (empresa/termos) com 18.4% efetividade gastando tokens
- importance_score=0.7 impedia cold tier para empresa memories

Acoes:
1. Remover diretorios fantasma (is_directory=True, content=NULL)
2. Mover termos ineficazes para cold tier (usage>=20, effective=0)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def run():
    from app import create_app, db
    from sqlalchemy import text as sql_text

    app = create_app()
    with app.app_context():
        # ── BEFORE ──
        stats_before = db.session.execute(sql_text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_directory = true AND (content IS NULL OR content = ''))
                    as diretorios_fantasma,
                COUNT(*) FILTER (WHERE is_cold = true) as cold,
                COUNT(*) FILTER (
                    WHERE path LIKE '/memories/empresa/termos/%%'
                    AND is_directory = false
                    AND effective_count = 0
                    AND usage_count >= 20
                    AND is_cold = false
                ) as termos_candidatos_cold
            FROM agent_memories
        """)).mappings().first()

        print(f"=== ANTES ===")
        print(f"  Total memorias: {stats_before['total']}")
        print(f"  Diretorios fantasma: {stats_before['diretorios_fantasma']}")
        print(f"  Cold tier: {stats_before['cold']}")
        print(f"  Termos candidatos cold: {stats_before['termos_candidatos_cold']}")

        if stats_before['diretorios_fantasma'] == 0 and stats_before['termos_candidatos_cold'] == 0:
            print("\nNada a fazer. Migration ja aplicada.")
            return

        # ── PARTE 1: Remover diretorios fantasma ──
        if stats_before['diretorios_fantasma'] > 0:
            # Limpar dependencias (cascade pode nao cobrir queries bulk)
            for dep_table in ['agent_memory_embeddings', 'agent_memory_entity_links', 'agent_memory_versions']:
                db.session.execute(sql_text(f"""
                    DELETE FROM {dep_table}
                    WHERE memory_id IN (
                        SELECT id FROM agent_memories
                        WHERE is_directory = true AND (content IS NULL OR content = '')
                    )
                """))

            result = db.session.execute(sql_text("""
                DELETE FROM agent_memories
                WHERE is_directory = true AND (content IS NULL OR content = '')
            """))
            deleted = result.rowcount
            print(f"\n[PARTE 1] Removidos {deleted} diretorios fantasma")

        # ── PARTE 2: Termos ineficazes -> cold ──
        if stats_before['termos_candidatos_cold'] > 0:
            result = db.session.execute(sql_text("""
                UPDATE agent_memories
                SET is_cold = true
                WHERE path LIKE '/memories/empresa/termos/%%'
                  AND is_directory = false
                  AND effective_count = 0
                  AND usage_count >= 20
                  AND is_cold = false
            """))
            moved = result.rowcount
            print(f"[PARTE 2] Movidos {moved} termos ineficazes para cold tier")

        db.session.commit()

        # ── AFTER ──
        stats_after = db.session.execute(sql_text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_directory = true AND (content IS NULL OR content = ''))
                    as diretorios_fantasma,
                COUNT(*) FILTER (WHERE is_cold = true) as cold
            FROM agent_memories
        """)).mappings().first()

        print(f"\n=== APOS ===")
        print(f"  Total memorias: {stats_after['total']}")
        print(f"  Diretorios fantasma: {stats_after['diretorios_fantasma']}")
        print(f"  Cold tier: {stats_after['cold']}")
        print(f"\nMigration concluida com sucesso.")


if __name__ == '__main__':
    run()
