"""
Callback de permissões do agente.

Implementa canUseTool conforme documentação oficial Anthropic:
https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

SDK 0.1.26+: Assinatura com 3 parâmetros e retorno tipado.

REGRAS DE SEGURANÇA:
- Write: APENAS permitido para /tmp (arquivos temporários, exports)
- Edit: APENAS permitido para /tmp (mesma regra)
- Bash: Permitido (executado em sandbox pelo SDK)
- Outras tools: Permitidas por padrão
- FAIL-CLOSED: Erros de validação NEGAM por segurança
"""

import logging
import os
import tempfile
from typing import Any

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

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
    tool_input: dict[str, Any],
    context: ToolPermissionContext | None = None,
) -> PermissionResultAllow | PermissionResultDeny:
    """
    Callback de permissão para uso de ferramentas.

    Esta função é chamada pelo Agent SDK antes de executar cada tool.
    SDK 0.1.26+: 3 parâmetros, retorno tipado (PermissionResult).

    REGRAS:
    - Write: APENAS /tmp (para exports, arquivos temporários)
    - Edit: APENAS /tmp (segurança em produção)
    - Bash: Permitido (com logging)
    - Outras tools: Permitidas
    - FAIL-CLOSED: Erros negam por segurança

    Args:
        tool_name: Nome da ferramenta
        tool_input: Parâmetros da ferramenta
        context: ToolPermissionContext do SDK (signal, suggestions)

    Returns:
        PermissionResultAllow ou PermissionResultDeny
    """
    try:
        # ================================================================
        # REGRA: Write APENAS para /tmp
        # ================================================================
        if tool_name == 'Write':
            file_path = tool_input.get('file_path', '')

            if not file_path:
                logger.warning("[PERMISSION] Write negado: file_path vazio")
                return PermissionResultDeny(
                    message="Escrita negada: caminho do arquivo não especificado."
                )

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
                return PermissionResultDeny(
                    message=(
                        f"Escrita negada: apenas arquivos em /tmp são permitidos.\n"
                        f"Caminho solicitado: {file_path}\n"
                        f"Use /tmp/agente_files/ para criar arquivos de export."
                    )
                )

            logger.info(f"[PERMISSION] Write permitido: {normalized_path}")
            return PermissionResultAllow(updated_input=tool_input)

        # ================================================================
        # REGRA: Edit APENAS para /tmp (mesma regra do Write)
        # ================================================================
        if tool_name == 'Edit':
            file_path = tool_input.get('file_path', '')

            if not file_path:
                logger.warning("[PERMISSION] Edit negado: file_path vazio")
                return PermissionResultDeny(
                    message="Edição negada: caminho do arquivo não especificado."
                )

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
                return PermissionResultDeny(
                    message=(
                        f"Edição negada: apenas arquivos em /tmp são permitidos.\n"
                        f"Caminho solicitado: {file_path}\n"
                        f"Use /tmp/agente_files/ para editar arquivos temporários."
                    )
                )

            logger.info(f"[PERMISSION] Edit permitido: {normalized_path}")
            return PermissionResultAllow(updated_input=tool_input)

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

            return PermissionResultAllow(updated_input=tool_input)

        # ================================================================
        # DEFAULT: Permite outras tools
        # ================================================================
        logger.debug(f"[PERMISSION] Tool '{tool_name}' permitida")
        return PermissionResultAllow(updated_input=tool_input)

    except Exception as e:
        # ================================================================
        # FAIL-CLOSED: Se der erro na validação, NEGA por segurança
        # SDK 0.1.26+: Comportamento seguro — negar em caso de dúvida
        # ================================================================
        logger.error(
            f"[PERMISSION] ERRO ao validar tool '{tool_name}': {e}. "
            f"NEGANDO por segurança (fail-closed)."
        )
        return PermissionResultDeny(
            message=f"Erro interno de permissão: {e}"
        )
