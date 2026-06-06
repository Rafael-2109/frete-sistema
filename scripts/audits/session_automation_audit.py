#!/usr/bin/env python3
"""
session_automation_audit.py — diagnóstico DETERMINÍSTICO de automação de sessões.

Pergunta que responde: quanto do custo do Agente Web vem de tarefas ROTINEIRAS +
ESTRUTURADAS (template estável) que poderiam ser resolvidas por fast-path (Tier 0
regex/serviço) ou modelo mais barato (Haiku/Sonnet), em vez do loop Opus?

Origem: avaliação 2026-06-06 (caso Gabriella id 69 — "vincular pedido C-XXX na nota
YYY no odoo e no frete", quase diário, sempre o mesmo procedimento). Este script
generaliza o caso: classifica a 1ª mensagem do usuário de cada sessão por TEMPLATE
(regex), agrega custo por categoria e estima a economia por tier-alvo.

Sem LLM. Determinístico. Read-only (apenas SELECT).

Uso:
  python scripts/audits/session_automation_audit.py                 # 45d, env DATABASE_URL_PROD
  python scripts/audits/session_automation_audit.py --dias 30
  python scripts/audits/session_automation_audit.py --json
  DATABASE_URL=... python scripts/audits/session_automation_audit.py --database-url ...

Tiers (custo in/out por Mtok): tier0 sem LLM ($0) < haiku ($0.25/$1.25) <
sonnet ($3/$15) < opus ($5/$25). A economia é ESTIMATIVA (fator por tier); a
atribuição usa a 1ª mensagem como assunto dominante da sessão (aproximação).
"""
import argparse
import os
import re
import sys

# ─────────────────────────────────────────────────────────── classificação

# Follow-ups curtos (last_message frequente: "pronto?", "ok") — NÃO são rotina.
_FOLLOWUP_RE = re.compile(
    r"^(pronto|ok|okay|obrigad\w*|valeu|sim|n[ãa]o|blz|beleza|\?+|"
    r"pode me ajudar\??|me ajuda\??|tudo bem\??|oi|ol[áa]|certo|isso)\s*\??$"
)

# Templates ordenados — primeiro match vence. (categoria, regex, automatizavel, tier_alvo)
_TEMPLATES = [
    ("vinculacao_nf_po",
     re.compile(r"vincul\w*.*\bpedido\b.*\bnota\b|vincul\w*.*\bnota\b.*\bpedido\b"),
     True, "sonnet"),
    ("recalculo_frete_carvia",
     re.compile(r"recalcul\w*.*frete|frete.*(m[íi]n|min)\.?\s*peso|"
                r"atualizar.*embarque.*carvia|embarque.*carvia.*frete"),
     True, "sonnet"),
    ("faturamento",
     re.compile(r"\bfaturar\b|\bfaturamento\b|\bfaturad[ao]s?\s+(o|a|esse|essa)"),
     True, "sonnet"),
    ("monitoramento_entrega",
     re.compile(
         r"foi entregue|\bentregue\b|que dia.*(embarc|fatur)|\bembarcou\b|"
         r"cad[êe]\w*\s+(o |a |os |as |meu |minha |esse |essa )?(pedido|entrega|nf|nota|carga|merc)|"
         r"\bstatus\b|\brastre|\bcanhoto\b|onde\s+est\w+.*(pedido|nf|nota|entrega|carga)|"
         r"quando\s+(foi\s+)?(entreg|fatur|embarc)|j[áa]\s+(foi\s+)?(entreg|fatur)"),
     True, "tier0"),
    ("cotacao",
     re.compile(
         r"cota[çc][ãa]o|quanto\s+(custa|sai|fica|vai|é|e)\b.*frete|"
         r"\bfrete\s+(para|pra|de\s)|valor\s+do\s+frete|pre[çc]o\s+do\s+frete|\bfrete\s+pra\b"),
     True, "tier0"),
    ("cancelamento",
     re.compile(r"\bcancel"),
     True, "sonnet"),
    ("lancamento_pedido",
     re.compile(r"(lan[çc]\w*|criar|incluir|cadastr\w*|inserir)\s+(o\s+|um\s+|novo\s+|esse\s+)?pedido"),
     True, "sonnet"),
    ("consulta_estoque",
     re.compile(r"quanto\s+(tem|temos|de)\b|estoque\s+d|tem\s+em\s+estoque|\bsaldo\b|disponibilidade"),
     True, "tier0"),
    ("consulta_movimentacao",
     re.compile(r"movimenta[çc][ãa]o\b|movimenta[çc][õo]es\b|validade\s+(do\s+|de\s+)?lote|hist[óo]rico.*lote"),
     True, "tier0"),
    ("baseline",
     re.compile(r"\bbaseline\b"),
     True, "tier0"),
    ("financeiro",
     re.compile(r"concilia|reconcilia|baixa\s+de\s+t[íi]tulo|lan[çc]\w*\s+pagamento|"
                r"extrato\s+banc|\bcnab\b|\bofx\b|\bboleto\b"),
     False, "sonnet"),
]

# Fator de economia por tier-alvo (fração do custo Opus evitada). Conservador.
FATOR_ECONOMIA = {"tier0": 0.90, "haiku": 0.88, "sonnet": 0.70, "opus": 0.0}


def classificar(texto):
    """Classifica a mensagem em (categoria, automatizavel, tier_alvo). Determinístico."""
    if not texto or not str(texto).strip():
        return {"categoria": "indeterminado", "automatizavel": False, "tier_alvo": "opus"}
    t = str(texto).strip().lower()
    if _FOLLOWUP_RE.match(t):
        cat = "conversa" if "ajud" in t else "indeterminado"
        return {"categoria": cat, "automatizavel": False, "tier_alvo": "opus"}
    for categoria, rgx, autom, tier in _TEMPLATES:
        if rgx.search(t):
            return {"categoria": categoria, "automatizavel": autom, "tier_alvo": tier}
    return {"categoria": "conversa_analise", "automatizavel": False, "tier_alvo": "opus"}


def agregar(linhas):
    """linhas: list[{texto, custo}]. Retorna ranking por custo desc com economia estimada."""
    agg = {}
    for ln in linhas:
        r = classificar(ln.get("texto"))
        cat = r["categoria"]
        a = agg.get(cat)
        if a is None:
            a = agg[cat] = {"categoria": cat, "sessoes": 0, "custo": 0.0,
                            "automatizavel": r["automatizavel"], "tier_alvo": r["tier_alvo"],
                            "economia_estimada": 0.0}
        a["sessoes"] += 1
        custo = float(ln.get("custo") or 0)
        a["custo"] += custo
        if r["automatizavel"]:
            a["economia_estimada"] += min(custo * FATOR_ECONOMIA.get(r["tier_alvo"], 0.0), custo)
    rank = sorted(agg.values(), key=lambda x: x["custo"], reverse=True)
    for r in rank:
        r["custo"] = round(r["custo"], 2)
        r["economia_estimada"] = round(r["economia_estimada"], 2)
    return rank


# ─────────────────────────────────────────────────────────── I/O (read-only)

_SQL = """
SELECT
  s.user_id,
  COALESCE(s.total_cost_usd, 0) AS custo,
  COALESCE(
    (SELECT m->>'content'
       FROM jsonb_array_elements(
              CASE WHEN jsonb_typeof(s.data->'messages')='array' THEN s.data->'messages' ELSE '[]'::jsonb END) m
       WHERE m->>'role'='user' AND jsonb_typeof(m->'content')='string'
       LIMIT 1),
    (SELECT b->>'text'
       FROM jsonb_array_elements(
              CASE WHEN jsonb_typeof(s.data->'messages')='array' THEN s.data->'messages' ELSE '[]'::jsonb END) m,
            jsonb_array_elements(CASE WHEN jsonb_typeof(m->'content')='array' THEN m->'content' ELSE '[]'::jsonb END) b
       WHERE m->>'role'='user' AND b->>'type'='text'
       LIMIT 1),
    s.last_message
  ) AS texto,
  (SELECT 1 WHERE jsonb_typeof(s.data->'messages')='array') AS tem_messages
FROM agent_sessions s
WHERE s.created_at >= NOW() - (%s || ' days')::interval
  AND s.total_cost_usd IS NOT NULL;
"""


def puxar(database_url, dias):
    import psycopg2
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(_SQL, (str(dias),))
            cols = [c[0] for c in (cur.description or [])]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="Diagnóstico determinístico de automação de sessões")
    ap.add_argument("--dias", type=int, default=45)
    ap.add_argument("--database-url", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    db = args.database_url or os.getenv("DATABASE_URL_PROD") or os.getenv("DATABASE_URL")
    if not db:
        print("ERRO: defina --database-url ou DATABASE_URL_PROD/DATABASE_URL no env.", file=sys.stderr)
        return 2

    linhas = puxar(db, args.dias)
    rank = agregar(linhas)

    custo_total = round(sum(r["custo"] for r in rank), 2)
    economia_total = round(sum(r["economia_estimada"] for r in rank), 2)
    custo_autom = round(sum(r["custo"] for r in rank if r["automatizavel"]), 2)
    fallback = sum(1 for ln in linhas if not ln.get("tem_messages"))

    if args.json:
        import json
        print(json.dumps({
            "dias": args.dias, "sessoes": len(linhas), "custo_total": custo_total,
            "custo_automatizavel": custo_autom, "economia_estimada": economia_total,
            "cobertura_via_last_message": fallback, "ranking": rank,
        }, ensure_ascii=False, indent=2))
        return 0

    print("=" * 78)
    print(f"AUTOMAÇÃO DE SESSÕES — últimos {args.dias} dias ({len(linhas)} sessões)")
    print("=" * 78)
    print(f"{'Categoria':<24}{'Sess':>6}{'Custo $':>10}{'%':>6}  {'Tier-alvo':<9}{'Economia~$':>11}")
    print("-" * 78)
    for r in rank:
        pct = (100 * r["custo"] / custo_total) if custo_total else 0
        flag = "" if r["automatizavel"] else "  (manual)"
        print(f"{r['categoria']:<24}{r['sessoes']:>6}{r['custo']:>10.2f}{pct:>5.0f}%  "
              f"{r['tier_alvo']:<9}{r['economia_estimada']:>11.2f}{flag}")
    print("-" * 78)
    print(f"{'TOTAL':<24}{len(linhas):>6}{custo_total:>10.2f}{'100%':>6}  "
          f"{'':<9}{economia_total:>11.2f}")
    print(f"\nCusto automatizável (categorias estruturadas): ${custo_autom:.2f} "
          f"({100*custo_autom/custo_total if custo_total else 0:.0f}% do total)")
    print(f"Economia estimada (fast-path/downgrade, fatores conservadores): ${economia_total:.2f} "
          f"(~{100*economia_total/custo_total if custo_total else 0:.0f}% do total)")
    print(f"Cobertura: {len(linhas)-fallback}/{len(linhas)} via 1ª msg do data; {fallback} via last_message.")
    print("\nNota: economia é ESTIMATIVA (fator por tier); custo atribuído à 1ª mensagem")
    print("(assunto dominante). Sessões multi-assunto podem misturar categorias.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
