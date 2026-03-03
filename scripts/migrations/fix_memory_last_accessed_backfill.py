"""
Fix: Corrigir backfill de last_accessed_at em agent_memories.

PROBLEMA: A migration original usava `DEFAULT NOW()` ao adicionar a coluna,
o que setou TODOS os registros existentes com o timestamp da migration.
Isso faz com que o decay scoring trate todas as memórias como "recém acessadas"
(decay ≈ 1.0), anulando o efeito do recency decay no composite scoring.

CORREÇÃO: Sobrescrever last_accessed_at com updated_at (semanticamente correto)
para registros que nunca foram genuinamente acessados pelo sistema de injeção.

Também adiciona NOT NULL constraint (faltava na versão original da migration).

Executar:
    source .venv/bin/activate
    python scripts/migrations/fix_memory_last_accessed_backfill.py

Verificar:
    python scripts/migrations/fix_memory_last_accessed_backfill.py --verificar

Dry-run:
    python scripts/migrations/fix_memory_last_accessed_backfill.py --dry-run
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def fix(dry_run: bool = False):
    """Corrige backfill de last_accessed_at."""
    print("\n=== Fix: memory last_accessed_at backfill ===\n")

    # 1. Diagnosticar estado atual
    result = db.session.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE last_accessed_at IS NOT NULL) AS has_value,
            COUNT(*) FILTER (WHERE last_accessed_at IS NULL) AS null_count,
            COUNT(*) FILTER (
                WHERE last_accessed_at IS NOT NULL
                AND updated_at IS NOT NULL
                AND ABS(EXTRACT(EPOCH FROM (last_accessed_at - updated_at))) > 60
            ) AS likely_migration_artifact
        FROM agent_memories
        WHERE is_directory = false
    """))
    row = result.fetchone()
    total = row.total
    has_value = row.has_value
    null_count = row.null_count
    likely_artifact = row.likely_migration_artifact

    print(f"   Total memórias (não-diretório): {total}")
    print(f"   Com last_accessed_at: {has_value}")
    print(f"   Sem last_accessed_at (NULL): {null_count}")
    print(f"   Provável artefato da migration (last_accessed != updated_at): {likely_artifact}")

    if total == 0:
        print("\n   Nenhuma memória encontrada. Nada a fazer.\n")
        return

    # 2. Corrigir: setar last_accessed_at = COALESCE(updated_at, created_at)
    # Isso sobrescreve o valor de migration (NOW()) com o valor semântico correto
    # É seguro porque o código de injeção (client.py) NÃO estava deployed quando
    # a migration original rodou — nenhum valor legítimo será perdido.
    if dry_run:
        print(f"\n   [DRY-RUN] {total} registros seriam atualizados.\n")
        return

    result = db.session.execute(text("""
        UPDATE agent_memories
        SET last_accessed_at = COALESCE(updated_at, created_at, NOW())
        WHERE is_directory = false
    """))
    rows_updated = result.rowcount
    db.session.commit()
    print(f"\n   Atualizados: {rows_updated} registros")

    # 3. Garantir NOT NULL + DEFAULT (pode já estar OK se re-rodou a migration)
    try:
        db.session.execute(text(
            "ALTER TABLE agent_memories ALTER COLUMN last_accessed_at SET NOT NULL"
        ))
        db.session.commit()
        print("   NOT NULL constraint: adicionada")
    except Exception as e:
        db.session.rollback()
        if 'already' in str(e).lower() or 'violates' in str(e).lower():
            print("   NOT NULL constraint: já existe")
        else:
            print(f"   NOT NULL constraint: falhou — {e}")

    try:
        db.session.execute(text(
            "ALTER TABLE agent_memories ALTER COLUMN last_accessed_at SET DEFAULT NOW()"
        ))
        db.session.commit()
        print("   DEFAULT NOW(): configurado")
    except Exception as e:
        db.session.rollback()
        print(f"   DEFAULT NOW(): falhou — {e}")

    # 4. Garantir NOT NULL em importance_score também
    try:
        db.session.execute(text(
            "ALTER TABLE agent_memories ALTER COLUMN importance_score SET NOT NULL"
        ))
        db.session.commit()
        print("   importance_score NOT NULL: adicionada")
    except Exception as e:
        db.session.rollback()
        if 'already' in str(e).lower():
            print("   importance_score NOT NULL: já existe")
        else:
            # Pode ter NULLs — preencher antes
            try:
                db.session.execute(text(
                    "UPDATE agent_memories SET importance_score = 0.5 WHERE importance_score IS NULL"
                ))
                db.session.commit()
                db.session.execute(text(
                    "ALTER TABLE agent_memories ALTER COLUMN importance_score SET NOT NULL"
                ))
                db.session.commit()
                print("   importance_score NOT NULL: backfill + constraint adicionados")
            except Exception as e2:
                db.session.rollback()
                print(f"   importance_score NOT NULL: falhou — {e2}")

    verify()


def verify():
    """Verifica estado após correção."""
    print("\n--- Verificação ---")

    result = db.session.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE last_accessed_at IS NULL) AS null_accessed,
            COUNT(*) FILTER (WHERE importance_score IS NULL) AS null_importance,
            AVG(EXTRACT(EPOCH FROM (last_accessed_at - COALESCE(updated_at, created_at)))::float)
                AS avg_diff_seconds
        FROM agent_memories
        WHERE is_directory = false
    """))
    row = result.fetchone()

    checks = [
        ("Total memórias", f"{row.total}"),
        ("last_accessed_at NULL", f"{row.null_accessed}" + (" — OK" if row.null_accessed == 0 else " — PENDENTE")),
        ("importance_score NULL", f"{row.null_importance}" + (" — OK" if row.null_importance == 0 else " — PENDENTE")),
        ("Diff média last_accessed vs updated_at", f"{row.avg_diff_seconds:.1f}s" if row.avg_diff_seconds else "N/A"),
    ]

    for desc, value in checks:
        print(f"   {desc}: {value}")

    all_ok = row.null_accessed == 0 and row.null_importance == 0
    # Se a diff média é pequena (< 1s), significa que last_accessed ≈ updated_at (correto)
    if row.avg_diff_seconds and abs(row.avg_diff_seconds) < 1:
        print("   Backfill: CORRETO (last_accessed_at ≈ updated_at)")
    elif row.avg_diff_seconds and abs(row.avg_diff_seconds) > 3600:
        print("   Backfill: ALERTA — last_accessed_at difere muito de updated_at (pode ser artefato)")

    print(f"\n{'   FIX COMPLETO' if all_ok else '   FIX INCOMPLETO'}\n")
    return all_ok


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        if '--verificar' in sys.argv:
            verify()
        else:
            dry_run = '--dry-run' in sys.argv
            fix(dry_run=dry_run)
