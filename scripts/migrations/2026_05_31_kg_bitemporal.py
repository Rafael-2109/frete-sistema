"""
Migration: D3 — Fatos bi-temporais + proveniência no Knowledge Graph (Onda 3).

Adiciona colunas de bi-temporalidade e proveniência nas tabelas de arestas do KG:
  • agent_memory_entity_relations: valid_from, valid_to, source_session_id, source_step_uid
  • agent_memory_entity_links:    source_session_id, source_step_uid

Idempotente via ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
Nenhum dado existente é alterado (todas as colunas são NULL por padrão).

Semântica:
  valid_from / valid_to  — tempo de validade do fato (bi-temporalidade); MVP: sempre NULL
  source_session_id      — sessão de origem (FK soft para agent_sessions.session_id)
  source_step_uid        — step de origem (FK soft para agent_step.step_uid; NULL no MVP)

Decisão de proveniência (1ª origem vence):
  ON CONFLICT em _upsert_relation usa COALESCE(existing, excluded) para preservar
  a source_session_id/source_step_uid do primeiro INSERT. Re-upserts não sobrescrevem.

Usage:
    python scripts/migrations/2026_05_31_kg_bitemporal.py
"""
import os
import sys

# Adiciona raiz do projeto ao sys.path quando script é executado direto
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

# Colunas esperadas após a migration
_EXPECTED_COLS = {
    'agent_memory_entity_relations': {
        'valid_from', 'valid_to', 'source_session_id', 'source_step_uid',
    },
    'agent_memory_entity_links': {
        'source_session_id', 'source_step_uid',
    },
}


def _get_columns(table_name: str) -> set:
    rows = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :t
    """), {'t': table_name}).fetchall()
    return {r[0] for r in rows}


def main() -> int:
    app = create_app()
    with app.app_context():
        # === Verificação BEFORE ===
        before_relations = _get_columns('agent_memory_entity_relations')
        before_links = _get_columns('agent_memory_entity_links')
        print("[before] agent_memory_entity_relations colunas:", sorted(before_relations))
        print("[before] agent_memory_entity_links colunas:", sorted(before_links))

        already_done = (
            _EXPECTED_COLS['agent_memory_entity_relations'].issubset(before_relations)
            and _EXPECTED_COLS['agent_memory_entity_links'].issubset(before_links)
        )
        if already_done:
            print("[info] Todas as colunas já existem — migration idempotente, nada a fazer.")
        else:
            print("[info] Aplicando migration D3 (bi-temporalidade + proveniência)...")

        # === DDL idempotente ===
        db.session.execute(text("""
            ALTER TABLE agent_memory_entity_relations
              ADD COLUMN IF NOT EXISTS valid_from        TIMESTAMP NULL,
              ADD COLUMN IF NOT EXISTS valid_to          TIMESTAMP NULL,
              ADD COLUMN IF NOT EXISTS source_session_id TEXT NULL,
              ADD COLUMN IF NOT EXISTS source_step_uid   TEXT NULL
        """))
        db.session.execute(text("""
            ALTER TABLE agent_memory_entity_links
              ADD COLUMN IF NOT EXISTS source_session_id TEXT NULL,
              ADD COLUMN IF NOT EXISTS source_step_uid   TEXT NULL
        """))
        db.session.commit()

        # === Verificação AFTER ===
        after_relations = _get_columns('agent_memory_entity_relations')
        after_links = _get_columns('agent_memory_entity_links')
        print("[after] agent_memory_entity_relations colunas:", sorted(after_relations))
        print("[after] agent_memory_entity_links colunas:", sorted(after_links))

        missing_relations = _EXPECTED_COLS['agent_memory_entity_relations'] - after_relations
        missing_links = _EXPECTED_COLS['agent_memory_entity_links'] - after_links

        if missing_relations or missing_links:
            print(f"[erro] Colunas faltando em relations: {missing_relations}")
            print(f"[erro] Colunas faltando em links: {missing_links}")
            return 1

        print("[ok] Migration D3 concluída com sucesso (idempotente).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
