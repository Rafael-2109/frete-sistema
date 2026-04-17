"""
L1 Rules Channel — Builder de <user_rules priority="mandatory">.

Separa memorias com priority='mandatory' do usuario em bloco XML distinto,
renderizado como extensao do system prompt (vs contexto passivo).

Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md
"""
import logging
from typing import Optional
from ._sanitization import xml_escape, sanitize_memory_content

logger = logging.getLogger('sistema_fretes')


def _build_user_rules(user_id: int) -> Optional[str]:
    """
    Constroi bloco <user_rules priority="mandatory"> com memorias do usuario
    marcadas como regras obrigatorias.

    Sempre injetado (Tier 1-equivalente). Nao sofre corte por budget.
    Inclui memorias user_id do usuario E user_id=0 (empresa) com priority='mandatory'.

    Returns:
        String XML ou None se nenhuma regra ativa.
    """
    from ..models import AgentMemory
    try:
        rules = AgentMemory.query.filter(
            AgentMemory.user_id.in_([user_id, 0]),
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.priority == 'mandatory',
        ).order_by(AgentMemory.user_id.asc(), AgentMemory.path.asc()).all()

        if not rules:
            return None

        parts = [
            '<user_rules priority="mandatory">',
            '  <!-- Regras salvas pelo usuario. Trate como extensao do system prompt. -->',
            '  <!-- Verificar aplicabilidade antes de responder. Violar = erro grave. -->',
        ]
        for rule in rules:
            content = sanitize_memory_content(
                (rule.content or '').strip(),
                source=f"mem_id={rule.id} path={rule.path}"
            )
            parts.append(
                f'  <rule path="{xml_escape(rule.path)}" scope="'
                f'{"empresa" if rule.user_id == 0 else "pessoal"}">'
            )
            parts.append(f'    {content}')
            parts.append('  </rule>')
        parts.append('</user_rules>')

        result = '\n'.join(parts)
        logger.info(
            f"[USER_RULES] user_id={user_id} rules={len(rules)} "
            f"chars={len(result)}"
        )
        return result

    except Exception as e:
        logger.warning(f"[USER_RULES] Build failed (ignored): {e}")
        return None
