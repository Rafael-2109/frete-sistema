"""
L1 Rules Channel — Builder de <user_rules priority="mandatory">.

Separa memorias com priority='mandatory' do usuario em bloco XML distinto,
renderizado como extensao do system prompt (vs contexto passivo).

Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md Task 3
"""
import logging
from typing import Optional
from ._sanitization import xml_escape, sanitize_memory_content

logger = logging.getLogger('sistema_fretes')


def _query_user_rules(user_id: int, agente: str = 'web'):
    """
    Query CANONICA das regras do canal L1 (priority='mandatory').

    M3 (F2 fatia 2): `agente` isola as regras por agente (web|lojas) — inclui
    as regras EMPRESA (user_id=0) do agente. Default 'web' = aditivo.

    Fonte unica compartilhada por _build_user_rules (renderiza o bloco XML) e
    _get_user_rule_ids (dedup do Tier 2) — manter UMA query garante que o
    conjunto excluido do RAG e exatamente o conjunto injetado como regra.

    Ordena por correction_count DESC (regras mais reincidentes primeiro) +
    cap MANDATORY_RULES_MAX_COUNT: adesao a instrucoes despenca >100-150
    regras (IFScale arXiv:2507.11538) — manter o canal duro pequeno e curado.

    F6 PAD-CTX (2026-06-10): exclui TIER1_PROTECTED_PATHS do PROPRIO usuario —
    bug de dupla injecao em PROD (user 18: preferences.xml com priority=
    mandatory entrava 2x no payload, no <user_rules> E no Tier 1). Paths
    protegidos do usuario vivem SO no Tier 1 (canal canonico de perfil, com
    cap proprio). Rows EMPRESA (user_id=0) com esses paths FICAM no canal L1:
    o Tier 1 e user-scoped e nao as injeta — exclui-las as faria sumir dos
    dois canais (edge do review F6). Exclusao INCONDICIONAL a flag
    AGENT_FIXED_BLOCKS_CAP: e bug fix, a dupla injecao nao volta no rollback.
    """
    from sqlalchemy import and_, not_
    from ..models import AgentMemory
    from ..config.feature_flags import MANDATORY_RULES_MAX_COUNT
    from .memory_injection import TIER1_PROTECTED_PATHS
    return AgentMemory.query.filter(
        AgentMemory.user_id.in_([user_id, 0]),
        AgentMemory.agente == agente,  # M3/R01: regras (pessoais + empresa) por agente
        AgentMemory.is_directory == False,  # noqa: E712
        AgentMemory.is_cold == False,  # noqa: E712
        AgentMemory.priority == 'mandatory',
        not_(and_(
            AgentMemory.path.in_(TIER1_PROTECTED_PATHS),
            AgentMemory.user_id == user_id,
        )),
    ).order_by(
        AgentMemory.correction_count.desc(),
        AgentMemory.user_id.asc(),
        AgentMemory.path.asc(),
    ).limit(MANDATORY_RULES_MAX_COUNT).all()


def _get_user_rule_ids(user_id: int, agente: str = 'web') -> set:
    """
    IDs das memorias que entram no canal L1 <user_rules>.

    F1.1 PAD-CTX (bug N-1 do estudo 2026-06-09): essas memorias eram re-injetadas
    no Tier 2 RAG quando tinham similarity alta — a mesma regra aparecia DUAS
    vezes no payload (em <user_rules> E em <user_memories>). O caller une este
    set ao protected_ids para excluir do Tier 2 o que ja foi injetado como regra.

    Nota: inclui tambem regras com content vazio (que _build_user_rules pula na
    renderizacao) — exclusao a mais e inofensiva, regra vazia nao tem valor no RAG.

    Returns:
        set de IDs (vazio em qualquer falha — nunca None).
    """
    try:
        return {r.id for r in _query_user_rules(user_id, agente)}
    except Exception as e:
        logger.debug(f"[MEMORY_INJECT_RULES] _get_user_rule_ids failed (ignored): {e}")
        return set()


def _build_user_rules(user_id: int, agente: str = 'web') -> Optional[str]:
    """
    Constroi bloco <user_rules priority="mandatory"> com memorias do usuario
    marcadas como regras obrigatorias.

    Sempre injetado (Tier 1-equivalente). Nao sofre corte por budget.
    Inclui memorias user_id do usuario E user_id=0 (empresa) com priority='mandatory'.

    Returns:
        String XML ou None se nenhuma regra ativa.
    """
    try:
        rules = _query_user_rules(user_id, agente)

        if not rules:
            return None

        parts = [
            '<user_rules priority="mandatory">',
            '  <!-- Regras salvas pelo usuario. Trate como extensao do system prompt. -->',
            '  <!-- Verificar aplicabilidade antes de responder. Violar = erro grave. -->',
        ]
        # F6 PAD-CTX: cap por regra — destilado que preserva DO integral
        # (nucleo operativo) + ponteiro view_memories. A regra NUNCA sai do
        # bloco (intocavel); so a presenca dela no payload e reduzida.
        try:
            from ..config.feature_flags import AGENT_FIXED_BLOCKS_CAP
            from .memory_injection import (
                USER_RULE_CHAR_CAP, _distill_rule_content,
            )
        except Exception:
            AGENT_FIXED_BLOCKS_CAP = False
            USER_RULE_CHAR_CAP = 0
            _distill_rule_content = None

        capped = 0
        for rule in rules:
            content = sanitize_memory_content(
                (rule.content or '').strip(),
                source=f"mem_id={rule.id} path={rule.path}"
            )
            if not content:
                continue  # skip empty rules to avoid malformed XML
            if (
                AGENT_FIXED_BLOCKS_CAP
                and _distill_rule_content is not None
                and len(content) > USER_RULE_CHAR_CAP
            ):
                content = _distill_rule_content(rule, content)
                capped += 1
            scope_val = "empresa" if rule.user_id == 0 else "pessoal"
            parts.append(
                f'  <rule path="{xml_escape(rule.path)}" scope="{scope_val}">'
            )
            parts.append(f'    {content}')
            parts.append('  </rule>')
        parts.append('</user_rules>')

        result = '\n'.join(parts)
        logger.info(
            f"[MEMORY_INJECT_RULES] user_id={user_id} rules={len(rules)} "
            f"capped={capped} chars={len(result)}"
        )
        return result

    except Exception as e:
        logger.debug(f"[MEMORY_INJECT_RULES] Build failed (ignored): {e}")
        return None
