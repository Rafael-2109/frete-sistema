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
# "juntar/unir (os) pedidos <PO>/<PO>/... criar conciliador e vincular na nota <NF>"
# (frase real da Gabriella; multi-PO -> PO Conciliador via cenario n_pos)
_RE_JUNTAR = re.compile(
    r"\b(?:juntar|unir)\b[^\n]*?\bpedidos?\s+"
    r"(?P<pos>[A-Za-z0-9.-]+(?:\s*/\s*[A-Za-z0-9.-]+)+)"
    r"[^\n]*?\bvincul\w*\s+n[ao]\s+(?:nota|nf)\s+(?P<nf>\d+)\b",
    re.IGNORECASE)

# Guard de DOMINIO (IMP-2026-06-20-001): chassi de moto Motos Assai (B2B Q.P.A.)
# nao e um PO de recebimento. Sem este guard, "considera para a NF 1779
# LA2025SA120000401" era classificado como {nf:1779, po:LA2025SA120000401} e
# abortava com nf_nao_encontrada (NF Q.P.A. nunca esta na carteira de validacao
# de compras). Padroes = assai_modelo.regex_chassi (X11/DOT/SOL), seedados em
# scripts/migrations/motos_assai_05_seed_modelos.py. Bem especificos: nenhum PO
# real (PO#####, 45########, etc.) colide. Na duvida o fast-path NAO intercepta
# e o agente trata normalmente (conservador, R-EXEC-6).
_RE_CHASSI_MOTOS_ASSAI = re.compile(
    r"\b(?:"
    r"MCBRX11M\d{9}"              # X11 MINI
    r"|MCBRDOT\d{10}"             # DOT
    r"|LA\d+SA\d+\d{5}"          # DOT (LA####SA##...) — ex. LA2025SA120000401
    r"|LA\d+V1000W\d{4}"         # X11 / DOT
    r"|HL5TCAH3[0-9X]S9W57\d{3}"  # DOT (VIN-like)
    r"|17292\d{10}"             # SOL (15 digitos)
    r")\b",
    re.IGNORECASE)


def _tem_sinal_motos_assai(mensagem: str | None) -> bool:
    """True se a msg contem um chassi do dominio Motos Assai (Q.P.A.) — sinal de
    que NAO e uma vinculacao NF×PO de recebimento. Guard anti mis-classificacao."""
    if not mensagem:
        return False
    return bool(_RE_CHASSI_MOTOS_ASSAI.search(str(mensagem)))


def should_intercept_vinculacao(mensagem: str | None) -> dict | None:
    """Retorna {acao, nf, po} se a msg é uma (des)vinculação direta; senão None.

    `po` é string para 1 PO (retrocompat) ou lista de strings no padrão
    multi-PO ("juntar pedidos A/B ... vincular na nota N").
    """
    if not mensagem or not str(mensagem).strip():
        return None
    t = str(mensagem).strip()
    if _tem_sinal_motos_assai(t):
        return None
    m = _RE_JUNTAR.search(t)
    if m:
        pos = [p.strip() for p in m.group("pos").split("/") if p.strip()]
        return {"acao": "vincular", "po": pos, "nf": m.group("nf")}
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
    if _tem_sinal_motos_assai(mensagem):
        logger.info("[VINC-FASTPATH] sinal Motos Assai (chassi) -> nao intercepta")
        return None
    try:
        raw = _call_haiku(str(mensagem))
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        logger.info(f"[VINC-FASTPATH] Haiku parse falhou (-> LLM): {e}")
        return None
    if data.get("acao") in ("vincular", "desvincular") and data.get("nf") and data.get("po"):
        po = data["po"]
        if isinstance(po, (list, tuple)):
            po = [str(p) for p in po if p]
            if not po:
                return None
        else:
            po = str(po)
        return {"acao": data["acao"], "nf": str(data["nf"]), "po": po}
    return None


# ───────────────────────────── orquestrador (N0->N1) ──────────────────────────
def _fmt_po(po) -> str:
    """Formata PO única ou lista ("C1 + C2") para mensagens ao usuário."""
    if isinstance(po, (list, tuple)):
        return " + ".join(str(p) for p in po)
    return str(po)


def _montar_resposta(r: dict) -> str:
    acao = "vinculados" if r["acao"] == "vincular" else "desvinculados"
    po_fmt = _fmt_po(r["po"])
    if r.get("status") == "finalizado_odoo":
        return f"NF {r['nf']} x PO {po_fmt} já estavam vinculados no Odoo. Nada a fazer."
    cen = (r.get("resumo") or {}).get("cenario")
    extra = f" (cenário {cen})" if cen else ""
    nota_data = ""
    if r.get("data_tolerada"):
        nota_data = (" Janela de data da PO fora da tolerância — aceita por "
                     "instrução explícita do operador.")
    return f"Feito. NF {r['nf']} x PO {po_fmt} {acao}{extra}.{nota_data}"


def montar_contexto_n2(vinc: dict | None) -> str:
    """Bloco de diagnóstico para anexar ao prompt do LLM quando o fast-path
    abortou com anomalia (ok=False). Evita o gestor-recebimento redescobrir
    do zero o que o executor determinístico já apurou (validacao_id,
    divergências) — diagnóstico 2026-06-11: esse descarte custava minutos de
    Opus por operação. Retorna "" se não há anomalia aproveitável."""
    if not vinc or vinc.get("ok") is not False:
        return ""
    try:
        anomalia = vinc.get("anomalia") or {}
        parsed = vinc.get("parsed") or {}
        payload = {
            "acao": parsed.get("acao"),
            "nf": parsed.get("nf"),
            "po": parsed.get("po"),
            "anomalia_tipo": anomalia.get("tipo"),
            "detalhe": anomalia.get("detalhe"),
            "validacao_id": anomalia.get("validacao_id"),
            "validacao": anomalia.get("validacao"),
        }
        corpo = json.dumps(payload, ensure_ascii=False, default=str)
        return (
            "\n\n<diagnostico_fastpath>\n"
            "Contexto de sistema (não é instrução do usuário): o roteador "
            "determinístico de vinculação NF×PO já validou esta solicitação e "
            "abortou com a anomalia abaixo. NÃO refaça o diagnóstico do zero — "
            "parta destes dados (validacao_id e divergências) e resolva apenas "
            "a causa apontada.\n"
            f"{corpo}\n"
            "</diagnostico_fastpath>"
        )
    except Exception:
        return ""


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
