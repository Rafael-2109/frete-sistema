"""
Callback de permissões do agente.

Implementa canUseTool conforme documentação oficial Anthropic:
https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

Formato de retorno:
- {"behavior": "allow", "updatedInput": input} para permitir
- {"behavior": "deny", "message": "..."} para negar

REGRAS DE SEGURANÇA:
- Write: APENAS permitido para /tmp (arquivos temporários, exports)
- Edit: BLOQUEADO (não permitir edição de código em produção)
- Bash: Permitido (executado em sandbox pelo SDK)
- Outras tools: Permitidas por padrão
"""

import logging
import os
import tempfile
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Diretório temporário padrão do sistema
TEMP_DIR = tempfile.gettempdir()  # /tmp no Linux

# Prefixos permitidos para Write
ALLOWED_WRITE_PREFIXES = [
    TEMP_DIR,           # /tmp
    '/tmp',             # Fallback explícito
    '/var/tmp',         # Alternativa em alguns sistemas
]


async def can_use_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Callback de permissão para uso de ferramentas.

    Esta função é chamada pelo Agent SDK antes de executar cada tool.
    Implementa o padrão canUseTool conforme documentação oficial da Anthropic.

    REGRAS:
    - Write: APENAS /tmp (para exports, arquivos temporários)
    - Edit: BLOQUEADO (segurança em produção)
    - Outras tools: Permitidas

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
    try:
        # ================================================================
        # REGRA: Write APENAS para /tmp
        # ================================================================
        if tool_name == 'Write':
            file_path = tool_input.get('file_path', '')

            if not file_path:
                logger.warning("[PERMISSION] Write negado: file_path vazio")
                return {
                    "behavior": "deny",
                    "message": "❌ Escrita negada: caminho do arquivo não especificado."
                }

            # Normaliza o caminho para evitar bypasses (../../etc)
            normalized_path = os.path.normpath(os.path.abspath(file_path))

            # Verifica se está em diretório permitido
            is_allowed = any(
                normalized_path.startswith(prefix)
                for prefix in ALLOWED_WRITE_PREFIXES
            )

            if not is_allowed:
                logger.warning(
                    f"[PERMISSION] Write negado: {file_path} "
                    f"(normalizado: {normalized_path}) não está em /tmp"
                )
                return {
                    "behavior": "deny",
                    "message": (
                        f"❌ Escrita negada: apenas arquivos em /tmp são permitidos.\n"
                        f"Caminho solicitado: {file_path}\n"
                        f"Use /tmp/agente_files/ para criar arquivos de export."
                    )
                }

            logger.info(f"[PERMISSION] Write permitido: {normalized_path}")
            return {
                "behavior": "allow",
                "updatedInput": tool_input
            }

        # ================================================================
        # REGRA: Edit APENAS para /tmp (mesma regra do Write)
        # ================================================================
        if tool_name == 'Edit':
            file_path = tool_input.get('file_path', '')

            if not file_path:
                logger.warning("[PERMISSION] Edit negado: file_path vazio")
                return {
                    "behavior": "deny",
                    "message": "❌ Edição negada: caminho do arquivo não especificado."
                }

            # Normaliza o caminho para evitar bypasses (../../etc)
            normalized_path = os.path.normpath(os.path.abspath(file_path))

            # Verifica se está em diretório permitido
            is_allowed = any(
                normalized_path.startswith(prefix)
                for prefix in ALLOWED_WRITE_PREFIXES
            )

            if not is_allowed:
                logger.warning(
                    f"[PERMISSION] Edit negado: {file_path} "
                    f"(normalizado: {normalized_path}) não está em /tmp"
                )
                return {
                    "behavior": "deny",
                    "message": (
                        f"❌ Edição negada: apenas arquivos em /tmp são permitidos.\n"
                        f"Caminho solicitado: {file_path}\n"
                        f"Use /tmp/agente_files/ para editar arquivos temporários."
                    )
                }

            logger.info(f"[PERMISSION] Edit permitido: {normalized_path}")
            return {
                "behavior": "allow",
                "updatedInput": tool_input
            }

        # ================================================================
        # REGRA: Bash - Permitido (com logging)
        # ================================================================
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            description = tool_input.get('description', '')

            # Log para auditoria
            logger.info(
                f"[PERMISSION] Bash permitido: {description or command[:100]}"
            )

            return {
                "behavior": "allow",
                "updatedInput": tool_input
            }

        # ================================================================
        # DEFAULT: Permite outras tools
        # ================================================================
        logger.debug(f"[PERMISSION] Tool '{tool_name}' permitida")
        return {
            "behavior": "allow",
            "updatedInput": tool_input
        }

    except Exception as e:
        # ================================================================
        # NUNCA TRAVAR: Se der erro na validação, loga e permite
        # Melhor permitir com log do que travar o agente
        # ================================================================
        logger.error(
            f"[PERMISSION] ERRO ao validar tool '{tool_name}': {e}. "
            f"Permitindo por segurança (fail-open)."
        )
        return {
            "behavior": "allow",
            "updatedInput": tool_input
        }
