"""
Custom Tool MCP: memory

Gerenciamento de memória persistente do usuário via MCP in-process.
O modelo principal (Sonnet/Opus) chama estas tools autonomamente via tool_use
para salvar/recuperar preferências, fatos, correções e contexto.

Substitui o padrão anterior de subagente Haiku (PRE/POST-HOOK).

Referência SDK:
  https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools

Referência Memory Tool:
  https://platform.claude.com/docs/pt-BR/agents-and-tools/tool-use/memory-tool
"""

import logging
import re
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# =====================================================================
# CONTEXTO DO USUÁRIO (thread-safe via contextvars)
# =====================================================================
# MCP tools são singleton (nível de módulo), mas user_id muda por request.
# O routes.py define set_current_user_id() antes de cada query.

_current_user_id: ContextVar[int] = ContextVar('_current_user_id', default=0)


def set_current_user_id(user_id: int) -> None:
    """
    Define o user_id para o contexto atual.

    Deve ser chamado em routes.py antes de cada stream_response().

    Args:
        user_id: ID do usuário no banco de dados
    """
    _current_user_id.set(user_id)


def get_current_user_id() -> int:
    """
    Obtém o user_id do contexto atual.

    Returns:
        ID do usuário

    Raises:
        RuntimeError: Se user_id não foi definido
    """
    uid = _current_user_id.get()
    if uid == 0:
        raise RuntimeError(
            "[MEMORY_MCP] user_id não definido. "
            "Chame set_current_user_id() antes de usar as memory tools."
        )
    return uid


# =====================================================================
# SANITIZAÇÃO ANTI-INJECTION (reutilizada de memory_agent.py)
# =====================================================================
_DANGEROUS_PATTERNS = [
    re.compile(r'(?i)ignore\s+(all\s+)?previous\s+instructions'),
    re.compile(r'(?i)ignore\s+rules?\s+(P\d|R\d)'),
    re.compile(r'(?i)you\s+(must|should|are)\s+now'),
    re.compile(r'(?i)new\s+instructions?:'),
    re.compile(r'(?i)system\s*prompt'),
    re.compile(r'(?i)override\s+rules?'),
    re.compile(r'(?i)act\s+as\s+if'),
    re.compile(r'(?i)disregard\s+(all\s+)?prior'),
    re.compile(r'(?i)forget\s+(everything|all|prior)'),
]


def _sanitize_content(content: str) -> str:
    """
    Sanitiza conteúdo contra prompt injection.

    Remove padrões que tentam modificar o comportamento do agente
    quando injetados via memória persistente.

    Args:
        content: Texto a sanitizar

    Returns:
        Texto sanitizado
    """
    sanitized = content
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(sanitized):
            logger.warning(
                f"[MEMORY_MCP] Padrão perigoso detectado e filtrado: {pattern.pattern}"
            )
            sanitized = pattern.sub('[FILTRADO]', sanitized)
    return sanitized


# =====================================================================
# VALIDAÇÃO DE PATH (reutilizada de memory_tool.py)
# =====================================================================
def _validate_path(path: str) -> str:
    """
    Valida e normaliza path de memória.

    Args:
        path: Path a validar

    Returns:
        Path normalizado

    Raises:
        ValueError: Se path inválido
    """
    if not path:
        raise ValueError("Path não pode ser vazio")

    if not path.startswith('/memories'):
        raise ValueError(f"Path deve começar com /memories, recebido: {path}")

    if '..' in path:
        raise ValueError(f"Path não pode conter '..': {path}")

    while '//' in path:
        path = path.replace('//', '/')

    if path != '/memories' and path.endswith('/'):
        path = path.rstrip('/')

    return path


# =====================================================================
# HELPERS PARA ACESSO AO BANCO
# =====================================================================
def _get_app_context():
    """Obtém Flask app context."""
    try:
        from flask import current_app
        _ = current_app.name
        # Já está dentro de app context
        return None
    except RuntimeError:
        from app import create_app
        app = create_app()
        return app.app_context()


def _execute_with_context(func):
    """
    Executa função dentro de Flask app context (se necessário).

    Args:
        func: Callable que precisa de app context

    Returns:
        Resultado da função
    """
    ctx = _get_app_context()
    if ctx is None:
        # Já dentro de app context
        return func()
    else:
        with ctx:
            return func()


# =====================================================================
# CUSTOM TOOLS — @tool decorator
# =====================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server

    @tool(
        "view_memories",
        "OBRIGATÓRIO no início de cada sessão: visualiza memórias persistentes do usuário. "
        "Consulte ANTES de responder a primeira mensagem para recuperar preferências, "
        "correções e contexto de sessões anteriores. "
        "Use path='/memories' para listar diretórios. "
        "Use path='/memories/user.xml' para ver arquivo específico. "
        "Esta ferramenta é sua ÚNICA fonte de contexto cross-session.",
        {"path": str}
    )
    async def view_memories(args: dict[str, Any]) -> dict[str, Any]:
        """
        Visualiza memória ou lista diretório.

        Args:
            args: {"path": str} — path da memória (default: /memories)

        Returns:
            MCP tool response com conteúdo ou listagem
        """
        path = args.get("path", "/memories").strip()

        try:
            path = _validate_path(path)
            user_id = get_current_user_id()

            def _view():
                from ..models import AgentMemory

                memory = AgentMemory.get_by_path(user_id, path)

                # Caso especial: /memories é diretório virtual raiz
                if path == '/memories':
                    items = AgentMemory.list_directory(user_id, path)
                    if not items:
                        return "Diretório: /memories\n(vazio — nenhuma memória salva)"

                    lines = ["Diretório: /memories"]
                    for item in sorted(items, key=lambda x: x.path):
                        name = item.path.split('/')[-1]
                        suffix = '/' if item.is_directory else ''
                        lines.append(f"- {name}{suffix}")
                    return "\n".join(lines)

                if not memory:
                    return f"Path não encontrado: {path}"

                # Se diretório, lista conteúdo
                if memory.is_directory:
                    items = AgentMemory.list_directory(user_id, path)
                    if not items:
                        return f"Diretório: {path}\n(vazio)"

                    lines = [f"Diretório: {path}"]
                    for item in sorted(items, key=lambda x: x.path):
                        name = item.path.split('/')[-1]
                        suffix = '/' if item.is_directory else ''
                        lines.append(f"- {name}{suffix}")
                    return "\n".join(lines)

                # Arquivo: retorna conteúdo
                content = memory.content or "(vazio)"
                return f"Arquivo: {path}\n\n{content}"

            result = _execute_with_context(_view)
            logger.info(f"[MEMORY_MCP] view_memories: {path}")
            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            error_msg = f"Erro ao visualizar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "save_memory",
        "Salva fato, preferência ou correção na memória persistente do usuário. "
        "Use PROATIVAMENTE quando detectar: correções do usuário, preferências reveladas, "
        "regras de negócio mencionadas, informações pessoais/profissionais, "
        "ou quando o usuário pedir explicitamente ('lembre que...', 'anote...'). "
        "Paths: /memories/user.xml (info pessoal), "
        "/memories/preferences.xml (estilo/comunicação), "
        "/memories/learned/regras.xml (regras de negócio), "
        "/memories/corrections/dominio.xml (correções). "
        "Se o arquivo já existir, o conteúdo será SUBSTITUÍDO.",
        {"path": str, "content": str}
    )
    async def save_memory(args: dict[str, Any]) -> dict[str, Any]:
        """
        Cria ou atualiza memória.

        Args:
            args: {"path": str, "content": str}

        Returns:
            MCP tool response com confirmação
        """
        path = args.get("path", "").strip()
        content = args.get("content", "").strip()

        if not path:
            return {
                "content": [{"type": "text", "text": "Erro: path é obrigatório"}],
                "is_error": True,
            }
        if not content:
            return {
                "content": [{"type": "text", "text": "Erro: content é obrigatório"}],
                "is_error": True,
            }

        try:
            path = _validate_path(path)
            content = _sanitize_content(content)
            user_id = get_current_user_id()

            def _save():
                from ..models import AgentMemory, AgentMemoryVersion
                from app import db

                existing = AgentMemory.get_by_path(user_id, path)

                if existing:
                    # Salvar versão anterior antes de atualizar
                    if existing.content is not None:
                        AgentMemoryVersion.save_version(
                            memory_id=existing.id,
                            content=existing.content,
                            changed_by='claude'
                        )
                    existing.content = content
                    existing.is_directory = False
                    action = "atualizado"
                else:
                    AgentMemory.create_file(user_id, path, content)
                    action = "criado"

                db.session.commit()
                return action

            action = _execute_with_context(_save)
            logger.info(f"[MEMORY_MCP] save_memory: {path} ({action})")

            # Best-effort: verificar se memórias precisam de consolidação
            try:
                from ..services.memory_consolidator import maybe_consolidate
                maybe_consolidate(user_id)
            except Exception as consolidation_err:
                logger.debug(
                    f"[MEMORY_MCP] Consolidação não executada (ignorado): {consolidation_err}"
                )

            return {
                "content": [{"type": "text", "text": f"Memória {action} em {path}"}]
            }

        except Exception as e:
            error_msg = f"Erro ao salvar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "update_memory",
        "Substitui um trecho de texto em um arquivo de memória existente. "
        "O old_str deve ser encontrado exatamente UMA vez no arquivo. "
        "Use para atualizar informações específicas sem reescrever o arquivo inteiro.",
        {"path": str, "old_str": str, "new_str": str}
    )
    async def update_memory(args: dict[str, Any]) -> dict[str, Any]:
        """
        Substitui texto em memória existente.

        Args:
            args: {"path": str, "old_str": str, "new_str": str}

        Returns:
            MCP tool response com confirmação
        """
        path = args.get("path", "").strip()
        old_str = args.get("old_str", "")
        new_str = args.get("new_str", "")

        if not path or not old_str:
            return {
                "content": [{"type": "text", "text": "Erro: path e old_str são obrigatórios"}],
                "is_error": True,
            }

        try:
            path = _validate_path(path)
            new_str = _sanitize_content(new_str)
            user_id = get_current_user_id()

            def _update():
                from ..models import AgentMemory, AgentMemoryVersion
                from app import db

                memory = AgentMemory.get_by_path(user_id, path)
                if not memory:
                    raise FileNotFoundError(f"Arquivo não encontrado: {path}")
                if memory.is_directory:
                    raise ValueError(f"Não é possível editar diretório: {path}")

                content = memory.content or ""
                count = content.count(old_str)

                if count == 0:
                    raise ValueError(f"Texto não encontrado em {path}")
                if count > 1:
                    raise ValueError(f"Texto aparece {count} vezes. Deve ser único.")

                # Versão anterior
                if content:
                    AgentMemoryVersion.save_version(
                        memory_id=memory.id,
                        content=content,
                        changed_by='claude'
                    )

                memory.content = content.replace(old_str, new_str)
                db.session.commit()

            _execute_with_context(_update)
            logger.info(f"[MEMORY_MCP] update_memory: {path}")
            return {
                "content": [{"type": "text", "text": f"Memória atualizada em {path}"}]
            }

        except Exception as e:
            error_msg = f"Erro ao atualizar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "delete_memory",
        "Deleta um arquivo ou diretório de memória. "
        "Não é possível deletar o diretório raiz /memories.",
        {"path": str}
    )
    async def delete_memory(args: dict[str, Any]) -> dict[str, Any]:
        """
        Deleta memória.

        Args:
            args: {"path": str}

        Returns:
            MCP tool response com confirmação
        """
        path = args.get("path", "").strip()

        if not path:
            return {
                "content": [{"type": "text", "text": "Erro: path é obrigatório"}],
                "is_error": True,
            }

        try:
            path = _validate_path(path)
            user_id = get_current_user_id()

            if path == '/memories':
                return {
                    "content": [{"type": "text", "text": "Erro: não é possível deletar /memories raiz. Use clear_memories para limpar tudo."}],
                    "is_error": True,
                }

            def _delete():
                from ..models import AgentMemory
                from app import db

                memory = AgentMemory.get_by_path(user_id, path)
                if not memory:
                    raise FileNotFoundError(f"Path não encontrado: {path}")

                tipo = "Diretório" if memory.is_directory else "Arquivo"
                count = AgentMemory.delete_by_path(user_id, path)
                db.session.commit()
                return f"{tipo} deletado: {path}" + (f" ({count} itens)" if count > 1 else "")

            result = _execute_with_context(_delete)
            logger.info(f"[MEMORY_MCP] delete_memory: {path}")
            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            error_msg = f"Erro ao deletar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "list_memories",
        "Lista todos os arquivos de memória persistente do usuário. "
        "Use no INÍCIO de cada sessão para verificar o que há salvo. "
        "Retorna paths e preview do conteúdo de cada memória.",
        {}
    )
    async def list_memories(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        """
        Lista todas as memórias do usuário.

        Returns:
            MCP tool response com listagem
        """
        try:
            user_id = get_current_user_id()

            def _list():
                from ..models import AgentMemory

                memories = AgentMemory.query.filter_by(
                    user_id=user_id,
                    is_directory=False,
                ).order_by(AgentMemory.path).all()

                if not memories:
                    return "Nenhuma memória salva."

                lines = [f"Memórias do usuário ({len(memories)} arquivos):\n"]
                for mem in memories:
                    content_preview = (mem.content or "")[:80]
                    if len(mem.content or "") > 80:
                        content_preview += "..."
                    lines.append(f"- {mem.path}: {content_preview}")

                return "\n".join(lines)

            result = _execute_with_context(_list)
            logger.info(f"[MEMORY_MCP] list_memories: user={user_id}")
            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            error_msg = f"Erro ao listar memórias: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "clear_memories",
        "Limpa TODAS as memórias do usuário. "
        "Use apenas quando o usuário pedir explicitamente para limpar tudo. "
        "Esta ação é IRREVERSÍVEL.",
        {}
    )
    async def clear_memories(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        """
        Limpa todas as memórias do usuário.

        Returns:
            MCP tool response com confirmação
        """
        try:
            user_id = get_current_user_id()

            def _clear():
                from ..models import AgentMemory
                from app import db

                count = AgentMemory.clear_all_for_user(user_id)
                db.session.commit()
                return count

            count = _execute_with_context(_clear)
            logger.info(f"[MEMORY_MCP] clear_memories: user={user_id}, count={count}")
            return {
                "content": [{"type": "text", "text": f"Todas as memórias limpas ({count} itens removidos)"}]
            }

        except Exception as e:
            error_msg = f"Erro ao limpar memórias: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    # Criar MCP server in-process
    memory_server = create_sdk_mcp_server(
        name="memory-tools",
        version="1.0.0",
        tools=[
            view_memories,
            save_memory,
            update_memory,
            delete_memory,
            list_memories,
            clear_memories,
        ],
    )

    logger.info("[MEMORY_MCP] Custom Tool MCP 'memory' registrada com sucesso (6 operações)")

except ImportError as e:
    # claude_agent_sdk não disponível (ex: rodando fora do agente)
    memory_server = None
    logger.debug(f"[MEMORY_MCP] claude_agent_sdk não disponível: {e}")
