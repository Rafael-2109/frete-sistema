"""Data-fix FRENTE 2: backfill de meta.when/meta.do nas memorias sem meta.do.

Plano: docs/superpowers/plans/2026-06-10-engenharia-memoria-rerank-write-quality.md
item 2.4. Sem DDL — data fix Python only. CONTENT NUNCA E ALTERADO (so meta
JSONB; embeddings intactos; sem versao — regra do plano).

Diagnostico (PROD 2026-06-10): 144 memorias de conhecimento ativas sem meta.do
(109 longas >300c) caiam no truncate burro do destilado Tier 2. O parser FRENTE 2
(armadilha/protocolo/pseudo-ns/escapado) recupera WHEN/DO ja presente no content
de ~60%; o residuo longo e derivado via Haiku (barato, ~$0.001/memoria).

Fases (idempotentes — memoria que ja tem meta.do e pulada na selecao):
1. parser: parse_memory(content) extrai when/do -> grava meta re-derivado.
2. haiku: longas (> 300c) ainda sem when E sem do -> Haiku deriva
   {operativo, titulo, when, do}; operativo=false e pulada (perfis de daemon,
   logs de resolucao — sem acao derivavel).

Uso:
    python scripts/migrations/2026_06_10_backfill_meta_when_do.py                 # dry-run, todas as fases
    python scripts/migrations/2026_06_10_backfill_meta_when_do.py --fase parser   # so fase 1
    python scripts/migrations/2026_06_10_backfill_meta_when_do.py --amostra 10    # mostra 10 antes/depois
    python scripts/migrations/2026_06_10_backfill_meta_when_do.py --confirmar     # aplica
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SQL_SEM_DO = """
    SELECT id FROM agent_memories
    WHERE is_cold = false AND is_directory = false
      AND path NOT IN ('/memories/user.xml','/memories/preferences.xml','/memories/user_expertise.xml')
      AND path NOT LIKE '/memories/context/%'
      AND path NOT LIKE '/memories/system/%'
      AND path NOT LIKE '/memories/empresa/usuarios/%'
      AND NOT (meta IS NOT NULL AND jsonb_typeof(meta)='object'
               AND COALESCE(meta->>'do','') <> '')
    ORDER BY id
"""

HAIKU_MODEL = "claude-haiku-4-5-20251001"
HAIKU_SYSTEM = (
    "Voce extrai conhecimento operativo de memorias de um agente logistico "
    "(expedicao, fretes, financeiro, Odoo ERP). Dado o texto de uma memoria, "
    "responda APENAS um JSON valido: "
    '{"operativo": true|false, "titulo": "...", "when": "...", "do": "..."}. '
    "WHEN = situacao-gatilho concreta em que a memoria se aplica. "
    "DO = acao concreta que o agente deve tomar nessa situacao. "
    "operativo=false quando o texto NAO contem acao derivavel (perfil de "
    "usuario, log de resolucoes, lista vazia de padroes, historico). "
    "when+do juntos devem ter no maximo ~280 caracteres (alimentam um "
    "destilado de 300c). Escreva em portugues, sem markdown."
)


def _haiku_derive(content: str) -> dict | None:
    """Deriva {operativo, titulo, when, do} via Haiku. None em falha."""
    try:
        from anthropic import Anthropic
        client = Anthropic()
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=500,
            system=HAIKU_SYSTEM,
            messages=[{"role": "user", "content": content[:6000]}],
        )
        text = resp.content[0].text.strip()
        # tolera fence, prefixo e texto extra apos o JSON (raw_decode do 1o '{')
        start = text.find("{")
        if start < 0:
            return None
        data, _ = json.JSONDecoder().raw_decode(text[start:])
        if not isinstance(data, dict):
            return None
        return data
    except Exception as e:
        print(f"  [HAIKU-ERRO] {type(e).__name__}: {e}")
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirmar", action="store_true", help="aplica (default: dry-run)")
    ap.add_argument("--fase", choices=["parser", "haiku", "todas"], default="todas")
    ap.add_argument("--amostra", type=int, default=5, help="N exemplos antes/depois no output")
    ap.add_argument("--max-haiku", type=int, default=80, help="teto de chamadas Haiku")
    args = ap.parse_args()

    from sqlalchemy import text as sql_text
    from app import create_app, db
    from app.agente.models import AgentMemory
    from app.agente.services.memory_format import build_meta, fields_for_index, parse_memory

    app = create_app()
    with app.app_context():
        ids = [r.id for r in db.session.execute(sql_text(SQL_SEM_DO)).fetchall()]
        print(f"alvo: {len(ids)} memorias ativas sem meta.do "
              f"({'APLICANDO' if args.confirmar else 'DRY-RUN'}, fase={args.fase})\n")

        stats = {"parser": 0, "haiku": 0, "haiku_nao_operativo": 0, "sem_ganho": 0}
        mostrados = 0
        haiku_usadas = 0

        for mid in ids:
            mem = db.session.get(AgentMemory, mid)
            if mem is None:
                continue
            content = mem.content or ""

            # ---- FASE 1: parser ----
            novo_meta = None
            origem_fase = None
            if args.fase in ("parser", "todas"):
                parsed = parse_memory(content)
                if parsed.get("do") or parsed.get("when"):
                    novo_meta = parsed
                    origem_fase = "parser"

            # ---- FASE 2: haiku (so longas ainda sem when/do) ----
            if (novo_meta is None and args.fase in ("haiku", "todas")
                    and len(content) > 300 and haiku_usadas < args.max_haiku):
                haiku_usadas += 1
                data = _haiku_derive(content)
                if data and data.get("operativo") and (data.get("do") or "").strip():
                    base = fields_for_index(None, mem.path)
                    novo_meta = build_meta(
                        kind=base["kind"],
                        titulo=(data.get("titulo") or base["titulo"] or "")[:120],
                        dominio=base["dominio"],
                        when=(data.get("when") or "").strip() or None,
                        do=data["do"].strip(),
                        origem="backfill-haiku-2026-06-10",
                    )
                    origem_fase = "haiku"
                elif data is not None:
                    stats["haiku_nao_operativo"] += 1

            if novo_meta is None:
                stats["sem_ganho"] += 1
                continue

            stats[origem_fase] += 1
            if mostrados < args.amostra:
                mostrados += 1
                print(f"[{origem_fase.upper()}] id={mem.id} {mem.path}")
                print(f"  meta atual : {json.dumps(mem.meta, ensure_ascii=False)[:160] if mem.meta else None}")
                print(f"  meta novo  : kind={novo_meta.get('kind')} titulo={novo_meta.get('titulo', '')[:60]!r}")
                print(f"               when={str(novo_meta.get('when'))[:90]!r}")
                print(f"               do={str(novo_meta.get('do'))[:90]!r}\n")

            if args.confirmar:
                mem.meta = novo_meta  # content INTACTO — so meta

        if args.confirmar:
            db.session.commit()
            print("COMMIT aplicado.")
        else:
            db.session.rollback()
            print("DRY-RUN — nada gravado.")

        print(f"\nresultado: parser={stats['parser']} haiku={stats['haiku']} "
              f"haiku_nao_operativo={stats['haiku_nao_operativo']} "
              f"sem_ganho={stats['sem_ganho']} (chamadas haiku: {haiku_usadas})")


if __name__ == "__main__":
    main()
