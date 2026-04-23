"""
Hooks do Agent SDK para o Agente Lojas HORA.

M1: apenas user_prompt_submit que injeta <loja_context> e <session_context>
a cada turno. Permite que o system prompt permaneca estatico (cache hit) e
o escopo por loja seja aplicado dinamicamente.
"""
import logging
from typing import Optional, Callable, Awaitable, Any

from app.agente_lojas.services.scope_injector import build_loja_context_block

logger = logging.getLogger('sistema_fretes')


def make_user_prompt_submit_hook(
    user_id: int,
    user_name: str,
    perfil: str,
    loja_hora_id: Optional[int],
) -> Callable[..., Awaitable[Any]]:
    """Fabrica hook que injeta contexto (usuario + escopo de loja) por turno.

    Returns:
        Async callable compativel com HookMatcher do SDK 0.1.60+.
    """
    async def _hook(input_data, tool_use_id, context):
        loja_block = build_loja_context_block(perfil=perfil, loja_hora_id=loja_hora_id)

        # Bloco de sessao/usuario (analogo ao agente logistico)
        session_block = (
            "<session_context>\n"
            f"  user_id: {user_id}\n"
            f"  usuario_nome: {user_name}\n"
            f"  perfil: {perfil}\n"
            "</session_context>"
        )

        additional = f"{session_block}\n\n{loja_block}"

        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional,
            },
        }

    return _hook
