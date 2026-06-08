"""Fast-path determinístico de vinculação NF×PO (Gabriella, Nicoly).

FASE 3 do plano docs/superpowers/plans/2026-06-08-fastpath-vinculacao-nf-po.md.
Espelha baseline_fastpath.py. SÓ o caminho feliz é interceptado; anomalia
(status!=aprovado, PO diverge, NF ambígua) e falha CAEM no LLM/gestor-recebimento
(R-EXEC-6). Conservador: na dúvida, retorna None/ok=False.

Camadas:
  N0  should_intercept_vinculacao  — regex puro (zero LLM)
  N1  parse_vinculacao_haiku       — fallback Haiku para variações de frase
      executar_vinculacao_fastpath — orquestra N0->N1->executor determinístico
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

# "vincular (o) pedido <PO> na nota <NF>"  (PO antes, NF depois)
_RE_VINCULAR = re.compile(
    r"\bvincul\w*\s+(?:o\s+)?pedido\s+(?P<po>[A-Za-z0-9./-]+)\s+n[ao]\s+(?:nota|nf)\s+(?P<nf>\d+)\b",
    re.IGNORECASE)
# "desfazer/desvincular (a vinculação) (NF) <NF> x <PO>"  (NF antes, PO depois)
_RE_DESVINCULAR = re.compile(
    r"\b(?:desvincul\w*|desfaz\w*|desfac\w*)\b.*?\b(?:nota|nf)\s+(?P<nf>\d+)\s*x\s*(?P<po>[A-Za-z0-9./-]+)",
    re.IGNORECASE | re.DOTALL)


def should_intercept_vinculacao(mensagem: str | None) -> dict | None:
    """Retorna {acao, nf, po} se a msg é uma (des)vinculação direta; senão None."""
    if not mensagem or not str(mensagem).strip():
        return None
    t = str(mensagem).strip()
    m = _RE_VINCULAR.search(t)
    if m:
        return {"acao": "vincular", "po": m.group("po"), "nf": m.group("nf")}
    m = _RE_DESVINCULAR.search(t)
    if m:
        return {"acao": "desvincular", "nf": m.group("nf"), "po": m.group("po")}
    return None


# ─────────────────────────── N1: parser Haiku (fallback) ───────────────────────
HAIKU_MODEL = "claude-haiku-4-5-20251001"
_KW_RECEBIMENTO = re.compile(r"\b(vincul\w*|desvincul\w*|nota|nf|pedido|po)\b", re.IGNORECASE)
_HAIKU_SYSTEM = (
    "Extraia de uma frase de operador de recebimento a ação de vincular/desvincular "
    "uma NOTA FISCAL a um PEDIDO de compra. Responda APENAS JSON: "
    '{"acao":"vincular"|"desvincular"|null,"nf":"<numero>"|null,"po":"<codigo>"|null}. '
    "Se a frase não for um pedido direto de (des)vinculação, retorne {\"acao\":null}.")


def _call_haiku(user_prompt: str) -> str:
    """Chama Haiku 4.5 e retorna texto. Testável via mock (padrão subagent_validator)."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=HAIKU_MODEL, max_tokens=120, system=_HAIKU_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}])
    return resp.content[0].text if resp.content else ""


def parse_vinculacao_haiku(mensagem: str | None) -> dict | None:
    """Fallback N1: Haiku estrutura (acao, nf, po). Só dispara se houver keyword
    de recebimento (não gasta token em msg fora de domínio)."""
    if not mensagem or not _KW_RECEBIMENTO.search(str(mensagem)):
        return None
    try:
        raw = _call_haiku(str(mensagem))
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        logger.info(f"[VINC-FASTPATH] Haiku parse falhou (-> LLM): {e}")
        return None
    if data.get("acao") in ("vincular", "desvincular") and data.get("nf") and data.get("po"):
        return {"acao": data["acao"], "nf": str(data["nf"]), "po": str(data["po"])}
    return None


# ───────────────────────────── orquestrador (N0->N1) ──────────────────────────
def _montar_resposta(r: dict) -> str:
    acao = "vinculados" if r["acao"] == "vincular" else "desvinculados"
    if r.get("status") == "finalizado_odoo":
        return f"NF {r['nf']} x PO {r['po']} já estavam vinculados no Odoo. Nada a fazer."
    cen = (r.get("resumo") or {}).get("cenario")
    extra = f" (cenário {cen})" if cen else ""
    return f"Feito. NF {r['nf']} x PO {r['po']} {acao}{extra}."


def executar_vinculacao_fastpath(mensagem: str, session_id=None, user_id=None) -> dict | None:
    """Orquestra N0->N1->executor determinístico. Retorna:
       - {"ok": True, "resposta": str}  -> caminho feliz (pula LLM)
       - {"ok": False, ...}             -> anomalia (caller cai no gestor-recebimento)
       - None                            -> não é vinculação (fluxo LLM normal)
    NUNCA levanta."""
    try:
        parsed = should_intercept_vinculacao(mensagem) or parse_vinculacao_haiku(mensagem)
        if not parsed:
            return None
        r = executar_vinculacao_por_nf(parsed["nf"], parsed["po"], parsed["acao"],
                                       usuario=f"agente:{user_id}")
        if r["ok"]:
            logger.info(f"[VINC-FASTPATH] OK ({parsed['acao']}) sem subagente "
                        f"user={user_id} nf={parsed['nf']}")
            return {"ok": True, "resposta": _montar_resposta({**r, **parsed})}
        logger.info(f"[VINC-FASTPATH] anomalia {r['anomalia']['tipo']} -> N2 "
                    f"(gestor-recebimento) nf={parsed['nf']}")
        return {"ok": False, "anomalia": r["anomalia"], "parsed": parsed}
    except Exception as e:
        logger.warning(f"[VINC-FASTPATH] falha geral (-> LLM) user={user_id}: {e}", exc_info=True)
        return None


# Import no escopo do MÓDULO para os testes mockarem via
# patch.object(fp, "executar_vinculacao_por_nf", ...) e para o orquestrador
# resolver o nome pelo namespace do módulo (patch pega).
from app.recebimento.services.vinculacao_rapida_service import (  # noqa: E402
    executar_vinculacao_por_nf,
)
