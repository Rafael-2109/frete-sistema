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
from typing import Any, Optional

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
# VALIDAÇÃO DE PATH
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
# HELPER: Contextual Retrieval — contexto semântico para embedding (T3-1)
# =====================================================================
# Referência: https://www.anthropic.com/news/contextual-retrieval
# Ao embedar uma memória, gera contexto breve (1-2 frases) via Haiku que
# situa a memória no conjunto geral do usuário. Embeda `contexto + memória`
# em vez de só `memória`, melhorando precision do retrieval em até 49-67%.
# Custo: ~$0.0003 por save_memory (1 chamada Haiku).

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_CONTEXTUAL_PROMPT = """\
<user_memories>
{existing_memories}
</user_memories>

Aqui está a memória sendo salva pelo usuário:
<memory path="{path}">
{content}
</memory>

Dê um contexto curto e sucinto (1-2 frases, máximo 80 tokens) para situar \
esta memória dentro da coleção geral de memórias do usuário. Este contexto \
será preposto à memória para melhorar a busca semântica.
Responda APENAS com o contexto sucinto, sem explicações ou formatação adicional.\
"""


def _generate_memory_context(user_id: int, path: str, content: str) -> Optional[str]:
    """
    Gera contexto semântico breve via Haiku para enriquecer embedding de memória.

    Técnica: Anthropic Contextual Retrieval (2024).
    Carrega memórias existentes do usuário como "documento",
    gera 1-2 frases de contexto que situam a nova memória no conjunto.

    Best-effort: falhas retornam None (fallback para embedding sem contexto).

    Args:
        user_id: ID do usuário
        path: Path da memória (ex: /memories/learned/regras.xml)
        content: Conteúdo da memória

    Returns:
        String com contexto (50-100 tokens) ou None se falhar
    """
    try:
        import anthropic

        # Carregar memórias existentes do usuário (paths + snippets)
        def _load_existing():
            from ..models import AgentMemory
            return AgentMemory.query.filter_by(
                user_id=user_id,
                is_directory=False,
            ).order_by(AgentMemory.updated_at.desc()).limit(30).all()

        existing = _execute_with_context(_load_existing)

        # Formatar memórias existentes como contexto do "documento"
        if existing:
            lines = []
            total_chars = 0
            for mem in existing:
                if mem.path == path:
                    continue  # Excluir a própria memória
                snippet = (mem.content or "")[:80].replace('\n', ' ').strip()
                if not snippet:
                    continue
                line = f"- {mem.path}: {snippet}"
                if total_chars + len(line) > 2000:
                    break  # Cap: ~2000 chars de contexto
                lines.append(line)
                total_chars += len(line)
            existing_text = "\n".join(lines) if lines else "(nenhuma memória anterior)"
        else:
            existing_text = "(nenhuma memória anterior — esta é a primeira)"

        # Truncar conteúdo para o prompt (economia de tokens)
        content_truncated = content[:500] if len(content) > 500 else content

        # Chamar Haiku com timeout curto (best-effort, não pode travar o save)
        client = anthropic.Anthropic(timeout=5.0)
        response = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": _CONTEXTUAL_PROMPT.format(
                    existing_memories=existing_text,
                    path=path,
                    content=content_truncated,
                ),
            }],
        )

        context = response.content[0].text.strip()

        # Validar: contexto deve ter pelo menos 10 chars e no máximo 500
        if not context or len(context) < 10:
            logger.debug(
                f"[MEMORY_MCP] Contextual: Haiku retornou contexto insuficiente "
                f"({len(context or '')} chars) para {path}"
            )
            return None

        if len(context) > 500:
            context = context[:500]

        logger.debug(
            f"[MEMORY_MCP] Contextual: gerado para {path} ({len(context)} chars)"
        )
        return context

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Contextual: falhou (ignorado): {e}")
        return None


# =====================================================================
# HELPER: Embedding de memória para busca semântica
# =====================================================================

def _embed_memory_best_effort(user_id: int, path: str, content: str) -> None:
    """
    Gera embedding de uma memória para busca semântica.

    Best-effort: falhas são silenciosas e não afetam o fluxo principal.

    Pipeline (T3-1 Contextual Retrieval):
    1. Se MEMORY_CONTEXTUAL_EMBEDDING ativo: gerar contexto via Haiku (~300ms)
    2. Construir texto_embedado: contexto + [path]: conteúdo
    3. Gerar embedding via Voyage AI (~100ms)
    4. Upsert em agent_memory_embeddings

    Args:
        user_id: ID do usuário
        path: Path da memória (ex: /memories/user.xml)
        content: Conteúdo da memória
    """
    import hashlib
    import json

    try:
        from app.embeddings.config import (
            MEMORY_SEMANTIC_SEARCH,
            VOYAGE_DEFAULT_MODEL,
            MEMORY_CONTEXTUAL_EMBEDDING,
        )
        if not MEMORY_SEMANTIC_SEARCH:
            return

        from app.embeddings.service import EmbeddingService

        # T3-1: Contextual Retrieval — gerar contexto semântico via Haiku
        context_prefix = None
        if MEMORY_CONTEXTUAL_EMBEDDING:
            context_prefix = _generate_memory_context(user_id, path, content)

        # Build texto embedado (com ou sem contexto)
        if context_prefix:
            texto_embedado = f"{context_prefix}\n\n[{path}]: {content}"
        else:
            texto_embedado = f"[{path}]: {content}"

        # Hash baseado no conteúdo original (não no texto_embedado).
        # Motivo: se só o contexto mudar (outras memórias adicionadas),
        # não re-embedamos — o contexto é "bom o suficiente" no momento do save.
        c_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

        def _do_embed():
            from ..models import AgentMemory
            from app import db
            from sqlalchemy import text

            # Buscar memory_id
            mem = AgentMemory.get_by_path(user_id, path)
            if not mem:
                return

            # Verificar se hash mudou (skip se identico)
            existing = db.session.execute(text("""
                SELECT content_hash FROM agent_memory_embeddings
                WHERE memory_id = :memory_id
            """), {"memory_id": mem.id}).fetchone()

            if existing and existing[0] == c_hash:
                return  # Conteúdo não mudou

            # Gerar embedding
            svc = EmbeddingService()
            embeddings = svc.embed_texts([texto_embedado], input_type="document")

            if not embeddings:
                return

            embedding_str = json.dumps(embeddings[0])

            # Upsert
            db.session.execute(text("""
                INSERT INTO agent_memory_embeddings
                    (memory_id, user_id, path,
                     texto_embedado, embedding, model_used, content_hash)
                VALUES
                    (:memory_id, :user_id, :path,
                     :texto_embedado, :embedding, :model_used, :content_hash)
                ON CONFLICT ON CONSTRAINT uq_memory_embedding
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    path = EXCLUDED.path,
                    texto_embedado = EXCLUDED.texto_embedado,
                    embedding = EXCLUDED.embedding,
                    model_used = EXCLUDED.model_used,
                    content_hash = EXCLUDED.content_hash,
                    updated_at = NOW()
            """), {
                "memory_id": mem.id,
                "user_id": user_id,
                "path": path,
                "texto_embedado": texto_embedado,
                "embedding": embedding_str,
                "model_used": VOYAGE_DEFAULT_MODEL,
                "content_hash": c_hash,
            })
            db.session.commit()

            logger.debug(f"[MEMORY_MCP] Embedding salvo para {path}")

        _execute_with_context(_do_embed)

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] _embed_memory_best_effort falhou: {e}")


def _calculate_importance_score(path: str, content: str) -> float:
    """
    Calcula importance score heurístico de uma memória (0-1).

    Scoring baseado em padrões do conteúdo e path, sem chamada LLM.
    Referência: Stanford Generative Agents (2023).

    Args:
        path: Path da memória
        content: Conteúdo da memória

    Returns:
        Float entre 0.0 e 1.0
    """
    score = 0.5  # default

    content_lower = content.lower() if content else ''
    path_lower = path.lower() if path else ''

    # Path-based scoring
    if '/memories/corrections/' in path_lower:
        score += 0.2  # Correções são valiosas
    elif '/memories/learned/' in path_lower:
        score += 0.1  # Aprendizados têm valor

    # Conteúdo: menção a entidades de negócio
    business_patterns = [
        'transportadora', 'cliente', 'rota', 'fornecedor',
        'produto', 'pedido', 'embarque', 'separação', 'separacao',
        'cnpj', 'nota fiscal', 'nf-e', 'fatura',
    ]
    if any(p in content_lower for p in business_patterns):
        score += 0.3

    # Conteúdo: valor monetário (R$ X.XXX,XX)
    if content and (re.search(r'R\$\s*[\d.,]+', content) or re.search(r'\d+[.,]\d{2}\b', content)):
        score += 0.2

    # Conteúdo: correção/erro
    correction_patterns = [
        'correto é', 'correto e', 'na verdade', 'errado',
        'não é', 'nao e', 'correção', 'correcao', 'corrigir',
        'nunca', 'sempre', 'importante', 'atenção', 'atencao',
        'cuidado', 'obrigatório', 'obrigatorio',
    ]
    if any(p in content_lower for p in correction_patterns):
        score += 0.3

    # Cap at 1.0
    return min(score, 1.0)


def _check_memory_duplicate(user_id: int, content: str, current_path: str = '') -> Optional[str]:
    """
    Verifica se ja existe memoria semanticamente similar para o usuario.

    Busca em agent_memory_embeddings por conteudo com cosine > 0.90,
    excluindo o path atual (para nao detectar self-match em updates).

    Args:
        user_id: ID do usuario
        content: Conteudo da nova memoria
        current_path: Path sendo atualizado (excluido da busca)

    Returns:
        Path da memoria duplicada ou None se nao houver duplicata
    """
    try:
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
        if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
            return None

        from app.embeddings.service import EmbeddingService

        svc = EmbeddingService()
        results = svc.search_memories(
            content, user_id=user_id, limit=3, min_similarity=0.90
        )

        if not results:
            return None

        for r in results:
            path = r.get('path', '')
            # Excluir self-match
            if path and path != current_path:
                similarity = r.get('similarity', 0)
                if similarity >= 0.90:
                    logger.info(
                        f"[MEMORY_MCP] Duplicata detectada: {current_path} ~ {path} "
                        f"(sim={similarity:.3f})"
                    )
                    return path

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Dedup check falhou (ignorado): {e}")

    return None


# =====================================================================
# CUSTOM TOOLS — @tool decorator
# =====================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "view_memories",
        "OBRIGATÓRIO no início de cada sessão: visualiza memórias persistentes do usuário. "
        "Consulte ANTES de responder a primeira mensagem para recuperar preferências, "
        "correções e contexto de sessões anteriores. "
        "Use path='/memories' para listar diretórios. "
        "Use path='/memories/user.xml' para ver arquivo específico. "
        "Esta ferramenta é sua ÚNICA fonte de contexto cross-session.",
        {"path": str},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        {"path": str, "content": str},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
                from app.utils.timezone import agora_utc_naive

                # Calcular importance score heurístico (QW-1)
                importance = _calculate_importance_score(path, content)

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
                    existing.importance_score = importance
                    existing.last_accessed_at = agora_utc_naive()
                    action = "atualizado"
                else:
                    mem = AgentMemory.create_file(user_id, path, content)
                    mem.importance_score = importance
                    mem.last_accessed_at = agora_utc_naive()
                    action = "criado"

                db.session.commit()
                return action

            action = _execute_with_context(_save)
            logger.info(f"[MEMORY_MCP] save_memory: {path} ({action})")

            # Best-effort: verificar duplicatas semanticas
            dedup_warning = ''
            try:
                dup_path = _check_memory_duplicate(user_id, content, current_path=path)
                if dup_path:
                    dedup_warning = (
                        f" AVISO: conteudo similar ja existe em '{dup_path}'. "
                        f"Considere consolidar."
                    )
            except Exception:
                pass

            # Best-effort: verificar se memórias precisam de consolidação
            try:
                from ..services.memory_consolidator import maybe_consolidate
                maybe_consolidate(user_id)
            except Exception as consolidation_err:
                logger.debug(
                    f"[MEMORY_MCP] Consolidação não executada (ignorado): {consolidation_err}"
                )

            # Best-effort: embeddar memória para busca semântica
            try:
                from app.embeddings.config import MEMORY_SEMANTIC_SEARCH
                if MEMORY_SEMANTIC_SEARCH:
                    _embed_memory_best_effort(user_id, path, content)
            except Exception as emb_err:
                logger.debug(f"[MEMORY_MCP] Embedding falhou (ignorado): {emb_err}")

            return {
                "content": [{"type": "text", "text": f"Memória {action} em {path}{dedup_warning}"}]
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
        {"path": str, "old_str": str, "new_str": str},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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

            # Best-effort: re-embeddar memória atualizada
            try:
                from app.embeddings.config import MEMORY_SEMANTIC_SEARCH
                if MEMORY_SEMANTIC_SEARCH:
                    # Ler conteúdo atualizado
                    def _get_content():
                        from ..models import AgentMemory
                        mem = AgentMemory.get_by_path(user_id, path)
                        return mem.content if mem else None

                    updated_content = _execute_with_context(_get_content)
                    if updated_content:
                        _embed_memory_best_effort(user_id, path, updated_content)
            except Exception as emb_err:
                logger.debug(f"[MEMORY_MCP] Embedding update falhou (ignorado): {emb_err}")

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
        {"path": str},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
                from sqlalchemy import text as sql_text

                memory = AgentMemory.get_by_path(user_id, path)
                if not memory:
                    raise FileNotFoundError(f"Path não encontrado: {path}")

                tipo = "Diretório" if memory.is_directory else "Arquivo"

                # QW-2: Cleanup explícito de embeddings (defense in depth)
                # O trigger trg_delete_memory_embedding já cuida disso no DB,
                # mas adicionamos cleanup Python para cobrir edge cases.
                try:
                    if memory.is_directory:
                        # Coletar IDs de todos os arquivos do diretório
                        children = AgentMemory.query.filter(
                            AgentMemory.user_id == user_id,
                            db.or_(
                                AgentMemory.id == memory.id,
                                AgentMemory.path.like(f'{path}/%')
                            ),
                            AgentMemory.is_directory == False,  # noqa: E712
                        ).with_entities(AgentMemory.id).all()
                        memory_ids = [c.id for c in children]
                    else:
                        memory_ids = [memory.id]

                    if memory_ids:
                        db.session.execute(sql_text("""
                            DELETE FROM agent_memory_embeddings
                            WHERE memory_id = ANY(:ids)
                        """), {"ids": memory_ids})
                except Exception as gc_err:
                    logger.debug(f"[MEMORY_MCP] Embedding cleanup falhou (ignorado): {gc_err}")

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
        {},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        {},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
