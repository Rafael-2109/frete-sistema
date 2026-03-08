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

_SONNET_MODEL = "claude-sonnet-4-6"

_CONTEXTUAL_PROMPT = """\
<user_memories>
{existing_memories}
</user_memories>

Aqui está a memória sendo salva pelo usuário:
<memory path="{path}">
{content}
</memory>

Responda no formato abaixo. Cada seção é obrigatória.

CONTEXTO: 1-2 frases situando esta memória no conjunto do usuário (máximo 80 tokens)
ENTIDADES: lista de entidades no formato tipo:nome separadas por | (ex: transportadora:RODONAVES|uf:AM|cliente:ATACADAO)
RELACOES: lista de relações no formato origem>tipo>destino separadas por | (ex: RODONAVES>atrasa_para>AM)

Tipos de entidade válidos: uf, pedido, cnpj, valor, transportadora, produto, cliente, fornecedor, regra
Se não houver entidades ou relações claras, escreva ENTIDADES: nenhuma e RELACOES: nenhuma\
"""


def _generate_memory_context(
    user_id: int, path: str, content: str,
) -> tuple[Optional[str], list[tuple[str, str]], list[tuple[str, str, str]]]:
    """
    Gera contexto semântico breve via Haiku para enriquecer embedding de memória.

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
        - entities: [(tipo, nome), ...] — entidades extraídas pelo Haiku
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
            messages=[{
                "role": "user",
                "content": _CONTEXTUAL_PROMPT.format(
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
                f"[MEMORY_MCP] Contextual: Haiku retornou contexto insuficiente "
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
    1. Se MEMORY_CONTEXTUAL_EMBEDDING ativo: gerar contexto + entidades + relações via Haiku (~300ms)
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

        # T3-1 + T3-3: Contextual Retrieval — gerar contexto + entidades + relações via Haiku
        context_prefix = None
        if MEMORY_CONTEXTUAL_EMBEDDING:
            context_prefix, haiku_entities, haiku_relations = _generate_memory_context(
                user_id, path, content
            )

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
                    updated_at = :updated_at
            """), {
                "memory_id": mem.id,
                "user_id": user_id,
                "path": path,
                "texto_embedado": texto_embedado,
                "embedding": embedding_str,
                "model_used": VOYAGE_DEFAULT_MODEL,
                "content_hash": c_hash,
                "updated_at": agora_utc_naive(),
            })
            db.session.commit()

            logger.debug(f"[MEMORY_MCP] Embedding salvo para {path}")

        _execute_with_context(_do_embed)

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] _embed_memory_best_effort falhou: {e}")

    return haiku_entities, haiku_relations


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
    Regenera /memories/system/pitfalls.xml a partir da lista JSON.

    O XML é o formato injetado no contexto do agente (tier 1 como structural memory).
    O JSON é a fonte de verdade (editável via tool).

    Args:
        user_id: ID do usuário
        pitfalls: Lista de dicts com area, description, hit_count, etc
    """
    try:
        from app.agente.models import AgentMemory
        from app.utils.timezone import agora_utc_naive

        path = '/memories/system/pitfalls.xml'
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
    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Erro ao regenerar pitfalls XML (ignorado): {e}")


def _check_memory_duplicate(user_id: int, content: str, current_path: str = '') -> Optional[str]:
    """
    Verifica se ja existe memoria semanticamente similar para o usuario.

    Busca em agent_memory_embeddings por conteudo com cosine > 0.85,
    excluindo o path atual (para nao detectar self-match em updates).

    IMPORTANTE: O content recebido e XML raw, mas os embeddings no banco foram
    gerados a partir de texto contextual enriquecido pelo Sonnet. Para evitar
    falsos negativos (similarity ~0.69 entre XML e texto narrativo), fazemos
    strip_xml_tags antes de buscar, elevando a similarity para faixa detectavel.

    Args:
        user_id: ID do usuario
        content: Conteudo da nova memoria (pode conter tags XML)
        current_path: Path sendo atualizado (excluido da busca)

    Returns:
        Path da memoria duplicada ou None se nao houver duplicata
    """
    try:
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
        if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
            return None

        from app.embeddings.service import EmbeddingService
        from ..services.knowledge_graph_service import strip_xml_tags

        # Strip XML para alinhar com embeddings contextuais no banco.
        # XML raw vs texto enriquecido causa similarity ~0.69 (abaixo do threshold).
        # Texto limpo vs texto enriquecido sobe para ~0.85+ (detectavel).
        clean_content = strip_xml_tags(content)

        svc = EmbeddingService()
        results = svc.search_memories(
            clean_content, user_id=user_id, limit=3, min_similarity=0.85
        )

        if not results:
            return None

        for r in results:
            path = r.get('path', '')
            # Excluir self-match
            if path and path != current_path:
                similarity = r.get('similarity', 0)
                if similarity >= 0.85:
                    logger.info(
                        f"[MEMORY_MCP] Duplicata detectada: {current_path} ~ {path} "
                        f"(sim={similarity:.3f})"
                    )
                    return path

    except Exception as e:
        logger.debug(f"[MEMORY_MCP] Dedup check falhou (ignorado): {e}")

    return None


def _track_correction_feedback(user_id: int, correction_path: str, correction_content: str) -> None:
    """
    Memory v2 — Feedback Loop: quando uma correção é salva,
    incrementa correction_count nas memórias recentemente injetadas.

    Lógica: se o Agent acabou de salvar uma correção, algo nas memórias
    existentes pode estar errado. Incrementamos correction_count nas
    memórias que foram injetadas nos últimos 5 minutos (mesmo turno).

    Best-effort: falhas silenciosas.
    """
    try:
        from ..models import AgentMemory
        from app import db
        from sqlalchemy import text as sql_text
        from app.utils.timezone import agora_utc_naive
        from datetime import timedelta

        now = agora_utc_naive()
        cutoff = now - timedelta(minutes=5)

        # Buscar memórias injetadas recentemente (mesmo turno) que NÃO são a correção atual
        recent = AgentMemory.query.filter(
            AgentMemory.user_id == user_id,
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.last_accessed_at >= cutoff,
            AgentMemory.usage_count > 0,
            AgentMemory.path != correction_path,
        ).all()

        if not recent:
            return

        # Incrementar correction_count apenas nas que têm conteúdo relacionado
        correction_lower = correction_content.lower()
        related_ids = []
        for mem in recent:
            mem_content = (mem.content or "").lower()
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

    Após salvar, busca memórias semanticamente similares (cosine 0.50-0.85)
    no mesmo domínio (parent path). Se encontrar com entidades em comum,
    marca a NOVA memória com has_potential_conflict=True.

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

            # Excluir self-match e duplicatas (>0.90 já detectadas pelo dedup)
            if r_path == new_path or similarity >= 0.90:
                continue

            # Faixa de conflito: similar o suficiente para ser relacionado,
            # mas diferente o suficiente para potencialmente contradizer
            if 0.50 <= similarity <= 0.85:
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
            args: {"path": str, "target_user_id": int (opcional, requer debug mode)}

        Returns:
            MCP tool response com conteúdo ou listagem
        """
        path = args.get("path", "/memories").strip()

        try:
            path = _validate_path(path)
            user_id = _resolve_user_id(args)

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
            actual_user_id = user_id
            escopo = 'pessoal'
            created_by_id = None

            if path.startswith('/memories/empresa/'):
                actual_user_id = 0  # Usuario Sistema
                escopo = 'empresa'
                created_by_id = user_id

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

            action = _execute_with_context(_save)
            logger.info(f"[MEMORY_MCP] save_memory: {path} ({action})")

            # Best-effort: verificar duplicatas semanticas
            dedup_warning = ''
            try:
                dup_path = _check_memory_duplicate(actual_user_id, content, current_path=path)
                if dup_path:
                    dedup_warning = (
                        f" AVISO: conteudo similar ja existe em '{dup_path}'. "
                        f"Considere consolidar."
                    )
            except Exception:
                pass

            # Best-effort: verificar se memórias precisam de consolidação + tier frio
            # Skip consolidacao para memorias empresa (user_id=0) por enquanto
            if actual_user_id != 0:
                try:
                    from ..services.memory_consolidator import maybe_consolidate, maybe_move_to_cold
                    maybe_consolidate(actual_user_id)
                    maybe_move_to_cold(actual_user_id)
                except Exception as consolidation_err:
                    logger.debug(
                        f"[MEMORY_MCP] Consolidação/cold não executada (ignorado): {consolidation_err}"
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
                if '/corrections/' in path.lower():
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
                "content": [{"type": "text", "text": f"Memória {action} em {path}{dedup_warning}{pitfall_hint}"}]
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
            user_id = _resolve_user_id(args)

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
                                mem = AgentMemory.get_by_path(user_id, path)
                                return mem.content if mem else None

                            updated_content = _execute_with_context(_get_content)
                            if updated_content:
                                _entities, _relations = _embed_memory_best_effort(
                                    user_id, path, updated_content
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
                                mem = AgentMemory.get_by_path(user_id, path)
                                if mem:
                                    remove_memory_links(mem.id)
                                    extract_and_link_entities(
                                        user_id, mem.id, mem.content,
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
            user_id = _resolve_user_id(args)

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

                # T3-3: Cleanup explícito de links no Knowledge Graph
                try:
                    from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
                    if MEMORY_KNOWLEDGE_GRAPH and memory_ids:
                        from ..services.knowledge_graph_service import remove_memory_links
                        for mid in memory_ids:
                            remove_memory_links(mid)
                except Exception as kg_err:
                    logger.debug(f"[MEMORY_MCP] KG cleanup falhou (ignorado): {kg_err}")

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
                "content": [{"type": "text", "text": f"Todas as memórias limpas ({count} itens removidos)"}]
            }

        except Exception as e:
            error_msg = f"Erro ao limpar memórias: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "search_cold_memories",
        "Busca no tier frio de memórias: memórias que foram automaticamente removidas da "
        "injeção por baixa efetividade (injetadas 20+ vezes sem nunca serem usadas na resposta). "
        "Use quando precisar consultar histórico de informações antigas que não aparecem mais "
        "no contexto automático. Busca por texto no conteúdo e path.",
        {"query": str},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
                query_lower = f"%{query.lower()}%"
                cold_memories = AgentMemory.query.filter(
                    AgentMemory.user_id == user_id,
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
                    return f"Nenhuma memória fria encontrada para '{query}'."

                lines = [f"Memórias frias ({len(cold_memories)} resultados para '{query}'):\n"]
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

                return "\n".join(lines)

            result = _execute_with_context(_search_cold)
            logger.info(f"[MEMORY_MCP] search_cold_memories: query='{query[:50]}'")
            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            error_msg = f"Erro ao buscar memórias frias: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "view_memory_history",
        "Consulta histórico de versões anteriores de uma memória. "
        "Use para ver quando e por quem a memória foi alterada, "
        "e o conteúdo de versões anteriores (preview de 200 chars). "
        "Útil para auditoria ou antes de restaurar uma versão antiga.",
        {"path": str, "limit": int},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
            limit = min(max(int(args.get("limit", 5)), 1), 20)

            def _view_history():
                from ..models import AgentMemory, AgentMemoryVersion

                memory = AgentMemory.get_by_path(user_id, path)
                if not memory:
                    return None, f"Memória não encontrada: {path}"

                versions = AgentMemoryVersion.get_versions(memory.id, limit)
                if not versions:
                    return None, f"Nenhuma versão anterior para {path}. A memória existe mas nunca foi modificada."

                lines = [f"Histórico de {path} ({len(versions)} versão(ões)):\n"]
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

                return versions, "\n".join(lines)

            versions, result_text = _execute_with_context(_view_history)

            if versions is None:
                logger.info(f"[MEMORY_MCP] view_memory_history: path={path} — {result_text}")
                return {"content": [{"type": "text", "text": result_text}]}

            logger.info(
                f"[MEMORY_MCP] view_memory_history: path={path}, "
                f"versions={len(versions)}"
            )
            return {"content": [{"type": "text", "text": result_text}]}

        except ValueError as e:
            return {"content": [{"type": "text", "text": f"Erro: {str(e)}"}], "is_error": True}
        except PermissionError as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
        except Exception as e:
            error_msg = f"Erro ao consultar histórico: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "restore_memory_version",
        "Restaura uma versão anterior de uma memória. "
        "O conteúdo atual é salvo como nova versão antes da restauração (backup automático). "
        "Use view_memory_history primeiro para ver versões disponíveis.",
        {"path": str, "version": int},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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

            def _restore():
                from ..models import AgentMemory, AgentMemoryVersion
                from app import db
                from app.utils.timezone import agora_utc_naive

                memory = AgentMemory.get_by_path(user_id, path)
                if not memory:
                    return None, f"Memória não encontrada: {path}"

                target_version = AgentMemoryVersion.get_version(memory.id, version_num)
                if not target_version:
                    # Listar versões disponíveis para ajudar o usuário
                    available = AgentMemoryVersion.get_versions(memory.id, 20)
                    if available:
                        nums = ", ".join(str(v.version) for v in available)
                        return None, (
                            f"Versão {version_num} não encontrada para {path}. "
                            f"Versões disponíveis: {nums}"
                        )
                    return None, f"Versão {version_num} não encontrada para {path}. Nenhuma versão anterior existe."

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

                return backup_version, (
                    f"Memória {path} restaurada para versão {version_num}.\n"
                    f"Conteúdo anterior (backup) salvo como versão {backup_version.version}.\n"
                    f"Preview: {preview}"
                )

            backup, result_text = _execute_with_context(_restore)

            if backup is None:
                logger.info(f"[MEMORY_MCP] restore_memory_version: path={path} — {result_text}")
                return {"content": [{"type": "text", "text": result_text}]}

            logger.info(
                f"[MEMORY_MCP] restore_memory_version: path={path}, "
                f"restored_to=v{version_num}, backup=v{backup.version}"
            )
            return {"content": [{"type": "text", "text": result_text}]}

        except ValueError as e:
            return {"content": [{"type": "text", "text": f"Erro: {str(e)}"}], "is_error": True}
        except PermissionError as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
        except Exception as e:
            error_msg = f"Erro ao restaurar versão: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "resolve_pendencia",
        "Marca uma pendência como resolvida para que não apareça mais no briefing de sessão. "
        "Use quando o usuário confirmar que uma pendência listada já foi tratada, "
        "ou quando você mesmo completar a tarefa descrita. "
        "A pendência simplesmente desaparece do contexto de sessões futuras.",
        {"description": str},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
            user_id = get_current_user_id()

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
                }]
            }

        except Exception as e:
            error_msg = f"Erro ao resolver pendência: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    @tool(
        "log_system_pitfall",
        "Registra uma armadilha/falha OPERACIONAL do sistema (não erro do agente). "
        "Use quando descobrir um gotcha do ambiente que economizaria tempo se lembrado. "
        "Exemplos: 'journal_id do Nacom SC deve ser 68, não 47', "
        "'API do HIBP retorna 429 se bater mais de 1 req/1.5s', "
        "'campo fiscal X só recalcula via Playwright, não XML-RPC'. "
        "Diferente de corrections (erros do agente) — são conhecimentos sobre armadilhas do sistema.",
        {"area": str, "description": str},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
            user_id = get_current_user_id()

            def _log_pitfall():
                import json
                from ..models import AgentMemory
                from app import db
                from app.utils.timezone import agora_utc_naive

                path = '/memories/system/pitfalls.json'
                now = agora_utc_naive()

                # Carregar lista existente
                existing = AgentMemory.get_by_path(user_id, path)
                if existing and existing.content:
                    try:
                        pitfalls = json.loads(existing.content)
                        if not isinstance(pitfalls, list):
                            pitfalls = []
                    except (json.JSONDecodeError, TypeError):
                        pitfalls = []
                else:
                    pitfalls = []

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
                    mem = AgentMemory.create_file(user_id, path, content)
                    mem.category = 'structural'  # Lento decay, sempre relevante

                db.session.commit()

                # Regenerar XML de pitfalls para injeção no contexto
                _regenerate_pitfalls_xml(user_id, pitfalls)

                return len(pitfalls)

            total = _execute_with_context(_log_pitfall)
            logger.info(
                f"[MEMORY_MCP] log_system_pitfall: area={area}, "
                f"desc='{description[:60]}' (total: {total})"
            )
            return {
                "content": [{
                    "type": "text",
                    "text": f"Pitfall registrado em '{area}': {description}. Total pitfalls: {total}.",
                }]
            }

        except Exception as e:
            error_msg = f"Erro ao registrar pitfall: {str(e)}"
            logger.error(f"[MEMORY_MCP] {error_msg}")
            return {"content": [{"type": "text", "text": error_msg}], "is_error": True}

    # Criar MCP server in-process
    memory_server = create_sdk_mcp_server(
        name="memory-tools",
        version="1.3.0",
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
        ],
    )

    logger.info("[MEMORY_MCP] Custom Tool MCP 'memory' registrada com sucesso (11 operações)")

except ImportError as e:
    # claude_agent_sdk não disponível (ex: rodando fora do agente)
    memory_server = None
    logger.debug(f"[MEMORY_MCP] claude_agent_sdk não disponível: {e}")
