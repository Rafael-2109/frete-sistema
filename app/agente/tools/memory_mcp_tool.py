"""
Custom Tool MCP: memory

Gerenciamento de memória persistente do usuário via MCP in-process.
O modelo principal (Sonnet/Opus) chama estas tools autonomamente via tool_use
para salvar/recuperar preferências, fatos, correções e contexto.

Substitui o padrão anterior de subagente Sonnet (PRE/POST-HOOK).

Referência SDK:
  https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools

Referência Memory Tool:
  https://platform.claude.com/docs/pt-BR/agents-and-tools/tool-use/memory-tool
"""

import logging
import re
import threading
from contextvars import ContextVar
from typing import Annotated, Any, Optional

logger = logging.getLogger(__name__)

# =====================================================================
# CONTEXTO DO USUÁRIO (ContextVar + fallback cross-thread SEGURO)
# =====================================================================
# MCP tools são singleton (nível de módulo), mas user_id muda por request.
# O routes.py/client.py define set_current_user_id() antes de cada query.
#
# PROBLEMA: O Claude Agent SDK executa MCP tools na thread "sdk-pool-daemon",
# diferente da thread onde set_current_user_id() é chamado. ContextVar é
# isolado por thread, então o valor não é visível no daemon.
#
# SOLUÇÃO: ContextVar (correto na mesma thread) + dict keyed por thread ID
# como fallback. O dict armazena {caller_thread_id: user_id}. No getter,
# se ContextVar=0, só usa fallback quando TODOS os callers ativos têm o
# MESMO user_id. Se há callers com IDs diferentes (concorrência multi-user),
# NÃO resolve — mantém o erro original para evitar cross-user data leak.
#
# Cleanup: clear_current_user_id() remove entrada do dict. Deve ser chamado
# no finally do agent invocation (client.py).

_current_user_id: ContextVar[int] = ContextVar('_current_user_id', default=0)
_user_id_by_caller: dict[int, int] = {}
_uid_lock = threading.Lock()


def set_current_user_id(user_id: int) -> None:
    """
    Define o user_id para o contexto atual.

    Deve ser chamado em routes.py antes de cada stream_response().
    Grava em ContextVar (mesma thread) E dict por caller thread (cross-thread).

    Args:
        user_id: ID do usuário no banco de dados
    """
    _current_user_id.set(user_id)
    tid = threading.current_thread().ident
    with _uid_lock:
        _user_id_by_caller[tid] = user_id


def clear_current_user_id() -> None:
    """
    Remove user_id do caller atual no dict cross-thread.

    Deve ser chamado no finally do agent invocation para evitar stale entries.
    """
    tid = threading.current_thread().ident
    with _uid_lock:
        _user_id_by_caller.pop(tid, None)


def get_current_user_id() -> int:
    """
    Obtém o user_id do contexto atual.

    Tenta ContextVar primeiro (isolamento por thread). Se não setado (MCP
    daemon thread), consulta dict cross-thread — só resolve se TODOS os
    callers ativos têm o MESMO user_id. Com callers diferentes, mantém
    o erro para evitar cross-user data leak.

    Returns:
        ID do usuário

    Raises:
        RuntimeError: Se user_id não pode ser determinado com segurança
    """
    uid = _current_user_id.get()
    if uid == 0:
        with _uid_lock:
            unique_ids = set(_user_id_by_caller.values())
            if len(unique_ids) == 1:
                uid = next(iter(unique_ids))
            elif len(unique_ids) > 1:
                logger.warning(
                    "[MEMORY_MCP] Múltiplos user_ids ativos (%s) — "
                    "não é seguro resolver cross-thread",
                    unique_ids,
                )
    if uid == 0:
        raise RuntimeError(
            "[MEMORY_MCP] user_id não definido. "
            "Chame set_current_user_id() antes de usar as memory tools."
        )
    return uid


# =====================================================================
# SANITIZAÇÃO ANTI-INJECTION
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


def _resolve_user_id(args: dict) -> int:
    """
    Resolve user_id efetivo: proprio usuario ou target em debug mode.

    Args:
        args: Dict dos argumentos da tool (pode conter target_user_id)

    Returns:
        user_id efetivo para a operacao

    Raises:
        PermissionError: target_user_id sem debug mode ativo
    """
    target = args.get('target_user_id')
    current = get_current_user_id()

    if target is None or target == current:
        return current

    # Cross-user requer debug mode (validacao deterministica)
    from ..config.permissions import get_debug_mode
    if not get_debug_mode():
        raise PermissionError(
            f"Acesso a memorias de outro usuario (ID={target}) requer Modo Debug ativo. "
            f"Peca ao administrador ativar o toggle de debug."
        )

    logger.warning(
        f"[MEMORY_MCP] DEBUG: acesso cross-user user={current} -> target={target}"
    )
    return target


def _resolve_empresa_user_id(user_id: int, path: str) -> int:
    """
    Resolve user_id real: paths /memories/empresa/* pertencem a user_id=0 (Sistema).

    Centraliza a lógica que antes estava inline em save_memory.
    Usado por todas as tools que acessam memórias por path.

    Args:
        user_id: ID do operador (usuário logado)
        path: Path da memória

    Returns:
        0 se path empresa, senão user_id original
    """
    if path.startswith('/memories/empresa/'):
        return 0
    return user_id


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
# EXCEÇÕES DE DOMÍNIO
# =====================================================================

class DuplicateMemoryError(Exception):
    """Raised when dedup gate detects duplicate memory before commit."""

    def __init__(self, dup_path: str):
        self.dup_path = dup_path
        super().__init__(f"Duplicate memory: {dup_path}")


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
# Ao embedar uma memória, gera contexto breve (1-2 frases) via Sonnet que
# situa a memória no conjunto geral do usuário. Embeda `contexto + memória`
# em vez de só `memória`, melhorando precision do retrieval em até 49-67%.
# Custo: ~$0.0012 por save_memory (1 chamada Sonnet).

_SONNET_MODEL = "claude-sonnet-4-6"

_CONTEXTUAL_SYSTEM_PROMPT = """\
Voce eh um analisador de memorias de um sistema de logistica (Nacom Goya).
Dada uma memoria sendo salva e o contexto das memorias existentes do usuario, gere:

1. CONTEXTO: 2-3 frases situando esta memoria no conjunto do usuario (maximo 150 tokens)
2. ENTIDADES: lista de entidades no formato tipo:nome:relevancia separadas por | onde relevancia eh E (essencial ao significado) ou A (incidental/acidental)
   Exemplo: transportadora:RODONAVES:E|uf:AM:A|cliente:ATACADAO:E
3. RELACOES: lista de relacoes no formato origem>tipo>destino:confianca separadas por | onde confianca eh alta, media ou baixa
   Exemplo: RODONAVES>atrasa_para>AM:alta

Tipos de entidade PERMITIDOS: uf, pedido, cnpj, valor, transportadora, produto, cliente, fornecedor, usuario, processo, conceito, campo, termo
Tipos de relacao PERMITIDOS: pertence_a, depende_de, substitui, conflita_com, precede, bloqueia, usa, produz, fornece, consome, localizado_em, responsavel_por, corrige, requer, complementa, atrasa_para
Use APENAS tipos das listas acima. Se nenhum tipo se aplica, NAO gere a entidade/relacao.
Se nao houver entidades ou relacoes claras, escreva ENTIDADES: nenhuma e RELACOES: nenhuma

Responda EXATAMENTE no formato abaixo. Cada secao eh obrigatoria.
CONTEXTO: ...
ENTIDADES: ...
RELACOES: ...\
"""

_CONTEXTUAL_USER_TEMPLATE = """\
<user_memories>
{existing_memories}
</user_memories>

<memory path="{path}">
{content}
</memory>\
"""


def _generate_memory_context(
    user_id: int, path: str, content: str,
) -> tuple[Optional[str], list[tuple[str, str]], list[tuple[str, str, str]]]:
    """
    Gera contexto semântico breve via Sonnet para enriquecer embedding de memória.

    T3-1: Anthropic Contextual Retrieval (2024).
    T3-3: Prompt ampliado para extrair entidades e relações (Knowledge Graph).

    Carrega memórias existentes do usuário como "documento",
    gera contexto + entidades + relações em formato estruturado.

    Best-effort: falhas retornam (None, [], []) (fallback para embedding sem contexto).

    Args:
        user_id: ID do usuário
        path: Path da memória (ex: /memories/learned/regras.xml)
        content: Conteúdo da memória

    Returns:
        Tupla (context, entities, relations):
        - context: String com contexto (50-100 tokens) ou None se falhar
        - entities: [(tipo, nome), ...] — entidades extraídas pelo Sonnet
        - relations: [(origem, tipo_relacao, destino), ...] — relações semânticas
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
                if total_chars + len(line) > 3000:
                    break  # Cap: ~3000 chars de contexto
                lines.append(line)
                total_chars += len(line)
            existing_text = "\n".join(lines) if lines else "(nenhuma memória anterior)"
        else:
            existing_text = "(nenhuma memória anterior — esta é a primeira)"

        # Truncar conteúdo para o prompt (economia de tokens)
        content_truncated = content[:1000] if len(content) > 1000 else content

        # Chamar Sonnet para contexto + entidades + relações (roda em background, sem timeout artificial)
        # T3-3: max_tokens 350 para acomodar entidades+relações ricas
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_SONNET_MODEL,
            max_tokens=350,
            system=[{
                "type": "text",
                "text": _CONTEXTUAL_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": _CONTEXTUAL_USER_TEMPLATE.format(
                    existing_memories=existing_text,
                    path=path,
                    content=content_truncated,
                ),
            }],
        )

        raw_text = response.content[0].text.strip()

        # T3-3: Parse estruturado com fallback
        from ..services.knowledge_graph_service import parse_contextual_response
        context, entities, relations = parse_contextual_response(raw_text)

        # Validar contexto: pelo menos 10 chars e no máximo 500
        if not context or len(context) < 10:
            logger.debug(
                f"[MEMORY_MCP] Contextual: Sonnet retornou contexto insuficiente "
                f"({len(context or '')} chars) para {path}"
            )
            return None, entities, relations

        if len(context) > 500:
            context = context[:500]

        logger.debug(
            f"[MEMORY_MCP] Contextual: gerado para {path} ({len(context)} chars, "
            f"{len(entities)} entidades, {len(relations)} relações)"
        )
        return context, entities, relations

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Contextual: falhou (ignorado): {e}")
        return None, [], []


# =====================================================================
# HELPER: Embedding de memória para busca semântica
# =====================================================================

def _embed_memory_best_effort(
    user_id: int, path: str, content: str,
) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """
    Gera embedding de uma memória para busca semântica.

    Best-effort: falhas são silenciosas e não afetam o fluxo principal.

    Pipeline (T3-1 Contextual Retrieval + T3-3 Knowledge Graph):
    1. Se MEMORY_CONTEXTUAL_EMBEDDING ativo: gerar contexto + entidades + relações via Sonnet (~300ms)
    2. Construir texto_embedado: contexto + [path]: conteúdo
    3. Gerar embedding via Voyage AI (~100ms)
    4. Upsert em agent_memory_embeddings

    Args:
        user_id: ID do usuário
        path: Path da memória (ex: /memories/user.xml)
        content: Conteúdo da memória

    Returns:
        Tupla (haiku_entities, haiku_relations) para uso pelo caller no KG pipeline.
        Retorna ([], []) se contextual embedding desabilitado ou falhou.
    """
    import hashlib
    import json

    haiku_entities = []
    haiku_relations = []

    try:
        from app.embeddings.config import (
            MEMORY_SEMANTIC_SEARCH,
            VOYAGE_DEFAULT_MODEL,
            MEMORY_CONTEXTUAL_EMBEDDING,
        )
        if not MEMORY_SEMANTIC_SEARCH:
            return haiku_entities, haiku_relations

        from app.embeddings.service import EmbeddingService

        # T3-1 + T3-3: Contextual Retrieval — gerar contexto + entidades + relações via Sonnet
        context_prefix = None
        if MEMORY_CONTEXTUAL_EMBEDDING:
            context_prefix, haiku_entities, haiku_relations = _generate_memory_context(
                user_id, path, content
            )

        # Build texto embedado (com ou sem contexto) — para RETRIEVAL
        if context_prefix:
            texto_embedado = f"{context_prefix}\n\n[{path}]: {content}"
        else:
            texto_embedado = f"[{path}]: {content}"

        # Build texto limpo — para DEDUP
        # Strip XML tags + decode entities → texto puro para embedding de dedup.
        # Voyage AI embeddings capturam similaridade semantica sem normalizacao adicional.
        dedup_texto = _canonicalize_for_dedup(content)

        # Hash baseado no conteúdo original (não no texto_embedado).
        # Motivo: se só o contexto mudar (outras memórias adicionadas),
        # não re-embedamos — o contexto é "bom o suficiente" no momento do save.
        c_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

        def _do_embed():
            from ..models import AgentMemory
            from app import db
            from sqlalchemy import text
            from app.utils.timezone import agora_utc_naive

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

            # Gerar embeddings: retrieval (contextual) + dedup (texto limpo)
            svc = EmbeddingService()
            try:
                embeddings = svc.embed_texts(
                    [texto_embedado, dedup_texto], input_type="document"
                )
            except Exception as e:
                from app.embeddings.client import EmbeddingUnavailableError
                if isinstance(e, EmbeddingUnavailableError):
                    logger.warning(f"[memory_embed] Voyage indisponivel, pulando: {e}")
                    return
                raise

            if not embeddings or len(embeddings) < 2:
                return

            embedding_str = json.dumps(embeddings[0])
            dedup_embedding_str = json.dumps(embeddings[1])

            # Upsert (inclui dedup_embedding)
            db.session.execute(text("""
                INSERT INTO agent_memory_embeddings
                    (memory_id, user_id, path,
                     texto_embedado, embedding, dedup_embedding,
                     model_used, content_hash)
                VALUES
                    (:memory_id, :user_id, :path,
                     :texto_embedado, :embedding, CAST(:dedup_embedding AS vector),
                     :model_used, :content_hash)
                ON CONFLICT ON CONSTRAINT uq_memory_embedding
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    path = EXCLUDED.path,
                    texto_embedado = EXCLUDED.texto_embedado,
                    embedding = EXCLUDED.embedding,
                    dedup_embedding = EXCLUDED.dedup_embedding,
                    model_used = EXCLUDED.model_used,
                    content_hash = EXCLUDED.content_hash,
                    updated_at = :updated_at
            """), {
                "memory_id": mem.id,
                "user_id": user_id,
                "path": path,
                "texto_embedado": texto_embedado,
                "embedding": embedding_str,
                "dedup_embedding": dedup_embedding_str,
                "model_used": VOYAGE_DEFAULT_MODEL,
                "content_hash": c_hash,
                "updated_at": agora_utc_naive(),
            })
            db.session.commit()

            logger.debug(f"[MEMORY_MCP] Embedding salvo para {path} (retrieval + dedup)")

        _execute_with_context(_do_embed)

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] _embed_memory_best_effort falhou: {e}")

    return haiku_entities, haiku_relations


def _save_dedup_embedding_only(user_id: int, path: str, content: str) -> None:
    """
    Salva APENAS o dedup_embedding de forma síncrona (~100ms Voyage).

    Garante que o próximo save_memory() detecte esta memória via Layer 1.
    O daemon thread posteriormente preencherá o embedding contextual completo.

    content_hash=NULL sinaliza ao daemon que processamento completo é necessário.

    Args:
        user_id: ID do usuário (pode ser 0 para empresa)
        path: Path da memória
        content: Conteúdo da memória (pode conter XML)
    """
    import json

    from app.embeddings.config import EMBEDDINGS_ENABLED, MEMORY_SEMANTIC_SEARCH
    if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
        return

    from ..models import AgentMemory
    from app.embeddings.service import EmbeddingService
    from ..services.knowledge_graph_service import clean_for_comparison
    from app import db
    from sqlalchemy import text
    from app.utils.timezone import agora_utc_naive
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL

    mem = AgentMemory.get_by_path(user_id, path)
    if not mem:
        return

    dedup_texto = clean_for_comparison(content)
    if not dedup_texto.strip():
        return

    svc = EmbeddingService()
    try:
        embeddings = svc.embed_texts([dedup_texto], input_type="document")
    except Exception as e:
        from app.embeddings.client import EmbeddingUnavailableError
        if isinstance(e, EmbeddingUnavailableError):
            logger.warning(f"[memory_dedup_embed] Voyage indisponivel, pulando: {e}")
            return
        raise
    if not embeddings:
        return

    dedup_embedding_str = json.dumps(embeddings[0])

    # Upsert: apenas dedup_embedding + placeholder texto_embedado.
    # content_hash=NULL sinaliza ao daemon que processamento completo é necessário.
    # ON CONFLICT: atualiza apenas dedup_embedding (não sobrescreve embedding contextual
    # caso daemon já tenha rodado — improvável mas seguro).
    db.session.execute(text("""
        INSERT INTO agent_memory_embeddings
            (memory_id, user_id, path,
             texto_embedado, dedup_embedding,
             model_used, content_hash)
        VALUES
            (:memory_id, :user_id, :path,
             :texto_embedado, CAST(:dedup_embedding AS vector),
             :model_used, NULL)
        ON CONFLICT ON CONSTRAINT uq_memory_embedding
        DO UPDATE SET
            dedup_embedding = EXCLUDED.dedup_embedding,
            updated_at = :updated_at
    """), {
        "memory_id": mem.id,
        "user_id": user_id,
        "path": path,
        "texto_embedado": dedup_texto,
        "dedup_embedding": dedup_embedding_str,
        "model_used": VOYAGE_DEFAULT_MODEL,
        "updated_at": agora_utc_naive(),
    })
    db.session.commit()

    logger.debug(f"[MEMORY_MCP] Sync dedup embed salvo para {path}")


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


def _classify_memory_category(path: str, content: str) -> str:
    """
    Classifica memória em categoria por heurística.

    Memory System v2: classificação automática zero-custo (<1ms).
    Agent pode override via parâmetro opcional no save_memory.

    Regras (ordem de prioridade):
    1. Path = user.xml ou preferences.xml → permanent
    2. Path /corrections/ + keywords de escopo → permanent
    3. Path /corrections/ + keywords estruturais → structural
    4. Path /corrections/ (demais) → structural
    5. Path /context/ → contextual
    6. Default → operational

    Args:
        path: Path da memória
        content: Conteúdo da memória

    Returns:
        category (str): permanent, structural, operational, contextual
    """
    path_lower = path.lower() if path else ''
    content_lower = content.lower() if content else ''

    # user.xml e preferences.xml → permanent
    if path_lower in ('/memories/user.xml', '/memories/preferences.xml'):
        return 'permanent'

    # corrections/ com keywords de escopo/permanência → permanent
    if '/corrections/' in path_lower:
        permanent_keywords = [
            'scope', 'escopo', 'permiss', 'regra', 'proibido',
            'obrigat', 'nunca fazer', 'sempre fazer', 'nunca use',
            'nunca usar', 'identidade', 'papel', 'role',
        ]
        if any(kw in content_lower for kw in permanent_keywords):
            return 'permanent'

        # corrections/ com keywords estruturais → structural
        structural_keywords = [
            'timeout', 'campo', 'fk', 'constraint', 'empresa',
            'odoo', 'nao existe', 'não existe', 'tabela', 'coluna',
            'modelo', 'api', 'endpoint', 'migration', 'index',
        ]
        if any(kw in content_lower for kw in structural_keywords):
            return 'structural'

        # corrections/ (demais) → structural por default
        return 'structural'

    # context/ → contextual
    if '/context/' in path_lower:
        return 'contextual'

    # learned/patterns → operational
    # Default → operational
    return 'operational'


def _detect_pitfall_hint(path: str, content: str) -> Optional[str]:
    """
    Detecta se uma correção salva parece ser um system pitfall (gotcha do ambiente).

    Diferença:
    - Correction: "eu errei, o campo certo é X" (erro do agent)
    - Pitfall: "o journal_id é 68, não 47" (armadilha do sistema)

    Heurística: keywords que indicam gotcha de sistema, não erro de raciocínio.

    Returns:
        Hint string para appendar na resposta, ou None.
    """
    if '/corrections/' not in path.lower():
        return None

    content_lower = content.lower()

    # Keywords que indicam gotcha de sistema (não erro do agent)
    system_keywords = [
        # IDs/configurações erradas
        'id deve ser', 'id é', 'id correto', 'id errado',
        'journal_id', 'account_id', 'company_id', 'partner_id',
        # Comportamento inesperado de APIs/sistemas
        'não funciona via', 'não expõe', 'não suporta',
        'retorna erro', 'retorna 4', 'retorna 5',
        'timeout', 'rate limit',
        # Campos/tabelas com comportamento não-óbvio
        'campo não recalcula', 'campo stale', 'não atualiza',
        'precisa de playwright', 'precisa de xml-rpc',
        'só funciona via', 'só recalcula',
        # Ordem obrigatória de operações
        'antes de', 'deve ser último', 'deve ser primeiro',
        'ordem obrigatória', 'desfaz a reconciliação',
        # Valores fixos/hardcoded
        'valor fixo', 'hardcoded', 'id fixo',
    ]

    hit_count = sum(1 for kw in system_keywords if kw in content_lower)

    if hit_count >= 2:
        # Tentar extrair a área do conteúdo
        area_hints = {
            'odoo': ['odoo', 'journal', 'account_id', 'xml-rpc', 'invoice', 'payment'],
            'ssw': ['ssw', 'opcao', 'cadastr', 'comissao', '401', '402', '408', '478', '485'],
            'banco': ['tabela', 'coluna', 'index', 'migration', 'constraint', 'trigger'],
            'api': ['api', 'endpoint', 'rate limit', 'timeout', 'webhook'],
            'deploy': ['render', 'deploy', 'env var', 'worker', 'scheduler'],
        }
        detected_area = 'sistema'
        for area, keywords in area_hints.items():
            if any(kw in content_lower for kw in keywords):
                detected_area = area
                break

        return (
            f'\n\nDica: esta correção parece ser um SYSTEM PITFALL (gotcha do ambiente, '
            f'não erro seu). Considere chamar log_system_pitfall(area="{detected_area}", '
            f'description="...") para registrá-lo separadamente — pitfalls ficam visíveis '
            f'em todas as sessões futuras.'
        )

    return None


def _regenerate_pitfalls_xml(user_id: int, pitfalls: list) -> None:
    """
    Regenera /memories/empresa/armadilhas/system-pitfalls.xml a partir da lista JSON.

    O XML é o formato injetado no contexto do agente (tier 1 como structural memory).
    O JSON é a fonte de verdade (editável via tool).

    Args:
        user_id: ID do usuário (0 para empresa)
        pitfalls: Lista de dicts com area, description, hit_count, etc
    """
    try:
        from app.agente.models import AgentMemory
        from app.utils.timezone import agora_utc_naive

        path = '/memories/empresa/armadilhas/system-pitfalls.xml'
        now = agora_utc_naive().strftime('%d/%m/%Y %H:%M')

        # Agrupar por área
        by_area: dict[str, list] = {}
        for p in pitfalls:
            area = p.get('area', 'geral')
            by_area.setdefault(area, []).append(p)

        lines = [f'<system_pitfalls updated_at="{now}" count="{len(pitfalls)}">']
        for area, items in sorted(by_area.items()):
            lines.append(f'  <area name="{area}">')
            for item in items:
                desc = item.get('description', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                hits = item.get('hit_count', 1)
                lines.append(f'    <pitfall hits="{hits}">{desc}</pitfall>')
            lines.append(f'  </area>')
        lines.append('</system_pitfalls>')

        content = '\n'.join(lines)

        existing = AgentMemory.get_by_path(user_id, path)
        if existing:
            existing.content = content
        else:
            mem = AgentMemory.create_file(user_id, path, content)
            mem.category = 'structural'
            mem.escopo = 'empresa'
    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Erro ao regenerar pitfalls XML (ignorado): {e}")


def _check_memory_duplicate(user_id: int, content: str, current_path: str = '') -> Optional[str]:
    """
    Verifica se ja existe memoria semanticamente similar para o usuario.

    Duas camadas de detecção:
    - Layer 0 (text overlap): Comparação textual por overlap coefficient de
      palavras normalizadas (sem acentos, >3 chars, sem stopwords). Zero custo
      de API. Threshold: 0.65. Captura duplicatas óbvias com wording diferente.
    - Layer 1 (dedup_embedding): Busca contra coluna dedup_embedding que armazena
      embedding do texto limpo (sem contexto Sonnet, sem path, sem XML).
      Threshold: 0.85. Ambos os lados na mesma representação — sem lacuna.
      Fallback para embedding contextual (threshold 0.70) se dedup_embedding
      ainda não foi populado (registros pré-migration).

    Args:
        user_id: ID do usuario
        content: Conteudo da nova memoria (pode conter tags XML)
        current_path: Path sendo atualizado (excluido da busca)

    Returns:
        Path da memoria duplicata ou None se nao houver duplicata
    """
    from ..services.knowledge_graph_service import clean_for_comparison

    clean_content = clean_for_comparison(content)

    # ── Layer 0: Text overlap (fast, free) ──
    try:
        text_dup = _text_overlap_check(user_id, clean_content, current_path)
        if text_dup:
            return text_dup
    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Text overlap check falhou (ignorado): {e}")

    # ── Layer 1: Dedup embedding (threshold 0.85, mesma representação) ──
    try:
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
        if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
            return None

        dup = _dedup_embedding_search(user_id, clean_content, current_path)
        if dup:
            return dup

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Dedup embedding check falhou (ignorado): {e}")

    return None


def _dedup_embedding_search(
    user_id: int, clean_content: str, current_path: str
) -> Optional[str]:
    """
    Layer 1: Busca contra dedup_embedding (texto limpo, mesma representação).

    Query e embedding armazenado estão na mesma representação (clean_for_comparison),
    eliminando a lacuna que causava falsos negativos (sim 0.66-0.78 no embedding
    contextualizado quando o threshold era 0.85).

    Fallback: se dedup_embedding não existe (registros pré-migration), usa
    embedding contextualizado com threshold mais baixo (0.70).
    """
    from app.embeddings.service import EmbeddingService
    from app import db
    from sqlalchemy import text

    svc = EmbeddingService()
    # DEDUP: usar input_type="document" (mesmo tipo do armazenado)
    # embed_query() usa input_type="query" — cria representação assimétrica
    # que reduz similaridade em ~0.07-0.15 pontos (Voyage AI asymmetric search)
    try:
        query_embedding = svc.embed_texts([clean_content], input_type="document")[0]
    except Exception as e:
        from app.embeddings.client import EmbeddingUnavailableError
        if isinstance(e, EmbeddingUnavailableError):
            logger.warning(f"[dedup_search] Voyage indisponivel, pulando dedup: {e}")
            return None
        raise
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Incluir user_id=0 (memórias empresa) para memória compartilhada
    user_ids = [user_id, 0] if user_id != 0 else [0]

    # Habilitar iterative_scan (pgvector 0.8.0+)
    svc._enable_iterative_scan()

    # Buscar primeiro contra dedup_embedding (threshold 0.85)
    result = db.session.execute(text("""
        SELECT
            path,
            1 - (dedup_embedding <=> CAST(:query AS vector)) AS similarity
        FROM agent_memory_embeddings
        WHERE user_id = ANY(:user_ids)
          AND dedup_embedding IS NOT NULL
          AND path != :current_path
        ORDER BY dedup_embedding <=> CAST(:query AS vector)
        LIMIT 3
    """), {
        "query": embedding_str,
        "user_ids": user_ids,
        "current_path": current_path or '',
    })

    for row in result.fetchall():
        similarity = float(row.similarity)
        if similarity >= 0.85:
            logger.info(
                f"[MEMORY_MCP] Duplicata detectada (dedup_embedding): "
                f"{current_path} ~ {row.path} (sim={similarity:.3f})"
            )
            return row.path

    # Fallback: registros sem dedup_embedding (pré-migration)
    # Usa embedding contextualizado com threshold mais baixo
    result_fallback = db.session.execute(text("""
        SELECT
            path,
            1 - (embedding <=> CAST(:query AS vector)) AS similarity
        FROM agent_memory_embeddings
        WHERE user_id = ANY(:user_ids)
          AND embedding IS NOT NULL
          AND dedup_embedding IS NULL
          AND path != :current_path
        ORDER BY embedding <=> CAST(:query AS vector)
        LIMIT 3
    """), {
        "query": embedding_str,
        "user_ids": user_ids,
        "current_path": current_path or '',
    })

    for row in result_fallback.fetchall():
        similarity = float(row.similarity)
        if similarity >= 0.70:
            logger.info(
                f"[MEMORY_MCP] Duplicata detectada (embedding fallback): "
                f"{current_path} ~ {row.path} (sim={similarity:.3f})"
            )
            return row.path

    return None


# Stopwords PT-BR para Layer 0 (text overlap).
# Palavras funcionais que não carregam significado semântico discriminante.
_DEDUP_STOPWORDS = frozenset({
    'para', 'como', 'todo', 'toda', 'pela', 'pelo', 'mais', 'esta',
    'esse', 'essa', 'isso', 'isto', 'aqui', 'seus', 'suas', 'dele',
    'dela', 'nosso', 'nossa', 'voce', 'eles', 'elas', 'cada', 'qual',
    'quais', 'onde', 'quando', 'porque', 'muito', 'pouco', 'outro',
    'outra', 'mesmo', 'mesma', 'ainda', 'apos', 'antes', 'sobre',
    'entre', 'desde', 'deve', 'pode', 'sido', 'sera', 'seria',
    'todas', 'todos', 'algumas', 'alguns', 'estas', 'estes',
    'com', 'que', 'dos', 'das', 'nos', 'nas', 'uma',
})


def _canonicalize_for_dedup(content: str) -> str:
    """
    Normaliza conteudo para forma canonica ANTES do embedding de dedup.

    Strip XML tags + decodifica entidades → texto puro. Voyage AI embeddings
    capturam similaridade semantica sem normalizacao adicional.
    """
    from ..services.knowledge_graph_service import clean_for_comparison
    return clean_for_comparison(content)


def _normalize_words_for_dedup(text: str) -> set:
    """
    Normaliza texto para set de palavras significativas.
    Remove acentos, filtra stopwords e palavras curtas (<=3 chars).
    """
    import re
    import unicodedata

    nfkd = unicodedata.normalize('NFKD', text.lower())
    ascii_text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return set(
        w for w in re.findall(r'\w+', ascii_text)
        if len(w) > 3 and w not in _DEDUP_STOPWORDS
    )


def _text_overlap_check(
    user_id: int, clean_content: str, current_path: str
) -> Optional[str]:
    """
    Layer 0: Text-level duplicate check usando overlap coefficient.

    Overlap coefficient = |A ∩ B| / min(|A|, |B|).
    Mais robusto que Jaccard para memórias de tamanhos diferentes
    (ex: uma memória é versão resumida da outra).

    Threshold: 0.65 (65% de overlap).
    Zero custo de API — apenas comparação textual contra memórias do banco.

    Diagnosticado em 2026-03-09: overlap coefficient para duplicatas conhecidas:
    - "Atacadão pede NF completa" vs "Atacadão exige NF completa": ~0.75
    - "Dry-run lote Odoo" vs "Dry-run obrigatório Odoo": ~0.83
    """
    from ..models import AgentMemory
    from ..services.knowledge_graph_service import clean_for_comparison

    words_new = _normalize_words_for_dedup(clean_content)
    if len(words_new) < 3:
        return None  # Conteúdo muito curto para comparação

    def _check():
        # Incluir memórias empresa (user_id=0) na busca
        user_ids = [user_id, 0] if user_id != 0 else [0]
        memories = AgentMemory.query.filter(
            AgentMemory.user_id.in_(user_ids),
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.path != current_path,
        ).with_entities(AgentMemory.path, AgentMemory.content).all()

        for mem_path, mem_content in memories:
            mem_clean = clean_for_comparison(mem_content or '')
            words_existing = _normalize_words_for_dedup(mem_clean)

            if len(words_existing) < 3:
                continue

            # Overlap coefficient: intersection / min(|A|, |B|)
            intersection = len(words_new & words_existing)
            min_size = min(len(words_new), len(words_existing))

            if min_size > 0 and intersection / min_size >= 0.65:
                overlap_ratio = intersection / min_size
                logger.info(
                    f"[MEMORY_MCP] Duplicata detectada (text overlap): "
                    f"{current_path} ~ {mem_path} "
                    f"(overlap={intersection}/{min_size}={overlap_ratio:.2f})"
                )
                return mem_path

        return None

    return _execute_with_context(_check)


def _track_correction_feedback(user_id: int, correction_path: str, correction_content: str) -> None:
    """
    Memory v2 — Feedback Loop: quando uma correção é salva,
    incrementa correction_count nas memórias recentemente injetadas.

    Lógica: se o Agent acabou de salvar uma correção, algo nas memórias
    existentes pode estar errado. Incrementamos correction_count nas
    memórias que foram injetadas nos últimos 30 minutos (sessão ativa).

    Best-effort: falhas silenciosas.
    """
    try:
        from ..models import AgentMemory
        from app import db
        from sqlalchemy import text as sql_text
        from app.utils.timezone import agora_utc_naive
        from datetime import timedelta

        now = agora_utc_naive()
        cutoff = now - timedelta(minutes=30)

        # Buscar memórias injetadas recentemente (mesmo turno) que NÃO são a correção atual
        # Inclui user_id=0 (empresa) — memórias compartilhadas são injetadas em todos os contextos
        recent = AgentMemory.query.filter(
            AgentMemory.user_id.in_([user_id, 0]),
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.last_accessed_at >= cutoff,
            AgentMemory.usage_count > 0,
            AgentMemory.path != correction_path,
        ).all()

        if not recent:
            return

        # Incrementar correction_count apenas nas que têm conteúdo relacionado
        from ..services.knowledge_graph_service import clean_for_comparison
        correction_lower = clean_for_comparison(correction_content).lower()
        related_ids = []
        for mem in recent:
            mem_content = clean_for_comparison(mem.content or '').lower()
            # Checar overlap: pelo menos 2 termos significativos em comum
            # (palavras >4 chars, excluindo genéricas que matcham quase tudo)
            _generic = {'pedido', 'campo', 'valor', 'odoo', 'tabela', 'dados',
                        'sistema', 'modelo', 'sempre', 'nunca', 'quando', 'existe'}
            mem_words = set(w for w in mem_content.split() if len(w) > 4 and w not in _generic)
            corr_words = set(w for w in correction_lower.split() if len(w) > 4 and w not in _generic)
            overlap = mem_words & corr_words
            if len(overlap) >= 2:  # Mínimo 2 termos para reduzir falsos positivos
                related_ids.append(mem.id)

        if related_ids:
            db.session.execute(sql_text("""
                UPDATE agent_memories
                SET correction_count = correction_count + 1
                WHERE id = ANY(:ids)
            """), {"ids": related_ids})
            db.session.commit()
            logger.info(
                f"[MEMORY_FEEDBACK] correction_count incremented for {len(related_ids)} memories "
                f"(correction={correction_path})"
            )

    except Exception as e:
        logger.debug(f"[MEMORY_FEEDBACK] Correction tracking falhou (ignorado): {e}")


def _detect_conflicts_async(user_id: int, new_path: str, new_content: str) -> None:
    """
    Memory v2 — Detecção de contradições (assíncrona/best-effort).

    Após salvar, busca memórias semanticamente similares (cosine 0.50-0.85
    no embedding contextualizado) no mesmo domínio (parent path).
    Se encontrar com entidades em comum, marca a NOVA memória com
    has_potential_conflict=True.

    NOTA: Usa embedding contextualizado (não dedup_embedding) porque queremos
    capturar memórias RELACIONADAS (mesmo tema, info diferente), não duplicatas.
    Duplicatas são detectadas pelo _check_memory_duplicate via dedup_embedding.

    O alerta aparece na PRÓXIMA injeção (não bloqueia o save atual).
    """
    try:
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
        if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
            return

        from app.embeddings.service import EmbeddingService
        from ..models import AgentMemory
        from app import db

        svc = EmbeddingService()
        results = svc.search_memories(
            new_content, user_id=user_id, limit=5, min_similarity=0.50
        )

        if not results:
            return

        # Extrair parent path para filtrar mesmo domínio
        parent = new_path.rsplit('/', 1)[0] if '/' in new_path else ''

        conflicts_found = False
        for r in results:
            r_path = r.get('path', '')
            similarity = r.get('similarity', 0)

            # Excluir self-match e duplicatas (>0.85 no dedup_embedding)
            if r_path == new_path or similarity >= 0.85:
                continue

            # Faixa de conflito: similar o suficiente para ser relacionado,
            # mas diferente o suficiente para potencialmente contradizer
            if 0.50 <= similarity < 0.85:
                # Verificar se está no mesmo domínio (parent path)
                r_parent = r_path.rsplit('/', 1)[0] if '/' in r_path else ''
                if r_parent == parent or parent in r_parent or r_parent in parent:
                    conflicts_found = True
                    logger.info(
                        f"[MEMORY_CONFLICT] Potencial contradição detectada: "
                        f"'{new_path}' vs '{r_path}' (sim={similarity:.3f})"
                    )
                    break

        if conflicts_found:
            # Marcar a nova memória com flag de conflito
            mem = AgentMemory.get_by_path(user_id, new_path)
            if mem:
                mem.has_potential_conflict = True
                db.session.commit()

    except Exception as e:
        logger.debug(f"[MEMORY_CONFLICT] Detection falhou (ignorado): {e}")


# =====================================================================
# OUTPUT SCHEMAS (Enhanced MCP — structuredContent)
# =====================================================================

MEMORY_VIEW_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "is_directory": {"type": "boolean"},
        "content": {"type": ["string", "null"]},
        "items": {
            "type": ["array", "null"],
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "is_dir": {"type": "boolean"},
                },
            },
        },
    },
    "required": ["path", "is_directory"],
}

MEMORY_SAVE_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "action": {"type": "string", "enum": ["criado", "atualizado", "duplicate_blocked"]},
        "category": {"type": ["string", "null"]},
        "importance": {"type": ["number", "null"]},
    },
    "required": ["path", "action"],
}

MEMORY_UPDATE_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "updated": {"type": "boolean"},
    },
    "required": ["path", "updated"],
}

MEMORY_DELETE_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "type": {"type": "string", "enum": ["file", "directory"]},
        "count": {"type": "integer"},
    },
    "required": ["path", "type", "count"],
}

MEMORY_LIST_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "memories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "preview": {"type": "string"},
                },
            },
        },
    },
    "required": ["count", "memories"],
}

MEMORY_CLEAR_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
    },
    "required": ["count"],
}

MEMORY_SEARCH_COLD_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "usage_count": {"type": "integer"},
                    "effective_count": {"type": "integer"},
                    "content_preview": {"type": "string"},
                },
            },
        },
    },
    "required": ["count", "results"],
}

MEMORY_HISTORY_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "version_count": {"type": "integer"},
        "versions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "version": {"type": "integer"},
                    "changed_at": {"type": ["string", "null"]},
                    "changed_by": {"type": ["string", "null"]},
                    "preview": {"type": "string"},
                },
            },
        },
    },
    "required": ["path", "version_count", "versions"],
}

MEMORY_RESTORE_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "restored_to_version": {"type": "integer"},
        "backup_version": {"type": ["integer", "null"]},
        "preview": {"type": ["string", "null"]},
    },
    "required": ["path", "restored_to_version"],
}

MEMORY_RESOLVE_PENDENCIA_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "total_resolved": {"type": "integer"},
    },
    "required": ["description", "total_resolved"],
}

MEMORY_LOG_PITFALL_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "area": {"type": "string"},
        "description": {"type": "string"},
        "total_pitfalls": {"type": "integer"},
        "is_update": {"type": "boolean"},
    },
    "required": ["area", "description", "total_pitfalls", "is_update"],
}

MEMORY_REGISTER_IMPROVEMENT_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "suggestion_key": {"type": "string"},
        "category": {"type": "string"},
        "severity": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "string"},
    },
    "required": ["suggestion_key", "category", "severity", "title", "status"],
}

# =====================================================================
# CUSTOM TOOLS — Enhanced MCP v2.0.0
# =====================================================================

try:
    from claude_agent_sdk import ToolAnnotations
    from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

    @enhanced_tool(
        "view_memories",
        "OBRIGATÓRIO no início de cada sessão: visualiza memórias persistentes do usuário. "
        "Consulte ANTES de responder a primeira mensagem para recuperar preferências, "
        "correções e contexto de sessões anteriores. "
        "Use path='/memories' para listar diretórios. "
        "Use path='/memories/user.xml' para ver arquivo específico. "
        "Esta ferramenta é sua ÚNICA fonte de contexto cross-session.",
        {"path": Annotated[str, "Path da memoria a visualizar. Raiz: /memories. Subdiretorios: user.xml, preferences.xml, corrections/, empresa/. Use /memories para listar tudo"]},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_VIEW_OUTPUT_SCHEMA,
    )
    async def view_memories(args: dict[str, Any]) -> dict[str, Any]:
        """
        Visualiza memória ou lista diretório.

        Args:
            args: {"path": str, "target_user_id": int (opcional, requer debug mode)}

        Returns:
            MCP tool response com conteúdo ou listagem
        """
        path = args.get("path", "/memories").strip()

        try:
            path = _validate_path(path)
            user_id = _resolve_user_id(args)
            actual_user_id = _resolve_empresa_user_id(user_id, path)

            def _view():
                from ..models import AgentMemory

                memory = AgentMemory.get_by_path(actual_user_id, path)

                # Caso especial: /memories é diretório virtual raiz
                if path == '/memories':
                    items = AgentMemory.list_directory(actual_user_id, path)
                    if not items:
                        text = "Diretório: /memories\n(vazio — nenhuma memória salva)"
                        return text, {"path": path, "is_directory": True, "content": None, "items": []}

                    lines = ["Diretório: /memories"]
                    structured_items = []
                    for item in sorted(items, key=lambda x: x.path):
                        name = item.path.split('/')[-1]
                        suffix = '/' if item.is_directory else ''
                        lines.append(f"- {name}{suffix}")
                        structured_items.append({"name": name, "is_dir": item.is_directory})
                    text = "\n".join(lines)
                    return text, {"path": path, "is_directory": True, "content": None, "items": structured_items}

                if not memory:
                    text = f"Path não encontrado: {path}"
                    return text, {"path": path, "is_directory": False, "content": None, "items": None}

                # Se diretório, lista conteúdo
                if memory.is_directory:
                    items = AgentMemory.list_directory(actual_user_id, path)
                    if not items:
                        text = f"Diretório: {path}\n(vazio)"
                        return text, {"path": path, "is_directory": True, "content": None, "items": []}

                    lines = [f"Diretório: {path}"]
                    structured_items = []
                    for item in sorted(items, key=lambda x: x.path):
                        name = item.path.split('/')[-1]
                        suffix = '/' if item.is_directory else ''
                        lines.append(f"- {name}{suffix}")
                        structured_items.append({"name": name, "is_dir": item.is_directory})
                    text = "\n".join(lines)
                    return text, {"path": path, "is_directory": True, "content": None, "items": structured_items}

                # Arquivo: retorna conteúdo
                content = memory.content or "(vazio)"
                text = f"Arquivo: {path}\n\n{content}"
                return text, {"path": path, "is_directory": False, "content": content, "items": None}

            result_text, structured = _execute_with_context(_view)
            logger.info(f"[MEMORY_MCP] view_memories: {path}")
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }

        except Exception as e:
            error_msg = f"Erro ao visualizar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
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
        {"path": Annotated[str, "Path completo onde salvar (ex: /memories/user.xml, /memories/corrections/regra_frete.md, /memories/empresa/termos/palmito.md)"], "content": Annotated[str, "Conteudo da memoria em formato texto ou XML. Para user.xml e preferences.xml, usar formato XML existente"]},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_SAVE_OUTPUT_SCHEMA,
    )
    async def save_memory(args: dict[str, Any]) -> dict[str, Any]:
        """
        Cria ou atualiza memória.

        Args:
            args: {"path": str, "content": str, "category": str (optional)}

        category pode ser: permanent, structural, operational, contextual.
        Se não informado, classificação automática por heurística de path + content.

        Returns:
            MCP tool response com confirmação
        """
        path = args.get("path", "").strip()
        content = args.get("content", "").strip()
        category_override = args.get("category", "").strip().lower() or None

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
            user_id = _resolve_user_id(args)

            # PRD v2.1: Classificar escopo pelo path
            # Paths /memories/empresa/* sao memorias compartilhadas (user_id=0)
            actual_user_id = _resolve_empresa_user_id(user_id, path)
            escopo = 'empresa' if actual_user_id == 0 else 'pessoal'
            created_by_id = user_id if escopo == 'empresa' else None

            def _save():
                from ..models import AgentMemory, AgentMemoryVersion
                from app import db
                from app.utils.timezone import agora_utc_naive

                # Calcular importance score heurístico (QW-1)
                importance = _calculate_importance_score(path, content)

                # Memory v2: classificar categoria (heurística ou override)
                valid_categories = {'permanent', 'structural', 'operational', 'contextual'}
                if category_override and category_override in valid_categories:
                    category = category_override
                else:
                    category = _classify_memory_category(path, content)

                existing = AgentMemory.get_by_path(actual_user_id, path)

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
                    existing.category = category
                    existing.last_accessed_at = agora_utc_naive()
                    # Se salvando novo conteúdo, limpar flag de conflito
                    existing.has_potential_conflict = False
                    # PRD v2.1: atualizar escopo e created_by
                    existing.escopo = escopo
                    if created_by_id:
                        existing.created_by = created_by_id
                    action = "atualizado"
                else:
                    # Dedup gate ANTES do commit (Bug 1+2 fix):
                    # Verificar duplicata ANTES de criar — se detectar, raise em vez de salvar.
                    # Defensive: falha no dedup NÃO deve impedir o save (best-effort gate).
                    # user_id (NÃO actual_user_id) para cross-namespace dedup:
                    # Se empresa (actual=0), user_id original garante check [user, 0]
                    # em vez de [0] — detecta duplicata pessoal↔empresa.
                    try:
                        dup_path = _check_memory_duplicate(
                            user_id, content, current_path=path
                        )
                        if dup_path:
                            raise DuplicateMemoryError(dup_path)
                    except DuplicateMemoryError:
                        raise  # Propagar — este É o gate
                    except Exception as dedup_gate_err:
                        logger.debug(
                            f"[MEMORY_MCP] Dedup gate check failed "
                            f"(allowing save): {dedup_gate_err}"
                        )

                    mem = AgentMemory.create_file(actual_user_id, path, content)
                    mem.importance_score = importance
                    mem.category = category
                    mem.last_accessed_at = agora_utc_naive()
                    # PRD v2.1: escopo e created_by
                    mem.escopo = escopo
                    if created_by_id:
                        mem.created_by = created_by_id
                    action = "criado"

                db.session.commit()
                return action

            try:
                action = _execute_with_context(_save)
            except DuplicateMemoryError as dup_err:
                logger.info(
                    f"[MEMORY_MCP] Dedup gate blocked: {path} ~ {dup_err.dup_path}"
                )
                return {
                    "content": [{
                        "type": "text",
                        "text": (
                            f"Memoria NAO salva: conteudo similar ja existe em "
                            f"'{dup_err.dup_path}'. Use update_memory para atualizar "
                            f"o conteudo existente, ou altere significativamente o conteudo."
                        ),
                    }],
                    "structuredContent": {
                        "path": path,
                        "action": "duplicate_blocked",
                        "category": None,
                        "importance": None,
                    },
                }

            logger.info(f"[MEMORY_MCP] save_memory: {path} ({action})")

            # Sync dedup embed: garante que próximos saves detectem esta memória
            # via Layer 1 (elimina race condition do Bug 3 — daemon thread assíncrono)
            if action == "criado":
                try:
                    _execute_with_context(
                        lambda: _save_dedup_embedding_only(actual_user_id, path, content)
                    )
                except Exception as sync_emb_err:
                    logger.debug(
                        f"[MEMORY_MCP] Sync dedup embed failed (ignorado): {sync_emb_err}"
                    )

            # Best-effort: consolidacao + tier frio
            # Consolidacao Sonnet: apenas pessoal (user_id > 0)
            # Cold move: pessoal + empresa (eficacia < threshold)
            # GC: remove memorias cold > 90 dias (MEMORY_PROTOCOL.md)
            try:
                from ..services.memory_consolidator import maybe_consolidate, maybe_move_to_cold, maybe_gc_cold_memories
                _consolidate_user_id = actual_user_id
                
                def _consolidate_cold_gc():
                    if _consolidate_user_id != 0:
                        maybe_consolidate(_consolidate_user_id)
                    maybe_move_to_cold(_consolidate_user_id)
                    maybe_gc_cold_memories(_consolidate_user_id)
                _execute_with_context(_consolidate_cold_gc)
            except Exception as consolidation_err:
                logger.debug(
                    f"[MEMORY_MCP] Consolidação/cold/gc não executada (ignorado): {consolidation_err}"
                )

            # Best-effort: cleanup empresa (user_id=0) — redundancia se save ja era empresa
            try:
                from ..services.memory_consolidator import maybe_cleanup_low_value
                _execute_with_context(maybe_cleanup_low_value)
            except Exception as cleanup_err:
                logger.debug(
                    f"[MEMORY_MCP] Cleanup empresa não executado (ignorado): {cleanup_err}"
                )

            # Best-effort: embeddar memória + KG em daemon thread (não bloqueia retorno)
            # Sonnet gera tags contextuais mais ricas que Haiku, mas latência maior.
            # Background thread elimina impacto na UX do save_memory.
            def _bg_embed_and_kg():
                try:
                    _entities = []
                    _relations = []
                    try:
                        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH
                        if MEMORY_SEMANTIC_SEARCH:
                            _entities, _relations = _embed_memory_best_effort(
                                actual_user_id, path, content
                            )
                    except Exception as emb_err:
                        logger.warning(f"[MEMORY_MCP] Embedding falhou (ignorado): {emb_err}")

                    try:
                        from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
                        if MEMORY_KNOWLEDGE_GRAPH:
                            def _kg_extract():
                                from ..models import AgentMemory
                                from ..services.knowledge_graph_service import extract_and_link_entities
                                mem = AgentMemory.get_by_path(actual_user_id, path)
                                if mem:
                                    extract_and_link_entities(
                                        actual_user_id, mem.id, content,
                                        haiku_entities=_entities,
                                        haiku_relations=_relations,
                                    )

                            _execute_with_context(_kg_extract)
                    except Exception as kg_err:
                        logger.warning(f"[MEMORY_MCP] Knowledge Graph falhou (ignorado): {kg_err}")
                except Exception as e:
                    logger.warning(f"[MEMORY_MCP] Background embed+KG falhou: {e}")

            from threading import Thread
            Thread(target=_bg_embed_and_kg, daemon=True).start()

            # Best-effort: Memory v2 — Feedback Loop: se é uma correção,
            # incrementar correction_count nas memórias recentemente injetadas
            # (indica que memórias existentes podem estar incorretas/incompletas)
            try:
                _is_correction_path = (
                    '/corrections/' in path.lower()
                    or '/correcoes/' in path.lower()
                )
                # Keywords de correção — exigir 2+ matches para reduzir falsos positivos
                # (ex: "na verdade" sozinho é conversação normal, mas "na verdade, o correto é" indica correção)
                _correction_keywords = [
                    'correto é', 'correto e', 'na verdade', 'errado',
                    'não é', 'nao e', 'correção', 'correcao', 'corrigir',
                ]
                _content_lower = (content or '').lower()
                _keyword_hits = sum(1 for kw in _correction_keywords if kw in _content_lower)
                _is_correction_content = _keyword_hits >= 2  # Mínimo 2 keywords
                if _is_correction_path or _is_correction_content:
                    _track_correction_feedback(user_id, path, content)
            except Exception as fb_err:
                logger.debug(f"[MEMORY_MCP] Correction feedback falhou (ignorado): {fb_err}")

            # Best-effort: Memory v2 — Conflict Detection (assíncrono)
            # Busca memórias semanticamente similares no mesmo domínio
            # Se encontrar potencial contradição, marca has_potential_conflict=True
            try:
                _detect_conflicts_async(user_id, path, content)
            except Exception as conflict_err:
                logger.debug(f"[MEMORY_MCP] Conflict detection falhou (ignorado): {conflict_err}")

            # Best-effort: Pitfall nudge — se correção parece system pitfall,
            # sugere ao Agent chamar log_system_pitfall()
            pitfall_hint = ''
            try:
                pitfall_hint = _detect_pitfall_hint(path, content) or ''
            except Exception:
                pass

            return {
                "content": [{"type": "text", "text": f"Memória {action} em {path}{pitfall_hint}"}],
                "structuredContent": {
                    "path": path,
                    "action": action,
                    "category": None,
                    "importance": None,
                },
            }

        except Exception as e:
            error_msg = f"Erro ao salvar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "update_memory",
        "Substitui um trecho de texto em um arquivo de memória existente. "
        "O old_str deve ser encontrado exatamente UMA vez no arquivo. "
        "Use para atualizar informações específicas sem reescrever o arquivo inteiro.",
        {"path": Annotated[str, "Path da memoria a atualizar"], "old_str": Annotated[str, "Texto EXATO a substituir (deve aparecer exatamente uma vez no conteudo atual)"], "new_str": Annotated[str, "Novo texto para substituir old_str (pode ser string vazia para deletar trecho)"]},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_UPDATE_OUTPUT_SCHEMA,
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
        old_str = args.get("old_str", "").strip()
        new_str = args.get("new_str", "")

        if not path or not old_str:
            return {
                "content": [{"type": "text", "text": "Erro: path e old_str são obrigatórios"}],
                "is_error": True,
            }

        try:
            path = _validate_path(path)
            new_str = _sanitize_content(new_str)
            user_id = _resolve_user_id(args)
            actual_user_id = _resolve_empresa_user_id(user_id, path)

            def _update():
                from ..models import AgentMemory, AgentMemoryVersion
                from app import db

                memory = AgentMemory.get_by_path(actual_user_id, path)
                if not memory:
                    raise FileNotFoundError(f"Arquivo não encontrado: {path}")
                if memory.is_directory:
                    raise ValueError(f"Não é possível editar diretório: {path}")

                content = memory.content or ""
                count = content.count(old_str)

                if count == 0:
                    preview = content[:3000] if len(content) > 3000 else content
                    truncated = " (truncado, conteúdo total tem {} chars)".format(len(content)) if len(content) > 3000 else ""
                    raise ValueError(
                        f"Texto não encontrado em {path}. "
                        f"Conteúdo atual{truncated}:\n\n{preview}"
                    )
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

            # Best-effort: re-embeddar memória + KG em daemon thread (não bloqueia retorno)
            def _bg_reembed_and_kg():
                try:
                    _entities = []
                    _relations = []
                    try:
                        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH
                        if MEMORY_SEMANTIC_SEARCH:
                            def _get_content():
                                from ..models import AgentMemory
                                mem = AgentMemory.get_by_path(actual_user_id, path)
                                return mem.content if mem else None

                            updated_content = _execute_with_context(_get_content)
                            if updated_content:
                                _entities, _relations = _embed_memory_best_effort(
                                    actual_user_id, path, updated_content
                                )
                    except Exception as emb_err:
                        logger.debug(f"[MEMORY_MCP] Embedding update falhou (ignorado): {emb_err}")

                    try:
                        from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
                        if MEMORY_KNOWLEDGE_GRAPH:
                            def _kg_update():
                                from ..models import AgentMemory
                                from ..services.knowledge_graph_service import (
                                    remove_memory_links,
                                    extract_and_link_entities,
                                )
                                mem = AgentMemory.get_by_path(actual_user_id, path)
                                if mem:
                                    remove_memory_links(mem.id)
                                    extract_and_link_entities(
                                        actual_user_id, mem.id, mem.content,
                                        haiku_entities=_entities,
                                        haiku_relations=_relations,
                                    )

                            _execute_with_context(_kg_update)
                    except Exception as kg_err:
                        logger.warning(f"[MEMORY_MCP] Knowledge Graph update falhou (ignorado): {kg_err}")
                except Exception as e:
                    logger.warning(f"[MEMORY_MCP] Background re-embed+KG falhou: {e}")

            from threading import Thread
            Thread(target=_bg_reembed_and_kg, daemon=True).start()

            return {
                "content": [{"type": "text", "text": f"Memória atualizada em {path}"}],
                "structuredContent": {"path": path, "updated": True},
            }

        except Exception as e:
            error_msg = f"Erro ao atualizar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "delete_memory",
        "Deleta um arquivo ou diretório de memória. "
        "Não é possível deletar o diretório raiz /memories.",
        {"path": Annotated[str, "Path da memoria ou diretorio a deletar permanentemente"]},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_DELETE_OUTPUT_SCHEMA,
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
            user_id = _resolve_user_id(args)
            actual_user_id = _resolve_empresa_user_id(user_id, path)

            if path == '/memories':
                return {
                    "content": [{"type": "text", "text": "Erro: não é possível deletar /memories raiz. Use clear_memories para limpar tudo."}],
                    "is_error": True,
                }

            def _delete():
                from ..models import AgentMemory
                from app import db
                from sqlalchemy import text as sql_text

                memory = AgentMemory.get_by_path(actual_user_id, path)
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
                            AgentMemory.user_id == actual_user_id,
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

                # T3-3: Cleanup explícito de links no Knowledge Graph
                try:
                    from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
                    if MEMORY_KNOWLEDGE_GRAPH and memory_ids:
                        from ..services.knowledge_graph_service import remove_memory_links
                        for mid in memory_ids:
                            remove_memory_links(mid)
                except Exception as kg_err:
                    logger.debug(f"[MEMORY_MCP] KG cleanup falhou (ignorado): {kg_err}")

                count = AgentMemory.delete_by_path(actual_user_id, path)
                db.session.commit()
                type_str = "directory" if tipo == "Diretório" else "file"
                text = f"{tipo} deletado: {path}" + (f" ({count} itens)" if count > 1 else "")
                return text, type_str, count

            result_text, type_str, count = _execute_with_context(_delete)
            logger.info(f"[MEMORY_MCP] delete_memory: {path}")
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": {"path": path, "type": type_str, "count": count},
            }

        except Exception as e:
            error_msg = f"Erro ao deletar {path}: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
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
        output_schema=MEMORY_LIST_OUTPUT_SCHEMA,
    )
    async def list_memories(args: dict[str, Any]) -> dict[str, Any]:
        """
        Lista todas as memórias do usuário.

        Args:
            args: {"target_user_id": int (opcional, requer debug mode)}

        Returns:
            MCP tool response com listagem
        """
        try:
            user_id = _resolve_user_id(args)

            def _list():
                from ..models import AgentMemory

                # Incluir memórias pessoais (user_id) E empresa (user_id=0)
                memories = AgentMemory.query.filter(
                    AgentMemory.user_id.in_([user_id, 0]),
                    AgentMemory.is_directory == False,  # noqa: E712
                ).order_by(AgentMemory.path).all()

                if not memories:
                    return "Nenhuma memória salva.", {"count": 0, "memories": []}

                lines = [f"Memórias do usuário ({len(memories)} arquivos):\n"]
                structured_memories = []
                for mem in memories:
                    content_preview = (mem.content or "")[:80]
                    if len(mem.content or "") > 80:
                        content_preview += "..."
                    lines.append(f"- {mem.path}: {content_preview}")
                    structured_memories.append({"path": mem.path, "preview": content_preview})

                text = "\n".join(lines)
                return text, {"count": len(memories), "memories": structured_memories}

            result_text, structured = _execute_with_context(_list)
            logger.info(f"[MEMORY_MCP] list_memories: user={user_id}")
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }

        except Exception as e:
            error_msg = f"Erro ao listar memórias: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
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
        output_schema=MEMORY_CLEAR_OUTPUT_SCHEMA,
    )
    async def clear_memories(args: dict[str, Any]) -> dict[str, Any]:
        """
        Limpa todas as memórias do usuário.

        Args:
            args: {"target_user_id": int (opcional, requer debug mode)}

        Returns:
            MCP tool response com confirmação
        """
        try:
            user_id = _resolve_user_id(args)

            def _clear():
                from ..models import AgentMemory
                from app import db

                count = AgentMemory.clear_all_for_user(user_id)
                db.session.commit()
                return count

            count = _execute_with_context(_clear)
            logger.info(f"[MEMORY_MCP] clear_memories: user={user_id}, count={count}")
            return {
                "content": [{"type": "text", "text": f"Todas as memórias limpas ({count} itens removidos)"}],
                "structuredContent": {"count": count},
            }

        except Exception as e:
            error_msg = f"Erro ao limpar memórias: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "search_cold_memories",
        "Busca no tier frio de memórias: memórias que foram automaticamente removidas da "
        "injeção por baixa efetividade (injetadas 20+ vezes sem nunca serem usadas na resposta). "
        "Use quando precisar consultar histórico de informações antigas que não aparecem mais "
        "no contexto automático. Busca por texto no conteúdo e path.",
        {"query": Annotated[str, "Texto para buscar no conteudo e path das memorias frias (arquivadas). Busca case-insensitive por substring"]},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_SEARCH_COLD_OUTPUT_SCHEMA,
    )
    async def search_cold_memories(args: dict[str, Any]) -> dict[str, Any]:
        """
        Busca memórias no tier frio (is_cold=True).

        Args:
            args: {"query": str, "target_user_id": int (opcional, requer debug mode)}

        Memory v2 — Fase 3B: memórias deprecadas são buscáveis mas não
        injetadas automaticamente no contexto.

        Args:
            args: {"query": str} — texto para buscar no conteúdo e path

        Returns:
            MCP tool response com memórias encontradas
        """
        query = args.get("query", "").strip()

        if not query:
            return {
                "content": [{"type": "text", "text": "Erro: query é obrigatório"}],
                "is_error": True,
            }

        try:
            user_id = _resolve_user_id(args)

            def _search_cold():
                from ..models import AgentMemory
                from app import db

                # Buscar memórias cold que contenham o query no conteúdo ou path
                # Incluir pessoais (user_id) E empresa (user_id=0)
                query_lower = f"%{query.lower()}%"
                cold_memories = AgentMemory.query.filter(
                    AgentMemory.user_id.in_([user_id, 0]),
                    AgentMemory.is_directory == False,  # noqa: E712
                    AgentMemory.is_cold == True,  # noqa: E712
                    db.or_(
                        AgentMemory.content.ilike(query_lower),
                        AgentMemory.path.ilike(query_lower),
                    ),
                ).order_by(
                    AgentMemory.updated_at.desc()
                ).limit(10).all()

                if not cold_memories:
                    text = f"Nenhuma memória fria encontrada para '{query}'."
                    return text, {"count": 0, "results": []}

                lines = [f"Memórias frias ({len(cold_memories)} resultados para '{query}'):\n"]
                structured_results = []
                for mem in cold_memories:
                    content_preview = (mem.content or "")[:200]
                    usage = getattr(mem, 'usage_count', 0) or 0
                    effective = getattr(mem, 'effective_count', 0) or 0
                    lines.append(
                        f"--- {mem.path} (uso={usage}, efetivo={effective}) ---\n"
                        f"{content_preview}"
                    )
                    if len(mem.content or "") > 200:
                        lines.append("...")
                    lines.append("")
                    structured_results.append({
                        "path": mem.path,
                        "usage_count": usage,
                        "effective_count": effective,
                        "content_preview": content_preview,
                    })

                text = "\n".join(lines)
                return text, {"count": len(cold_memories), "results": structured_results}

            result_text, structured = _execute_with_context(_search_cold)
            logger.info(f"[MEMORY_MCP] search_cold_memories: query='{query[:50]}'")
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }

        except Exception as e:
            error_msg = f"Erro ao buscar memórias frias: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "view_memory_history",
        "Consulta histórico de versões anteriores de uma memória. "
        "Use para ver quando e por quem a memória foi alterada, "
        "e o conteúdo de versões anteriores (preview de 200 chars). "
        "Útil para auditoria ou antes de restaurar uma versão antiga.",
        {"path": Annotated[str, "Path da memoria cujo historico de versoes sera consultado"], "limit": Annotated[int, "Maximo de versoes a retornar (1-20, default 5)"]},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_HISTORY_OUTPUT_SCHEMA,
    )
    async def view_memory_history(args: dict[str, Any]) -> dict[str, Any]:
        """
        Consulta histórico de versões de uma memória.

        Args:
            args: {
                "path": str — path da memória (ex: /memories/preferences.xml),
                "limit": int — máximo de versões (default 5, max 20),
                "target_user_id": int (opcional, requer debug mode)
            }

        Returns:
            MCP tool response com lista de versões
        """
        path = args.get("path", "").strip()

        if not path:
            return {
                "content": [{"type": "text", "text": "Erro: path é obrigatório"}],
                "is_error": True,
            }

        try:
            path = _validate_path(path)
            user_id = _resolve_user_id(args)
            actual_user_id = _resolve_empresa_user_id(user_id, path)
            limit = min(max(int(args.get("limit", 5)), 1), 20)

            def _view_history():
                from ..models import AgentMemory, AgentMemoryVersion

                memory = AgentMemory.get_by_path(actual_user_id, path)
                if not memory:
                    text = f"Memória não encontrada: {path}"
                    return None, text, {"path": path, "version_count": 0, "versions": []}

                versions = AgentMemoryVersion.get_versions(memory.id, limit)
                if not versions:
                    text = f"Nenhuma versão anterior para {path}. A memória existe mas nunca foi modificada."
                    return None, text, {"path": path, "version_count": 0, "versions": []}

                lines = [f"Histórico de {path} ({len(versions)} versão(ões)):\n"]
                structured_versions = []
                for v in versions:
                    changed_at = v.changed_at.strftime('%d/%m/%Y %H:%M') if v.changed_at else '?'
                    changed_by = v.changed_by or '?'
                    preview = (v.content or "")[:200]
                    if len(v.content or "") > 200:
                        preview += "..."
                    lines.append(
                        f"v{v.version} | {changed_at} | {changed_by}\n"
                        f"  Preview: {preview}\n"
                    )
                    structured_versions.append({
                        "version": v.version,
                        "changed_at": v.changed_at.isoformat() if v.changed_at else None,
                        "changed_by": v.changed_by,
                        "preview": preview,
                    })

                text = "\n".join(lines)
                return versions, text, {"path": path, "version_count": len(versions), "versions": structured_versions}

            versions, result_text, structured = _execute_with_context(_view_history)

            if versions is None:
                logger.info(f"[MEMORY_MCP] view_memory_history: path={path} — {result_text}")
                return {
                    "content": [{"type": "text", "text": result_text}],
                    "structuredContent": structured,
                }

            logger.info(
                f"[MEMORY_MCP] view_memory_history: path={path}, "
                f"versions={len(versions)}"
            )
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }

        except ValueError as e:
            return {"content": [{"type": "text", "text": f"Erro: {str(e)}"}], "is_error": True}
        except PermissionError as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
        except Exception as e:
            error_msg = f"Erro ao consultar histórico: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "restore_memory_version",
        "Restaura uma versão anterior de uma memória. "
        "O conteúdo atual é salvo como nova versão antes da restauração (backup automático). "
        "Use view_memory_history primeiro para ver versões disponíveis.",
        {"path": Annotated[str, "Path da memoria a restaurar para versao anterior"], "version": Annotated[int, "Numero da versao a restaurar (use view_memory_history para ver versoes disponiveis)"]},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_RESTORE_OUTPUT_SCHEMA,
    )
    async def restore_memory_version(args: dict[str, Any]) -> dict[str, Any]:
        """
        Restaura versão anterior de uma memória.

        O conteúdo atual é salvo como nova versão (backup) antes de
        substituir pelo conteúdo da versão alvo.

        Args:
            args: {
                "path": str — path da memória,
                "version": int — número da versão a restaurar,
                "target_user_id": int (opcional, requer debug mode)
            }

        Returns:
            MCP tool response com confirmação
        """
        path = args.get("path", "").strip()
        version_num = args.get("version")

        if not path:
            return {
                "content": [{"type": "text", "text": "Erro: path é obrigatório"}],
                "is_error": True,
            }

        if version_num is None:
            return {
                "content": [{"type": "text", "text": "Erro: version é obrigatório (número inteiro)"}],
                "is_error": True,
            }

        try:
            version_num = int(version_num)
        except (TypeError, ValueError):
            return {
                "content": [{"type": "text", "text": f"Erro: version deve ser inteiro, recebido: {version_num}"}],
                "is_error": True,
            }

        try:
            path = _validate_path(path)
            user_id = _resolve_user_id(args)
            actual_user_id = _resolve_empresa_user_id(user_id, path)

            def _restore():
                from ..models import AgentMemory, AgentMemoryVersion
                from app import db
                from app.utils.timezone import agora_utc_naive

                memory = AgentMemory.get_by_path(actual_user_id, path)
                if not memory:
                    text = f"Memória não encontrada: {path}"
                    return None, text, {"path": path, "restored_to_version": version_num, "backup_version": None, "preview": None}

                target_version = AgentMemoryVersion.get_version(memory.id, version_num)
                if not target_version:
                    # Listar versões disponíveis para ajudar o usuário
                    available = AgentMemoryVersion.get_versions(memory.id, 20)
                    if available:
                        nums = ", ".join(str(v.version) for v in available)
                        text = (
                            f"Versão {version_num} não encontrada para {path}. "
                            f"Versões disponíveis: {nums}"
                        )
                    else:
                        text = f"Versão {version_num} não encontrada para {path}. Nenhuma versão anterior existe."
                    return None, text, {"path": path, "restored_to_version": version_num, "backup_version": None, "preview": None}

                # Backup: salvar conteúdo atual como nova versão
                backup_version = AgentMemoryVersion.save_version(
                    memory.id, memory.content, changed_by='claude'
                )

                # Restaurar conteúdo da versão alvo
                memory.content = target_version.content
                memory.updated_at = agora_utc_naive()

                db.session.commit()

                preview = (target_version.content or "")[:200]
                if len(target_version.content or "") > 200:
                    preview += "..."

                text = (
                    f"Memória {path} restaurada para versão {version_num}.\n"
                    f"Conteúdo anterior (backup) salvo como versão {backup_version.version}.\n"
                    f"Preview: {preview}"
                )
                return backup_version, text, {
                    "path": path,
                    "restored_to_version": version_num,
                    "backup_version": backup_version.version,
                    "preview": preview,
                }

            backup, result_text, structured = _execute_with_context(_restore)

            if backup is None:
                logger.info(f"[MEMORY_MCP] restore_memory_version: path={path} — {result_text}")
                return {
                    "content": [{"type": "text", "text": result_text}],
                    "structuredContent": structured,
                }

            logger.info(
                f"[MEMORY_MCP] restore_memory_version: path={path}, "
                f"restored_to=v{version_num}, backup=v{backup.version}"
            )
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }

        except ValueError as e:
            return {"content": [{"type": "text", "text": f"Erro: {str(e)}"}], "is_error": True}
        except PermissionError as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
        except Exception as e:
            error_msg = f"Erro ao restaurar versão: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "resolve_pendencia",
        "Marca uma pendência como resolvida para que não apareça mais no briefing de sessão. "
        "Use quando o usuário confirmar que uma pendência listada já foi tratada, "
        "ou quando você mesmo completar a tarefa descrita. "
        "A pendência simplesmente desaparece do contexto de sessões futuras.",
        {"description": Annotated[str, "Texto EXATO da pendencia a marcar como resolvida (deve corresponder a uma pendencia existente no briefing)"]},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_RESOLVE_PENDENCIA_OUTPUT_SCHEMA,
    )
    async def resolve_pendencia(args: dict[str, Any]) -> dict[str, Any]:
        """
        Marca uma pendência como resolvida.

        Salva em /memories/system/resolved_pendencias.json (lista de strings).
        O _build_session_window() filtra pendências que estão nessa lista.

        Args:
            args: {"description": str} — texto da pendência (match exato)

        Returns:
            MCP tool response com confirmação
        """
        description = args.get("description", "").strip()

        if not description:
            return {
                "content": [{"type": "text", "text": "Erro: description é obrigatório"}],
                "is_error": True,
            }

        try:
            user_id = _resolve_user_id(args)

            def _resolve():
                import json
                from ..models import AgentMemory
                from app import db

                path = '/memories/system/resolved_pendencias.json'

                # Carregar lista existente
                existing = AgentMemory.get_by_path(user_id, path)
                if existing and existing.content:
                    try:
                        resolved_list = json.loads(existing.content)
                        if not isinstance(resolved_list, list):
                            resolved_list = []
                    except (json.JSONDecodeError, TypeError):
                        resolved_list = []
                else:
                    resolved_list = []

                # Evitar duplicatas
                if description not in resolved_list:
                    resolved_list.append(description)

                content = json.dumps(resolved_list, ensure_ascii=False)

                if existing:
                    existing.content = content
                else:
                    AgentMemory.create_file(user_id, path, content)

                db.session.commit()
                return len(resolved_list)

            total = _execute_with_context(_resolve)
            logger.info(
                f"[MEMORY_MCP] resolve_pendencia: '{description[:60]}' "
                f"(total resolvidas: {total})"
            )
            return {
                "content": [{
                    "type": "text",
                    "text": f"Pendência resolvida: '{description}'. Total resolvidas: {total}.",
                }],
                "structuredContent": {"description": description, "total_resolved": total},
            }

        except PermissionError as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
        except Exception as e:
            error_msg = f"Erro ao resolver pendência: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "log_system_pitfall",
        "Registra uma armadilha/falha OPERACIONAL do sistema (não erro do agente). "
        "Use quando descobrir um gotcha do ambiente que economizaria tempo se lembrado. "
        "Exemplos: 'journal_id do Nacom SC deve ser 68, não 47', "
        "'API do HIBP retorna 429 se bater mais de 1 req/1.5s', "
        "'campo fiscal X só recalcula via Playwright, não XML-RPC'. "
        "Diferente de corrections (erros do agente) — são conhecimentos sobre armadilhas do sistema.",
        {"area": Annotated[str, "Area do sistema: odoo, ssw, banco, deploy, api, frete, carteira, financeiro"], "description": Annotated[str, "Descricao da armadilha/gotcha operacional encontrada no sistema (max 20 pitfalls ativos)"]},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_LOG_PITFALL_OUTPUT_SCHEMA,
    )
    async def log_system_pitfall(args: dict[str, Any]) -> dict[str, Any]:
        """
        Registra falha operacional do sistema.

        Salva em /memories/system/pitfalls.xml (acumulativo, max 20 pitfalls).
        Pitfalls são injetados no contexto do agente como memória structural.

        Args:
            args: {
                "area": str — área do sistema (odoo, ssw, banco, deploy, etc),
                "description": str — descrição da armadilha/gotcha
            }

        Returns:
            MCP tool response com confirmação
        """
        area = args.get("area", "").strip().lower()
        description = args.get("description", "").strip()

        if not area:
            return {
                "content": [{"type": "text", "text": "Erro: area é obrigatório (ex: odoo, ssw, banco)"}],
                "is_error": True,
            }
        if not description:
            return {
                "content": [{"type": "text", "text": "Erro: description é obrigatório"}],
                "is_error": True,
            }

        try:
            caller_user_id = _resolve_user_id(args)
            # Pitfalls sao conhecimento organizacional — salvar como empresa (user_id=0)
            empresa_user_id = 0

            def _log_pitfall():
                import json
                from ..models import AgentMemory
                from app import db
                from app.utils.timezone import agora_utc_naive

                new_path = '/memories/empresa/armadilhas/system-pitfalls.json'
                old_path = '/memories/system/pitfalls.json'
                now = agora_utc_naive()

                # Carregar lista existente (novo path empresa)
                existing = AgentMemory.get_by_path(empresa_user_id, new_path)
                if existing and existing.content:
                    try:
                        pitfalls = json.loads(existing.content)
                        if not isinstance(pitfalls, list):
                            pitfalls = []
                    except (json.JSONDecodeError, TypeError):
                        pitfalls = []
                else:
                    pitfalls = []

                # Backward-compat: migrar conteudo do path antigo (qualquer user)
                if not pitfalls:
                    old_existing = AgentMemory.get_by_path(caller_user_id, old_path)
                    if old_existing and old_existing.content:
                        try:
                            old_pitfalls = json.loads(old_existing.content)
                            if isinstance(old_pitfalls, list):
                                pitfalls = old_pitfalls
                                logger.info(
                                    f"[MEMORY_MCP] Migrado {len(pitfalls)} pitfalls "
                                    f"de {old_path} (user={caller_user_id}) para {new_path} (empresa)"
                                )
                        except (json.JSONDecodeError, TypeError):
                            pass

                # Dedup por descrição (atualiza timestamp se já existe)
                found = False
                for p in pitfalls:
                    if p.get('description') == description:
                        p['updated_at'] = now.isoformat()
                        p['hit_count'] = p.get('hit_count', 1) + 1
                        found = True
                        break

                if not found:
                    pitfalls.append({
                        'area': area,
                        'description': description,
                        'created_at': now.isoformat(),
                        'updated_at': now.isoformat(),
                        'hit_count': 1,
                    })

                # Cap em 20 pitfalls (remove mais antigos)
                if len(pitfalls) > 20:
                    pitfalls.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
                    pitfalls = pitfalls[:20]

                content = json.dumps(pitfalls, ensure_ascii=False, indent=2)

                if existing:
                    existing.content = content
                else:
                    mem = AgentMemory.create_file(empresa_user_id, new_path, content)
                    mem.category = 'structural'  # Lento decay, sempre relevante
                    mem.escopo = 'empresa'
                    mem.created_by = caller_user_id  # Auditoria: quem originou

                db.session.commit()

                # Regenerar XML de pitfalls para injeção no contexto (empresa)
                _regenerate_pitfalls_xml(empresa_user_id, pitfalls)

                return len(pitfalls), found

            total, is_update = _execute_with_context(_log_pitfall)
            logger.info(
                f"[MEMORY_MCP] log_system_pitfall: area={area}, "
                f"desc='{description[:60]}' (total: {total})"
            )
            return {
                "content": [{
                    "type": "text",
                    "text": f"Pitfall registrado em '{area}': {description}. Total pitfalls: {total}.",
                }],
                "structuredContent": {
                    "area": area,
                    "description": description,
                    "total_pitfalls": total,
                    "is_update": is_update,
                },
            }

        except PermissionError as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
        except Exception as e:
            error_msg = f"Erro ao registrar pitfall: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "query_knowledge_graph",
        "Consulta o Knowledge Graph de memórias para descobrir relações entre entidades. "
        "Use para responder perguntas como 'o que sabemos sobre RODONAVES?', "
        "'quais transportadoras atendem AM?', ou 'que relações existem com este cliente?'. "
        "Retorna entidades relacionadas, tipos de relação e memórias associadas.",
        {
            "entity_name": Annotated[str, "Nome da entidade a buscar (ex: RODONAVES, AM, Atacadao). Case-insensitive, busca por ILIKE"],
            "entity_type": Annotated[Optional[str], "Filtro opcional: transportadora, uf, cliente, produto, pedido, fornecedor, conceito. Se omitido, busca todos os tipos"],
            "max_hops": Annotated[Optional[int], "Profundidade da busca: 1 (relacoes diretas) ou 2 (relacoes de relacoes). Default: 1"],
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def query_knowledge_graph(args: dict[str, Any]) -> dict[str, Any]:
        """
        Consulta o Knowledge Graph por entidade.

        Pipeline:
        1. Busca entity_id por nome (ILIKE) em agent_memory_entities
        2. Hop 1: relações diretas via agent_memory_entity_relations
        3. Hop 2 (opcional): segue entidades do hop 1
        4. Para cada relação: retorna entidades, tipo, peso e memórias linkadas
        """
        entity_name = args.get("entity_name", "").strip()
        entity_type = args.get("entity_type")
        max_hops = min(max(args.get("max_hops", 1) or 1, 1), 2)

        if not entity_name:
            return {"content": [{"type": "text", "text": "entity_name é obrigatório"}], "is_error": True}

        try:
            user_id = _resolve_user_id(args)

            def _query():
                from app import db
                from sqlalchemy import text as sql_text
                from ..services.knowledge_graph_service import _normalize_name

                normalized = _normalize_name(entity_name)

                # 1. Buscar entidades matching
                entity_sql = """
                    SELECT id, entity_type, entity_name, mention_count
                    FROM agent_memory_entities
                    WHERE user_id = ANY(:user_ids)
                    AND LOWER(entity_name) LIKE LOWER(:pattern)
                """
                params: dict = {
                    "user_ids": [user_id, 0],
                    "pattern": f"%{normalized}%",
                }
                if entity_type:
                    entity_sql += " AND entity_type = :etype"
                    params["etype"] = entity_type.lower()
                entity_sql += " ORDER BY mention_count DESC LIMIT 10"

                entities = db.session.execute(sql_text(entity_sql), params).fetchall()

                if not entities:
                    return f"Nenhuma entidade encontrada para '{entity_name}'.", {
                        "entity_name": entity_name,
                        "entities_found": 0,
                        "relations": [],
                        "memories": [],
                    }

                entity_ids = [e[0] for e in entities]
                entity_map = {e[0]: {"type": e[1], "name": e[2], "mentions": e[3]} for e in entities}

                # 2. Hop 1: relações diretas (source OU target)
                rel_sql = """
                    SELECT r.source_entity_id, r.target_entity_id, r.relation_type,
                           r.weight, e_src.entity_name, e_src.entity_type,
                           e_tgt.entity_name, e_tgt.entity_type
                    FROM agent_memory_entity_relations r
                    JOIN agent_memory_entities e_src ON r.source_entity_id = e_src.id
                    JOIN agent_memory_entities e_tgt ON r.target_entity_id = e_tgt.id
                    WHERE r.source_entity_id = ANY(:eids) OR r.target_entity_id = ANY(:eids)
                    ORDER BY r.weight DESC
                    LIMIT 30
                """
                rel_rows = db.session.execute(sql_text(rel_sql), {"eids": entity_ids}).fetchall()

                relations = []
                hop1_entity_ids = set(entity_ids)
                for r in rel_rows:
                    relations.append({
                        "source": r[4], "source_type": r[5],
                        "target": r[6], "target_type": r[7],
                        "relation": r[3], "weight": round(r[3] or 0, 2) if r[3] else 0,
                        "relation_type": r[2],
                        "hop": 1,
                    })
                    hop1_entity_ids.add(r[0])
                    hop1_entity_ids.add(r[1])

                # 3. Hop 2 (opcional)
                if max_hops >= 2 and hop1_entity_ids - set(entity_ids):
                    hop2_ids = list(hop1_entity_ids - set(entity_ids))[:15]
                    rel2_rows = db.session.execute(sql_text("""
                        SELECT r.source_entity_id, r.target_entity_id, r.relation_type,
                               r.weight, e_src.entity_name, e_src.entity_type,
                               e_tgt.entity_name, e_tgt.entity_type
                        FROM agent_memory_entity_relations r
                        JOIN agent_memory_entities e_src ON r.source_entity_id = e_src.id
                        JOIN agent_memory_entities e_tgt ON r.target_entity_id = e_tgt.id
                        WHERE (r.source_entity_id = ANY(:eids) OR r.target_entity_id = ANY(:eids))
                        AND r.source_entity_id != ALL(:orig) AND r.target_entity_id != ALL(:orig)
                        ORDER BY r.weight DESC
                        LIMIT 15
                    """), {"eids": hop2_ids, "orig": entity_ids}).fetchall()

                    for r in rel2_rows:
                        relations.append({
                            "source": r[4], "source_type": r[5],
                            "target": r[6], "target_type": r[7],
                            "relation": r[3], "weight": round(r[3] or 0, 2) if r[3] else 0,
                            "relation_type": r[2],
                            "hop": 2,
                        })

                # 4. Memórias associadas às entidades encontradas
                all_eids = list(hop1_entity_ids)
                mem_sql = """
                    SELECT DISTINCT m.path, LEFT(m.content, 100) as preview
                    FROM agent_memories m
                    JOIN agent_memory_entity_links l ON l.memory_id = m.id
                    WHERE l.entity_id = ANY(:eids)
                    AND m.is_cold = false
                    LIMIT 10
                """
                mem_rows = db.session.execute(sql_text(mem_sql), {"eids": all_eids}).fetchall()

                memories = [{"path": m[0], "preview": m[1]} for m in mem_rows]

                # Format text output
                lines = [f"Entidades encontradas para '{entity_name}':"]
                for e in entities:
                    lines.append(f"  [{e[1]}] {e[2]} (menções: {e[3]})")

                if relations:
                    lines.append(f"\nRelações ({len(relations)}):")
                    for rel in relations[:20]:
                        hop_label = f" [hop {rel['hop']}]" if rel['hop'] > 1 else ""
                        lines.append(
                            f"  {rel['source']} --{rel['relation_type']}--> "
                            f"{rel['target']} (peso: {rel['weight']}){hop_label}"
                        )

                if memories:
                    lines.append(f"\nMemórias associadas ({len(memories)}):")
                    for mem in memories:
                        lines.append(f"  {mem['path']}: {mem['preview']}")

                text = "\n".join(lines)
                structured = {
                    "entity_name": entity_name,
                    "entities_found": len(entities),
                    "entities": [entity_map[eid] for eid in entity_ids],
                    "relations": relations,
                    "memories": memories,
                }
                return text, structured

            result = _execute_with_context(_query)
            if isinstance(result, tuple):
                text, structured = result
            else:
                text = str(result)
                structured = {"entity_name": entity_name, "entities_found": 0, "relations": [], "memories": []}

            return {
                "content": [{"type": "text", "text": text}],
                "structuredContent": structured,
            }

        except PermissionError as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
        except Exception as e:
            error_msg = f"Erro ao consultar knowledge graph: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @enhanced_tool(
        "register_improvement",
        "Registra sugestao de melhoria para o Claude Code (dev). "
        "Use quando descobrir: bug em skill existente (skill_bug), "
        "skill que falta (skill_suggestion), instrucao necessaria "
        "(instruction_request), ou gotcha do sistema (gotcha_report). "
        "Diferente de log_system_pitfall (armadilhas operacionais do ambiente) "
        "— isto vai para o dialogo de melhoria Agent SDK <-> Claude Code.",
        {
            "category": Annotated[str, "Categoria: skill_bug, skill_suggestion, instruction_request, prompt_feedback, gotcha_report, memory_feedback"],
            "severity": Annotated[str, "Severidade: critical (erro/frustacao recorrente), warning (melhoria significativa), info (nice-to-have)"],
            "title": Annotated[str, "Titulo conciso da sugestao (max 100 chars)"],
            "description": Annotated[str, "Descricao PRESCRITIVA: o que deve mudar e por que. Para skill_bug: nome da skill, o que fez errado, o que deveria fazer"],
            "evidence": Annotated[str, "Evidencia da sessao: o que aconteceu, IDs envolvidos, valores, o que falhou"],
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=MEMORY_REGISTER_IMPROVEMENT_OUTPUT_SCHEMA,
    )
    async def register_improvement(args: dict[str, Any]) -> dict[str, Any]:
        """
        Registra sugestao de melhoria no dialogo Agent SDK <-> Claude Code.

        Escreve diretamente na tabela agent_improvement_dialogue (v1, proposed).
        O D8 cron (Claude Code local) avalia e implementa/rejeita.

        Args:
            args: {
                "category": str — skill_bug|skill_suggestion|instruction_request|
                                   prompt_feedback|gotcha_report|memory_feedback,
                "severity": str — critical|warning|info,
                "title": str — titulo conciso (max 100 chars),
                "description": str — descricao prescritiva,
                "evidence": str — evidencia da sessao
            }

        Returns:
            MCP tool response com suggestion_key gerado
        """
        category = args.get("category", "").strip()
        severity = args.get("severity", "info").strip()
        title = args.get("title", "").strip()
        description = args.get("description", "").strip()
        evidence = args.get("evidence", "").strip()

        # Validacoes
        valid_categories = {
            'skill_bug', 'skill_suggestion', 'instruction_request',
            'prompt_feedback', 'gotcha_report', 'memory_feedback',
        }
        valid_severities = {'critical', 'warning', 'info'}

        if category not in valid_categories:
            return {
                "content": [{"type": "text", "text": f"Erro: category deve ser um de: {', '.join(sorted(valid_categories))}"}],
                "is_error": True,
            }
        if severity not in valid_severities:
            severity = 'info'
        if not title:
            return {
                "content": [{"type": "text", "text": "Erro: title e obrigatorio"}],
                "is_error": True,
            }
        if not description:
            return {
                "content": [{"type": "text", "text": "Erro: description e obrigatoria"}],
                "is_error": True,
            }
        if len(title) > 200:
            title = title[:197] + '...'

        try:
            from ..models import AgentImprovementDialogue
            from app import db
            from app.agente.config.permissions import get_current_session_id

            def _register():
                session_id = get_current_session_id()
                evidence_json = {
                    'session_signal': evidence,
                    'occurrences': 1,
                    'session_ids': [session_id] if session_id else [],
                    'source': 'real_time',
                }

                suggestion = AgentImprovementDialogue.create_suggestion(
                    category=category,
                    severity=severity,
                    title=title,
                    description=description,
                    evidence=evidence_json,
                    session_ids=[session_id] if session_id else [],
                )
                db.session.commit()
                return suggestion.suggestion_key

            key = _execute_with_context(_register)
            logger.info(
                f"[MEMORY_MCP] register_improvement: {key} "
                f"category={category} severity={severity} title='{title[:60]}'"
            )
            return {
                "content": [{
                    "type": "text",
                    "text": (
                        f"Sugestao registrada: {key} ({category}/{severity}).\n"
                        f"Titulo: {title}\n"
                        f"O Claude Code (dev) avaliara na proxima execucao D8."
                    ),
                }],
                "structuredContent": {
                    "suggestion_key": key,
                    "category": category,
                    "severity": severity,
                    "title": title,
                    "status": "proposed",
                },
            }

        except Exception as e:
            error_msg = f"Erro ao registrar improvement: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    # Criar MCP server in-process
    memory_server = create_enhanced_mcp_server(
        name="memory-tools",
        version="2.2.0",
        tools=[
            view_memories,
            save_memory,
            update_memory,
            delete_memory,
            list_memories,
            clear_memories,
            search_cold_memories,
            view_memory_history,
            restore_memory_version,
            resolve_pendencia,
            log_system_pitfall,
            query_knowledge_graph,
            register_improvement,
        ],
    )

    logger.info("[MEMORY_MCP] Enhanced MCP 'memory' v2.2.0 registrado (13 tools, structuredContent)")

except ImportError as e:
    # claude_agent_sdk não disponível (ex: rodando fora do agente)
    memory_server = None
    logger.debug(f"[MEMORY_MCP] claude_agent_sdk não disponível: {e}")
