"""Fase 2 aprendizado ad-hoc -> skill: captura, cluster e sugestao.

Spec: docs/superpowers/specs/2026-06-12-aprendizado-adhoc-fase2-design.md
Plano: docs/superpowers/plans/2026-06-12-aprendizado-adhoc-fase2.md
Padrao espelhado da Fase 1 (skill_effectiveness_service.py).
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parser do transcript cru (claude_session_store)
# ---------------------------------------------------------------------------

def _entry_blocks(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    content = (entry.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def _entry_user_text(entry: Dict[str, Any]) -> Optional[str]:
    if entry.get("type") != "user":
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        joined = " ".join(t for t in texts if t).strip()
        return joined or None
    return None


def extract_adhoc_candidates(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Percorre o transcript cru e retorna candidatos Bash substantivos.

    Cada candidato: {command, skill_ativa, user_msg, teve_erro}.
    skill_ativa = ultimo tool_use Skill ANTES do Bash (superficie-agnostico —
    cobre Teams, diferente do tools_used do DB que so e enriquecido por canal).
    """
    out: List[Dict[str, Any]] = []
    last_skill: Optional[str] = None
    last_user_msg: Optional[str] = None
    error_ids: set = set()

    # 1o passe: tool_results com erro (chegam DEPOIS do tool_use correspondente)
    for e in entries:
        for b in _entry_blocks(e):
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                error_ids.add(b.get("tool_use_id"))

    for e in entries:
        utext = _entry_user_text(e)
        if utext:
            last_user_msg = utext
        for b in _entry_blocks(e):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name = b.get("name", "")
            tinput = b.get("input") or {}
            if name == "Skill" and isinstance(tinput, dict):
                last_skill = (tinput.get("skill") or "").strip() or last_skill
            elif name == "Bash" and isinstance(tinput, dict):
                cmd = tinput.get("command") or ""
                if is_substantive(cmd):
                    out.append({
                        "command": cmd,
                        "skill_ativa": last_skill,
                        "user_msg": last_user_msg,
                        "teve_erro": b.get("id") in error_ids,
                    })
    return out


# ---------------------------------------------------------------------------
# Filtro "Bash substantivo"
# ---------------------------------------------------------------------------

# Limiar de comprimento: comandos acima disso sao "substantivos" mesmo sem
# python/SQL explicito (heredocs, pipelines longos). Calibrado na Task 9 do
# plano com transcripts reais.
SUBSTANTIVE_MIN_CHARS = 200

_TRIVIAL_PREFIXES = (
    "ls", "cat ", "head ", "tail ", "grep ", "find ", "echo ", "pwd", "wc ",
    "git status", "git log", "git diff", "git show", "which ", "env", "date",
)
_SCRIPT_FILE_RE = re.compile(
    r"python3?\s+\S*(\.claude/skills/|scripts/|app/\S+/scripts/)\S*\.py")
_INLINE_CODE_RE = re.compile(
    r"python3?\s+-c\s|<<\s*['\"]?EOF|psql\b|"
    r"\b(SELECT|INSERT|UPDATE|DELETE)\b.*\b(FROM|INTO|SET)\b", re.IGNORECASE)


def is_substantive(command: str) -> bool:
    """Filtro deterministico (zero token) do que e 'script ad-hoc'.

    Inclui: python -c / heredoc / SQL inline, ou comando longo.
    Exclui: triviais e execucao de scripts PERSISTIDOS (skill ou repo) —
    esses ja tem dono; o alvo da Fase 2 e codigo improvisado inline.
    """
    cmd = (command or "").strip()
    if not cmd:
        return False
    # remove prefixo de env injetado pelo hook (bash_prefix_propagacao)
    cmd_clean = re.sub(r"^(export\s+\w+=\S+;\s*)+", "", cmd)
    low = cmd_clean.lower()
    if _SCRIPT_FILE_RE.search(cmd_clean):
        return False
    if any(low.startswith(p) for p in _TRIVIAL_PREFIXES):
        return False
    if _INLINE_CODE_RE.search(cmd_clean):
        return True
    return len(cmd_clean) >= SUBSTANTIVE_MIN_CHARS


# ---------------------------------------------------------------------------
# Extracao de metadados (Haiku, com fallback deterministico)
# ---------------------------------------------------------------------------

# Reuso da infra LLM da Fase 1 (mesmos modelos/parse).
from app.agente.services.skill_effectiveness_service import (  # noqa: E402
    HAIKU_MODEL, SONNET_MODEL, _call_anthropic, _parse_json,
)

_EXTRACT_SYSTEM = (
    "Voce extrai metadados de um script ad-hoc executado por um agente. "
    "Responda APENAS JSON: {\"problema\": \"<=100 chars, o problema de negocio "
    "que o script resolve>\", \"motivo_fallback\": \"<=150 chars, por que o "
    "agente usou script em vez da skill ativa — ou null se nao houver skill\"}."
)


def extract_problema(command: str, user_msg: Optional[str],
                     skill_ativa: Optional[str]) -> tuple:
    """(problema <=100c, motivo_fallback <=150c|None). Fallback = truncate da msg."""
    try:
        user = (f"Skill ativa: {skill_ativa or 'nenhuma'}\n"
                f"Pedido do usuario: {(user_msg or '')[:500]}\n"
                f"Comando: {command[:1500]}")
        raw = _call_anthropic(HAIKU_MODEL, _EXTRACT_SYSTEM, user, max_tokens=300)
        data = _parse_json(raw)
        prob = (data.get("problema") or "")[:100] or None
        motivo = data.get("motivo_fallback")
        motivo = str(motivo)[:150] if motivo and skill_ativa else None
        if prob:
            return prob, motivo
    except Exception as e:
        logger.warning(f"[ADHOC] extracao Haiku falhou (fallback): {e}")
    return ((user_msg or command or "")[:100] or None), None
