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
