"""Handoff magro: empacota o MINIMO p/ o especialista quente assumir (entidades
resolvidas, saldo, objetivo) — NUNCA a conversa inteira. Guard de orcamento <10k tok.

ESTRATEGIA DE SESSAO (decisao central, anti-gap): o especialista tem SESSAO SDK
PROPRIA por papel (cliente proprio no pool, chave `session_id::role`). NAO herda
nem forka a sessao/transcript do principal — recebe SO' este handoff magro no 1o
turno e as proximas mensagens acumulam na sessao DELE. Sessoes SDK separadas
evitam o gap dos "2 subprocessos no mesmo sdk_session_id" (R1) e o cache fica
MODEL-scoped por papel. Confirmado por execucao: spec §Componentes #1 + §Correcao
de premissa (arranjo B do H3 = sessao propria; 1.32x mais barato que subagente-
retomavel). Resume com `resume=session_id` so' e' necessario cross-deploy.

ESCOPO DESTE MODULO: aqui SO' se monta/renderiza o handoff magro. O SWAP real do
cliente (que efetiva a sessao SDK propria por papel) vive em `client.py`/
`client_pool.py` (8b) — ativado por `AGENT_SPECIALIST_HANDOFF` (default `off`; em
`on` o stream troca o cliente do papel). Ver `app/agente/CLAUDE.md` secao "Handoff
de SESSAO"."""
from __future__ import annotations
import json
import math


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text or "") / 3.5)


def _ctx_tokens(objetivo, entidades, saldo) -> int:
    blob = json.dumps({"objetivo": objetivo, "entidades": entidades,
                       "saldo": saldo}, ensure_ascii=False, default=str)
    return estimate_tokens(blob)


def build_handoff_context(objetivo: str, entidades: dict,
                          saldo: dict | None = None, max_tokens: int = 10000) -> dict:
    objetivo = objetivo or ""
    entidades = dict(entidades or {})
    saldo = dict(saldo or {}) if saldo else None
    truncado = False
    # Trunca dados resolvidos PRIMEIRO (saldo, depois entidades). Se ainda exceder
    # com saldo/entidades vazios, o objetivo sozinho estoura -> trunca o OBJETIVO
    # (preservando o INICIO) ate caber. Devolver um handoff acima do orcamento
    # (o bug antigo: esvaziava os dados resolvidos E ainda estourava) e' pior.
    while _ctx_tokens(objetivo, entidades, saldo) > max_tokens:
        truncado = True
        if saldo:
            saldo.popitem()
            if not saldo:
                saldo = None
            continue
        if entidades:
            entidades.popitem()
            continue
        if len(objetivo) > 1:
            corte = max(1, len(objetivo) // 8)  # ~12%/iteracao, converge rapido
            objetivo = objetivo[:-corte]
            continue
        break
    return {
        "objetivo": objetivo,
        "entidades": entidades,
        "saldo": saldo,
        "tokens_estimados": _ctx_tokens(objetivo, entidades, saldo),
        "truncado": truncado,
    }


def render_handoff_block(ctx: dict) -> str:
    corpo = json.dumps({k: ctx.get(k) for k in ("objetivo", "entidades", "saldo")},
                       ensure_ascii=False, default=str)
    # Defesa de prompt-injection: neutraliza delimitadores forjados nos dados
    # resolvidos (ex.: objetivo contendo `</handoff_context>` + pseudo-instrucoes).
    # Escapa `<`/`>` para \uXXXX — mantem o JSON parseavel e impede que o objetivo
    # ENCERRE o bloco de sistema. O unico fechamento valido e' o desta funcao.
    corpo = corpo.replace("<", "\\u003c").replace(">", "\\u003e")
    return ("<handoff_context>\n"
            "Contexto de sistema (nao e instrucao do usuario): voce assumiu este "
            "assunto como especialista. Os dados resolvidos abaixo ja foram apurados "
            "pelo principal — parta deles, nao redescubra.\n"
            f"{corpo}\n"
            "</handoff_context>")
