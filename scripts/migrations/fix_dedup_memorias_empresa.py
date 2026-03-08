"""
Fix: Remove 7 memorias empresa duplicadas causadas por bug no dedup.

Causa raiz: _check_memory_duplicate() comparava XML raw contra embeddings
gerados a partir de texto contextual enriquecido pelo Sonnet, resultando
em similarity ~0.69 (abaixo do threshold 0.90). Fix aplicado em
memory_mcp_tool.py: strip_xml_tags() + threshold 0.85.

Duplicatas confirmadas em producao (2026-03-07):
  ID 155 = dup de 139 (Atacadao NF completa)
  ID 156 = dup de 110 (Pedidos Assai)
  ID 157 = dup de 111 (Assai multiplas lojas)
  ID 158 = dup de 112 (Dry-run obrigatorio)
  ID 160 = correcao Gilberto (dup semantica)
  ID 161 = dup de 139 (Atacadao NF completa, 3a copia)
  ID 162 = dup de 160 (Gilberto, 2a copia)

Cascades:
  - agent_memory_entity_links: ON DELETE CASCADE (auto)
  - agent_memory_entity_relations: ON DELETE SET NULL (mantém relação, seta memory_id=NULL)
  - agent_memory_embeddings: FK lógica (precisa deletar manualmente)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text

DUPLICATE_IDS = [155, 156, 157, 158, 160, 161, 162]

# Mapeamento para log legível
DUPLICATE_MAP = {
    155: 'dup de 139 (atacadao-sempre-pede-nf-completa)',
    156: 'dup de 110 (pedidos-para-a-rede-assai)',
    157: 'dup de 111 (a-rede-assai-opera-com-multiplas-lojas)',
    158: 'dup de 112 (antes-de-executar-acoes-em-lote-no-odoo)',
    160: 'correcao gilberto (primeira)',
    161: 'dup de 139 (atacadao NF completa, 3a copia)',
    162: 'dup de 160 (gilberto, 2a copia)',
}


def run():
    app = create_app()
    with app.app_context():
        # ── BEFORE: Contagem ──
        before_mems = db.session.execute(
            text("SELECT COUNT(*) FROM agent_memories WHERE user_id = 0")
        ).scalar()
        before_embeddings = db.session.execute(
            text("SELECT COUNT(*) FROM agent_memory_embeddings WHERE memory_id IN :ids"),
            {'ids': tuple(DUPLICATE_IDS)}
        ).scalar()
        before_links = db.session.execute(
            text("SELECT COUNT(*) FROM agent_memory_entity_links WHERE memory_id IN :ids"),
            {'ids': tuple(DUPLICATE_IDS)}
        ).scalar()
        before_relations = db.session.execute(
            text("SELECT COUNT(*) FROM agent_memory_entity_relations WHERE memory_id IN :ids"),
            {'ids': tuple(DUPLICATE_IDS)}
        ).scalar()

        print(f"=== BEFORE ===")
        print(f"Memorias empresa: {before_mems}")
        print(f"Embeddings a deletar: {before_embeddings}")
        print(f"Entity links a deletar (CASCADE): {before_links}")
        print(f"Entity relations a setar NULL: {before_relations}")
        print()

        # Verificar que os IDs existem
        existing = db.session.execute(
            text("SELECT id, path FROM agent_memories WHERE id IN :ids ORDER BY id"),
            {'ids': tuple(DUPLICATE_IDS)}
        ).fetchall()

        if not existing:
            print("NENHUMA duplicata encontrada. Já foi limpo?")
            return

        print(f"Duplicatas encontradas ({len(existing)}/{len(DUPLICATE_IDS)}):")
        for row in existing:
            reason = DUPLICATE_MAP.get(row[0], '?')
            print(f"  ID {row[0]}: {row[1]} — {reason}")
        print()

        # ── DRY RUN check ──
        if '--execute' not in sys.argv:
            print("DRY RUN — nenhuma mudança feita.")
            print("Para executar: python scripts/migrations/fix_dedup_memorias_empresa.py --execute")
            return

        existing_ids = tuple(row[0] for row in existing)

        # 1. Deletar embeddings (FK lógica, sem cascade)
        deleted_embeddings = db.session.execute(
            text("DELETE FROM agent_memory_embeddings WHERE memory_id IN :ids"),
            {'ids': existing_ids}
        ).rowcount
        print(f"Embeddings deletados: {deleted_embeddings}")

        # 2. Deletar memórias (entity_links CASCADE, relations SET NULL)
        deleted_mems = db.session.execute(
            text("DELETE FROM agent_memories WHERE id IN :ids"),
            {'ids': existing_ids}
        ).rowcount
        print(f"Memórias deletadas: {deleted_mems}")

        db.session.commit()

        # ── AFTER: Verificação ──
        after_mems = db.session.execute(
            text("SELECT COUNT(*) FROM agent_memories WHERE user_id = 0")
        ).scalar()
        after_links = db.session.execute(
            text("SELECT COUNT(*) FROM agent_memory_entity_links WHERE memory_id IN :ids"),
            {'ids': tuple(DUPLICATE_IDS)}
        ).scalar()
        after_null_relations = db.session.execute(
            text("SELECT COUNT(*) FROM agent_memory_entity_relations WHERE memory_id IS NULL")
        ).scalar()

        print()
        print(f"=== AFTER ===")
        removidas = (before_mems or 0) - (after_mems or 0)
        print(f"Memorias empresa: {after_mems} (era {before_mems}, removidas {removidas})")
        print(f"Entity links restantes para IDs removidos: {after_links} (esperado: 0)")
        print(f"Entity relations com memory_id=NULL: {after_null_relations}")
        print()
        print("OK — Sanitização concluída com sucesso.")


if __name__ == '__main__':
    run()
