"""Revisao 4-maos (Rafael + Claude Code) das sugestoes de skill da Fase 2.

Fluxo aprovado em 2026-06-12: D8 -> sessao dev no Claude Code -> sistema.
As sugestoes F2 (suggestion_key `adhoc-cluster-*` / `skill-gap-*`) NAO sao
decididas pela tela web nem pelo D8 autonomo — a decisao e tomada em sessao
dev e gravada por este CLI via endpoint oficial do D8
(`POST /agente/api/improvement-dialogue`, auth X-Cron-Key), cujo
`upsert_response` cria a v2 (author=claude_code) E propaga o status a v1.

Uso:
    python scripts/agente/revisar_sugestoes_skill.py listar [--all]
    python scripts/agente/revisar_sugestoes_skill.py aprovar adhoc-cluster-4 --nota "..."
    python scripts/agente/revisar_sugestoes_skill.py rejeitar adhoc-cluster-6 --motivo "..."

Env: CRON_API_KEY (carregada do .env). --base-url para apontar fora de PROD.
"""
import argparse
import json
import os
import sys
from datetime import date

import requests
from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://sistema-fretes.onrender.com"
F2_PREFIXES = ("adhoc-", "skill-gap-")


def _headers() -> dict:
    key = os.environ.get("CRON_API_KEY", "")
    if not key:
        print("ERRO: CRON_API_KEY ausente no ambiente/.env", file=sys.stderr)
        sys.exit(2)
    return {"X-Cron-Key": key, "Content-Type": "application/json"}


def listar(base_url: str, mostrar_todas: bool) -> int:
    r = requests.get(f"{base_url}/agente/api/improvement-dialogue/pending",
                     headers=_headers(), params={"limit": 50}, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not mostrar_todas:
        items = [i for i in items
                 if str(i.get("suggestion_key", "")).startswith(F2_PREFIXES)]
    if not items:
        print("Nenhuma sugestao pendente" + ("" if mostrar_todas else " (F2)"))
        return 0
    for i in items:
        print("=" * 78)
        print(f"[{i['id']}] {i['suggestion_key']}  ({i['category']}/{i['severity']})")
        print(f"TITULO: {i['title']}")
        print(f"\nDESCRICAO:\n{i['description']}")
        ev = i.get("evidence_json") or {}
        if ev:
            print(f"\nEVIDENCIA: tipo_gap={ev.get('tipo_gap')} "
                  f"skill_relacionada={ev.get('skill_relacionada')} "
                  f"n_membros={ev.get('n_membros')}")
            for m in (ev.get("membros") or []):
                print(f"  - {m.get('problema')}  [sessao {str(m.get('session_id'))[:8]}]")
        print()
    print(f"{len(items)} pendente(s). Decida com: aprovar|rejeitar <suggestion_key>")
    return 0


def _post_decisao(base_url: str, key: str, status: str, descricao: str,
                  notas: str) -> int:
    payload = {
        "suggestion_key": key, "version": 2, "author": "claude_code",
        "status": status, "description": descricao,
        "implementation_notes": notas, "auto_implemented": False,
    }
    r = requests.post(f"{base_url}/agente/api/improvement-dialogue",
                      headers=_headers(), data=json.dumps(payload), timeout=30)
    if r.status_code != 200:
        print(f"ERRO {r.status_code}: {r.text}", file=sys.stderr)
        return 1
    print(f"OK: {key} -> {status} (v2 id={r.json().get('id')}; v1 propagada)")
    return 0


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("acao", choices=["listar", "aprovar", "rejeitar"])
    ap.add_argument("suggestion_key", nargs="?")
    ap.add_argument("--nota", default="", help="plano/observacao da aprovacao")
    ap.add_argument("--motivo", default="", help="motivo da rejeicao (calibracao)")
    ap.add_argument("--all", action="store_true", help="listar todas as categorias")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    a = ap.parse_args()

    if a.acao == "listar":
        return listar(a.base_url, a.all)
    if not a.suggestion_key:
        print("ERRO: informe a suggestion_key", file=sys.stderr)
        return 2
    hoje = date.today().isoformat()
    if a.acao == "aprovar":
        if not a.nota:
            print("ERRO: --nota obrigatoria na aprovacao (vira o plano)", file=sys.stderr)
            return 2
        return _post_decisao(
            a.base_url, a.suggestion_key, "responded",
            f"Aprovada por Rafael em sessao dev 4-maos ({hoje}). "
            f"Implementacao segue com o Claude Code.",
            a.nota)
    # rejeitar
    if not a.motivo:
        print("ERRO: --motivo obrigatorio na rejeicao (alimenta calibracao)", file=sys.stderr)
        return 2
    return _post_decisao(
        a.base_url, a.suggestion_key, "rejected",
        f"Rejeitada por Rafael em sessao dev 4-maos ({hoje}).",
        a.motivo)


if __name__ == "__main__":
    raise SystemExit(main())
