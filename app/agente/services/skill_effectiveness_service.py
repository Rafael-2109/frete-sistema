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


# ---------------------------------------------------------------------------
# Task 5: Estagios 1 e 2 — Haiku e Sonnet
# ---------------------------------------------------------------------------
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
_VALID_RAMOS = ("lembrete_usuario", "lembrete_todos", "ajuste_codigo", "nada")

_STAGE1_SYSTEM = (
    "Voce avalia se uma SKILL resolveu o pedido do usuario, olhando a janela de "
    "conversa logo apos a invocacao. Responda SO JSON: "
    '{"resolveu": bool, "suspeita_ajuste": bool, "motivo": "curto", "sinais": ["..."]}. '
    "suspeita_ajuste=true se o usuario pediu correcao/ajuste, reclamou, repetiu o pedido, "
    "ou o agente recorreu a script ad-hoc para o mesmo assunto. Seja conservador."
)

_STAGE2_SYSTEM = (
    "Voce e um avaliador de solucoes, chamado pela suspeita de necessidade de ajuste numa "
    "skill. Decida o RAMO da solucao. SEPARACAO DE COMPETENCIAS (inviolavel): para "
    "'ajuste_codigo' voce DESCREVE o problema e a evidencia e PEDE ajuda — NUNCA prescreve "
    "a solucao de codigo (isso e trabalho do Claude Code). Responda SO JSON: "
    '{"ramo": "lembrete_usuario|lembrete_todos|ajuste_codigo|nada", "titulo": "...", '
    '"conteudo_lembrete": "texto do lembrete (so ramos lembrete_*)", '
    '"problema": "descricao do problema (so ajuste_codigo)", '
    '"evidencia": "trechos que sustentam (so ajuste_codigo)", '
    '"categoria_codigo": "skill_bug|skill_suggestion|instruction_request|prompt_feedback", '
    '"justificativa": "...", "confianca": 0.0}. '
    "lembrete_usuario = orientacao especifica para ESTE usuario ao usar a skill. "
    "lembrete_todos = vale para todos (empresa). ajuste_codigo = a skill/codigo precisa mudar."
)


def _call_anthropic(model: str, system: str, user: str, max_tokens: int = 600) -> str:
    """Chamada sincrona ao Claude (mesmo padrao de step_judge._call_haiku_judge)."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _format_window(window: SkillWindow, skill_description: str = "") -> str:
    # PII masking antes de enviar ao LLM (CNPJ/CPF/email) — spec edge-case.
    from app.agente.utils.pii_masker import mask_pii
    def _fmt(m): return f"[{m.get('role')}] {mask_pii(str(m.get('content') or ''))[:1500]}"
    parts = [f"SKILL: {window.skill_name}"]
    if skill_description:
        parts.append(f"DESCRICAO DA SKILL: {skill_description[:500]}")
    if window.msg_anterior:
        parts.append("PERGUNTA ANTERIOR:\n" + _fmt(window.msg_anterior))
    parts.append("RESPOSTA QUE INVOCOU A SKILL:\n" + _fmt(window.resposta_invocacao))
    if window.proximas_user:
        parts.append("PROXIMAS MSGS DO USUARIO:\n" + "\n".join(_fmt(m) for m in window.proximas_user))
    if window.proximas_assistant:
        parts.append("PROXIMAS RESPOSTAS DO AGENTE:\n" + "\n".join(_fmt(m) for m in window.proximas_assistant))
    return "\n\n".join(parts)


def _parse_json(raw: str) -> Dict[str, Any]:
    try:
        from app.agente.services._utils import parse_llm_json_response
        data = parse_llm_json_response(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def stage1_haiku(window: SkillWindow) -> Dict[str, Any]:
    raw = _call_anthropic(HAIKU_MODEL, _STAGE1_SYSTEM, _format_window(window), max_tokens=300)
    data = _parse_json(raw)
    return {
        "resolveu": bool(data.get("resolveu", True)),
        "suspeita_ajuste": bool(data.get("suspeita_ajuste", False)),
        "motivo": str(data.get("motivo", "")),
        "sinais": data.get("sinais", []) if isinstance(data.get("sinais"), list) else [],
    }


def stage2_sonnet(window: SkillWindow, skill_description: str = "") -> Dict[str, Any]:
    raw = _call_anthropic(SONNET_MODEL, _STAGE2_SYSTEM,
                          _format_window(window, skill_description), max_tokens=800)
    data = _parse_json(raw)
    ramo = data.get("ramo", "nada")
    if ramo not in _VALID_RAMOS:
        ramo = "nada"
    try:
        conf = float(data.get("confianca", 0.0) or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    return {
        "ramo": ramo,
        "titulo": str(data.get("titulo", ""))[:200],
        "conteudo_lembrete": str(data.get("conteudo_lembrete", "")),
        "problema": str(data.get("problema", "")),
        "evidencia": str(data.get("evidencia", "")),
        "categoria_codigo": str(data.get("categoria_codigo", "skill_bug")),
        "justificativa": str(data.get("justificativa", "")),
        "confianca": conf,
    }


# ---------------------------------------------------------------------------
# Task 6: Aplicacao dos ramos
# ---------------------------------------------------------------------------
def _xml_escape(s: Optional[str]) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_reminder_xml(skill: str, decision: Dict[str, Any]) -> str:
    titulo = _xml_escape(decision.get("titulo", ""))
    corpo = _xml_escape(decision.get("conteudo_lembrete", "") or decision.get("titulo", ""))
    return (f'<skill_reminder skill="{_xml_escape(skill)}">\n'
            f'  <titulo>{titulo}</titulo>\n'
            f'  <orientacao>{corpo}</orientacao>\n'
            f'</skill_reminder>')


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-') or 'skill'


def _invalidate_caches(user_id: int) -> None:
    try:
        from app.agente.sdk.memory_injection import invalidate_injection_cache_for_user
        invalidate_injection_cache_for_user(user_id)
    except Exception as e:
        logger.debug(f"[SKILL_EVAL] invalidate_injection_cache_for_user falhou: {e}")
    try:
        from app.agente.sdk.memory_injection import invalidate_skill_reminders_cache
        invalidate_skill_reminders_cache()
    except Exception as e:
        # invalidate_skill_reminders_cache criada na Task 10/G4 — tolerante a ImportError
        logger.debug(f"[SKILL_EVAL] invalidate_skill_reminders_cache nao disponivel ainda: {e}")


def _apply_lembrete_usuario(decision, window, user_id, shadow=False) -> str:
    from app import db
    from app.agente.models import AgentMemory
    path = f"/memories/lembretes_skill/{window.skill_name}.xml"
    content = _render_reminder_xml(window.skill_name, decision)
    mem = AgentMemory.query.filter_by(user_id=user_id, path=path).first()
    if mem:
        mem.content = content
    else:
        mem = AgentMemory.create_file(user_id, path, content)
    mem.priority = "mandatory"
    mem.category = "permanent"
    mem.importance_score = 0.9
    mem.directive_status = "shadow" if shadow else None
    db.session.commit()
    _invalidate_caches(user_id)
    return f"memory:{mem.id}"


def _apply_lembrete_todos(decision, window) -> str:
    from app import db
    from app.agente.models import AgentMemory
    path = f"/memories/empresa/lembretes_skill/{_slug(window.skill_name)}.xml"
    existing = AgentMemory.query.filter_by(user_id=0, path=path).first()
    if existing:
        return f"approval:{existing.id}"
    mem = AgentMemory(
        user_id=0, path=path, content=_render_reminder_xml(window.skill_name, decision),
        is_directory=False, importance_score=0.7,
        escopo="empresa", directive_status="shadow", priority="mandatory",
        created_by=None,
    )
    db.session.add(mem)
    db.session.commit()
    return f"approval:{mem.id}"


def _apply_ajuste_codigo(decision, window, session_id) -> str:
    from app import db
    from app.agente.models import AgentImprovementDialogue
    # Separacao de competencias: so descreve problema+evidencia, NAO prescreve solucao.
    # affected_files e implementation_notes ficam None (avaliador nao prescreve).
    sug = AgentImprovementDialogue.create_suggestion(
        category=decision.get("categoria_codigo", "skill_bug"),
        severity="info",
        title=(decision.get("titulo") or f"skill {window.skill_name}")[:200],
        description=decision.get("problema", ""),          # SO problema (sem solucao)
        evidence={"skill": window.skill_name,
                  "evidencia": decision.get("evidencia", ""),
                  "justificativa": decision.get("justificativa", "")},
        session_ids=[session_id],
    )
    db.session.commit()
    return f"dialogue:{sug.id}"


def apply_decision(decision: Dict[str, Any], window: SkillWindow,
                   user_id: int, session_id: str) -> str:
    """Aplica o ramo decidido. Retorna action_ref ('' se nada)."""
    from app.agente.config import feature_flags as ff
    ramo = decision.get("ramo", "nada")
    conf = decision.get("confianca", 0.0) or 0.0

    # lembrete_usuario de baixa confianca -> rebaixa p/ inbox (ajuste_codigo)
    if ramo == "lembrete_usuario" and conf < ff.AGENT_SKILL_EVAL_CONF_MIN:
        ramo = "ajuste_codigo"

    if ramo == "lembrete_usuario":
        apply_user = getattr(ff, "AGENT_SKILL_EVAL_APPLY_USER", True)
        return _apply_lembrete_usuario(decision, window, user_id, shadow=not apply_user)
    if ramo == "lembrete_todos":
        return _apply_lembrete_todos(decision, window)
    if ramo == "ajuste_codigo":
        return _apply_ajuste_codigo(decision, window, session_id)
    return ""


# ---------------------------------------------------------------------------
# Task 7: evaluate_session — orquestracao + idempotencia
# ---------------------------------------------------------------------------
def _window_evidence(w: SkillWindow) -> Dict[str, Any]:
    # PII masking antes de persistir (evidencia_json e exibida na inbox admin) — spec edge-case.
    from app.agente.utils.pii_masker import mask_pii
    def _c(m): return {"role": m.get("role"), "content": mask_pii(str(m.get("content") or ""))[:500]}
    return {
        "skill": w.skill_name,
        "anterior": _c(w.msg_anterior) if w.msg_anterior else None,
        "proximas_user": [_c(m) for m in w.proximas_user],
    }


def _safe_persist(row, result) -> None:
    from app import db
    from sqlalchemy.exc import IntegrityError
    try:
        db.session.add(row)
        db.session.commit()
        result["avaliadas"] += 1
        if row.ramo:
            result["ramos"][row.ramo] = result["ramos"].get(row.ramo, 0) + 1
    except IntegrityError:
        db.session.rollback()  # corrida: ancora ja gravada por outra execucao


def _evaluate_inner(session_id: str, user_id: int) -> Dict[str, Any]:
    from app.agente.models import AgentSession, AgentSkillEffectiveness
    from app.agente.config import feature_flags as ff
    from app.utils.json_helpers import sanitize_for_json
    result = {"avaliadas": 0, "ramos": {}}

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if not sess:
        return result
    windows = build_skill_windows(sess.get_messages() or [])
    sonnet_budget = getattr(ff, "AGENT_SKILL_EVAL_MAX_SONNET", 3)

    for w in windows:
        if not w.janela_fechada:
            continue
        if AgentSkillEffectiveness.query.filter_by(
                session_id=session_id, anchor_msg_id=w.anchor_msg_id).first():
            continue
        row = AgentSkillEffectiveness(
            user_id=user_id, session_id=session_id, skill_name=w.skill_name,
            anchor_msg_id=w.anchor_msg_id, stage_reached=0, resolveu=True,
            evidencia_json=sanitize_for_json(_window_evidence(w)),
        )
        if not stage0_has_signal(w):
            _safe_persist(row, result)
            continue
        s1 = stage1_haiku(w)
        row.stage_reached = 1
        row.resolveu = bool(s1.get("resolveu", True))
        if not s1.get("suspeita_ajuste"):
            _safe_persist(row, result)
            continue
        if not getattr(ff, "AGENT_SKILL_EVAL_SONNET", True) or sonnet_budget <= 0:
            _safe_persist(row, result)
            continue
        sonnet_budget -= 1
        s2 = stage2_sonnet(w)
        row.stage_reached = 2
        row.ramo = s2.get("ramo", "nada")
        row.confidence = s2.get("confianca", 0.0)
        row.resolveu = (s2.get("ramo") == "nada")
        try:
            row.action_ref = apply_decision(s2, w, user_id, session_id) or None
        except Exception as e:
            logger.warning(f"[SKILL_EVAL] apply falhou: {e}")
        _safe_persist(row, result)
    return result


def evaluate_session(session_id: str, user_id: int, app=None) -> Dict[str, Any]:
    """Entry point. Best-effort. `app` fornecido => abre app_context (job RQ)."""
    try:
        if app is not None:
            with app.app_context():
                return _evaluate_inner(session_id, user_id)
        return _evaluate_inner(session_id, user_id)
    except Exception as e:
        logger.warning(f"[SKILL_EVAL] evaluate_session falhou (ignorado): {e}")
        return {"avaliadas": 0, "ramos": {}}
