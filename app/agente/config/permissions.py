"""
Callback de permissões do agente.

Implementa canUseTool conforme documentação oficial Anthropic:
https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

Formato de retorno:
- {"behavior": "allow", "updatedInput": input} para permitir
- {"behavior": "deny", "message": "..."} para negar
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def can_use_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Callback de permissão para uso de ferramentas.

    Esta função é chamada pelo Agent SDK antes de executar cada tool.
    Implementa o padrão canUseTool conforme documentação oficial da Anthropic.

    Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

    Args:
        tool_name: Nome da ferramenta
        tool_input: Parâmetros da ferramenta

    Returns:
        Dict com formato oficial:
        {
            "behavior": "allow" | "deny",
            "updatedInput": dict (opcional - input modificado),
            "message": str (opcional - mensagem de negação)
        }
    """
    # Por padrão, permite todas as tools
    # O controle de quais tools estão disponíveis é feito via allowed_tools no SDK
    # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

    logger.debug(f"[PERMISSION] Tool '{tool_name}' permitida")
    return {
        "behavior": "allow",
        "updatedInput": tool_input
    }
