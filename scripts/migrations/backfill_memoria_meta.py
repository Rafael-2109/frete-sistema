"""Backfill do formato canonico de memorias: popula agent_memories.meta.

Para cada memoria ESTRUTURADA (heuristica/armadilha/protocolo/correcao), parseia o
`content` legado (qualquer um dos 5 formatos: bracket, <heuristica>, <conhecimento>,
code-fence, pseudo-XML) para o dict canonico `meta`, e — SOMENTE quando o parse e
'full' (titulo + do extraidos com seguranca) — re-renderiza o content para o sentinela
canonico. Memorias 'partial'/'raw' preservam o content original (zero perda) e ainda
recebem meta best-effort.

Data-fix (sem DDL): a coluna `meta` ja foi criada pela migration
2026_06_08_agent_memories_meta_jsonb.py. Rode-a ANTES deste backfill.

Modos:
  (default)        DRY-RUN local: reporta estatisticas, NAO grava.
  --apply          Efetiva no banco do ambiente (DATABASE_URL).
  --all            Reprocessa tambem memorias que JA tem meta (re-normaliza).
  --validate-prod  READ-ONLY contra DATABASE_URL_PROD: roda o parser sobre os dados
                   reais de producao e reporta cobertura. NUNCA escreve.

Uso:
    python scripts/migrations/backfill_memoria_meta.py                 # dry-run local
    python scripts/migrations/backfill_memoria_meta.py --validate-prod # prova contra PROD
    python scripts/migrations/backfill_memoria_meta.py --apply         # efetiva local
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agente.services.memory_format import (
    parse_memory, render_content, is_structured_path,
)


def _classificar(rows):
    """Roda o parser sobre [(path, content, meta_atual)] e retorna (stats, exemplos_raw)."""
    stats = {
        "estruturadas": 0, "nao_estruturadas": 0, "ja_tem_meta": 0,
        "full": 0, "partial": 0, "raw": 0,
        "content_normalizaria": 0, "erros": 0,
    }
    exemplos_raw = []
    plano = []  # (idx, meta, novo_content_ou_None)
    for idx, path, content, meta_atual in rows:
        if not is_structured_path(path):
            stats["nao_estruturadas"] += 1
            continue
        stats["estruturadas"] += 1
        if meta_atual:
            stats["ja_tem_meta"] += 1
        try:
            meta = parse_memory(content or "")
        except Exception:
            stats["erros"] += 1
            continue
        stats[meta["parse"]] += 1
        novo_content = None
        if meta["parse"] == "full":
            rc = render_content(meta)
            if rc != (content or ""):
                novo_content = rc
                stats["content_normalizaria"] += 1
        elif meta["parse"] == "raw" and len(exemplos_raw) < 8:
            exemplos_raw.append(path)
        plano.append((idx, meta, novo_content))
    return stats, exemplos_raw, plano


def _print_stats(titulo, stats, exemplos_raw):
    print("=" * 68)
    print(titulo)
    print("=" * 68)
    print(f"  Memorias estruturadas (heuristica/armadilha/protocolo/correcao): {stats['estruturadas']}")
    print(f"  Nao-estruturadas (puladas; meta=NULL): {stats['nao_estruturadas']}")
    print(f"  Ja tinham meta: {stats['ja_tem_meta']}")
    print(f"  Parse FULL (titulo+do -> normaliza content): {stats['full']}")
    print(f"  Parse PARTIAL (preserva content; meta best-effort): {stats['partial']}")
    print(f"  Parse RAW (preserva content; meta minimo): {stats['raw']}")
    print(f"  Content que seria normalizado p/ sentinela: {stats['content_normalizaria']}")
    print(f"  Erros de parse: {stats['erros']}")
    cobertura = stats["full"] + stats["partial"]
    if stats["estruturadas"]:
        pct = 100.0 * cobertura / stats["estruturadas"]
        print(f"  COBERTURA (full+partial): {cobertura}/{stats['estruturadas']} ({pct:.1f}%)")
    if exemplos_raw:
        print("  Exemplos RAW (revisar manualmente):")
        for p in exemplos_raw:
            print(f"    - {p}")


def _validate_prod():
    """READ-ONLY: roda o parser sobre os dados reais de PROD. Nunca escreve."""
    from sqlalchemy import create_engine, text
    url = os.environ.get("DATABASE_URL_PROD")
    if not url:
        raise RuntimeError("DATABASE_URL_PROD ausente no ambiente (.env).")
    engine = create_engine(url)
    with engine.connect() as conn:
        # NAO seleciona `meta` — em PROD a coluna so existe apos a migration DDL.
        # A validacao do parser precisa apenas de path + content.
        result = conn.execute(text(
            "SELECT id, path, content FROM agent_memories WHERE is_directory = false"
        ))
        rows = [(r[0], r[1], r[2], None) for r in result]
    stats, exemplos_raw, _ = _classificar(rows)
    _print_stats(f"VALIDACAO READ-ONLY contra PROD ({len(rows)} memorias)", stats, exemplos_raw)
    print("\n[OK] Nenhuma escrita realizada (validacao read-only).")


def _run_local(apply_changes, reprocess_all):
    from app import create_app, db
    from app.agente.models import AgentMemory

    app = create_app()
    with app.app_context():
        mems = AgentMemory.query.filter(AgentMemory.is_directory == False).all()
        rows = []
        for m in mems:
            if m.meta and not reprocess_all:
                # ja tem meta e nao e --all: conta como ja_tem_meta mas nao reprocessa
                rows.append((m.id, m.path, m.content, m.meta))
            else:
                rows.append((m.id, m.path, m.content, None if reprocess_all else m.meta))

        stats, exemplos_raw, plano = _classificar(rows)
        modo = "APPLY" if apply_changes else "DRY-RUN"
        _print_stats(f"BACKFILL meta LOCAL ({modo}) — {len(mems)} memorias", stats, exemplos_raw)

        if apply_changes:
            by_id = {m.id: m for m in mems}
            aplicadas = 0
            for idx, meta, novo_content in plano:
                mem = by_id.get(idx)
                if mem is None:
                    continue
                if mem.meta and not reprocess_all:
                    continue
                mem.meta = meta
                if novo_content is not None:
                    mem.content = novo_content
                aplicadas += 1
            db.session.commit()
            print(f"\n[OK] {aplicadas} memorias atualizadas (meta + content normalizado).")
        else:
            print("\n[DRY-RUN] Nenhuma alteracao gravada. Use --apply para efetivar.")


def main():
    ap = argparse.ArgumentParser(description="Backfill agent_memories.meta (formato canonico)")
    ap.add_argument("--apply", action="store_true", help="Efetiva no banco do ambiente (default: dry-run)")
    ap.add_argument("--all", action="store_true", help="Reprocessa tambem memorias que ja tem meta")
    ap.add_argument("--validate-prod", action="store_true", help="READ-ONLY: valida o parser contra PROD")
    args = ap.parse_args()

    if args.validate_prod:
        _validate_prod()
    else:
        _run_local(apply_changes=args.apply, reprocess_all=args.all)


if __name__ == "__main__":
    main()
