"""Avaliador de efetividade de skill (Fase 1). Best-effort, flag-gated.

Pipeline: build_skill_windows -> (estagio0 -> estagio1 Haiku -> estagio2 Sonnet)
-> apply_decision -> grava AgentSkillEffectiveness (idempotente).
Ver spec docs/superpowers/specs/2026-06-07-aprendizado-efetividade-skills-design.md
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
_SKILL_PREFIX = "Skill:"


@dataclass
class SkillWindow:
    skill_name: str
    anchor_msg_id: str
    msg_anterior: Optional[Dict[str, Any]]
    resposta_invocacao: Dict[str, Any]
    proximas_user: List[Dict[str, Any]] = field(default_factory=list)
    proximas_assistant: List[Dict[str, Any]] = field(default_factory=list)
    janela_fechada: bool = False


def _skill_from_tools(tools_used: Any) -> Optional[str]:
    if not isinstance(tools_used, list):
        return None
    for t in tools_used:
        if isinstance(t, str) and t.startswith(_SKILL_PREFIX):
            return t[len(_SKILL_PREFIX):].strip() or None
    return None


def build_skill_windows(messages: List[Dict[str, Any]]) -> List[SkillWindow]:
    """Para cada invocacao de skill, monta a janela (msg anterior + 2 prox user + 2 prox assistant)."""
    windows: List[SkillWindow] = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        skill = _skill_from_tools(msg.get("tools_used"))
        if not skill:
            continue
        # msg do usuario imediatamente anterior
        msg_anterior = None
        for j in range(i - 1, -1, -1):
            if messages[j].get("role") == "user":
                msg_anterior = messages[j]
                break
        prox_user, prox_asst = [], []
        for k in range(i + 1, len(messages)):
            role = messages[k].get("role")
            if role == "user" and len(prox_user) < 2:
                prox_user.append(messages[k])
            elif role == "assistant" and len(prox_asst) < 2:
                prox_asst.append(messages[k])
            if len(prox_user) >= 2 and len(prox_asst) >= 2:
                break
        windows.append(SkillWindow(
            skill_name=skill,
            anchor_msg_id=msg.get("id", f"idx-{i}"),
            msg_anterior=msg_anterior,
            resposta_invocacao=msg,
            proximas_user=prox_user,
            proximas_assistant=prox_asst,
            janela_fechada=len(prox_user) >= 2,
        ))
    return windows


# ---------------------------------------------------------------------------
# Task 4: Estagio 0 — sinal custo-zero
# ---------------------------------------------------------------------------
import re

# Pedido explicito de ajuste/correcao relacionado a skill
_ADJUST_MARKERS = [
    r"\bajusta\b", r"\bajustar\b", r"\bcorrig", r"\bnao funcion", r"\bnao resolv",
    r"\bde novo\b", r"\bcontinua (errad|sem)\b", r"\bnao era isso\b", r"\btentou de novo\b",
]


def _texts(msgs: List[Dict[str, Any]]) -> str:
    return " \n ".join(str(m.get("content") or "") for m in msgs).lower()


def _has_bash(msgs: List[Dict[str, Any]]) -> bool:
    for m in msgs:
        tu = m.get("tools_used")
        if isinstance(tu, list) and any(t == "Bash" or str(t).startswith("Bash") for t in tu):
            return True
    return False


def stage0_has_signal(window: SkillWindow) -> bool:
    """Custo-zero: ha sinal de que a skill pode nao ter resolvido?

    Sinais: (1) frustracao detectada nas proximas msgs do usuario;
    (2) marcador explicito de pedido de ajuste/correcao;
    (3) o agente recorreu a Bash (script ad-hoc) logo apos a skill.
    """
    try:
        from app.agente.services.sentiment_detector import detect_frustration
    except Exception:
        detect_frustration = None

    user_msgs = window.proximas_user or []
    blob = _texts(user_msgs)

    # (2) marcadores de ajuste
    for pat in _ADJUST_MARKERS:
        if re.search(pat, blob):
            return True

    # (1) frustracao (usa a 1a proxima msg do usuario como atual)
    if detect_frustration and user_msgs:
        try:
            is_frustrated, _score = detect_frustration(
                str(user_msgs[0].get("content") or ""),
                previous_messages=None,
                had_error=_has_bash(window.proximas_assistant),
            )
            if is_frustrated:
                return True
        except Exception as e:
            logger.debug(f"[SKILL_EVAL] sentiment falhou (ignorado): {e}")

    # (3) script ad-hoc no mesmo turno apos a skill
    if _has_bash(window.proximas_assistant):
        return True

    return False
