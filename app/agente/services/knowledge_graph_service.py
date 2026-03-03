"""
Knowledge Graph Service — T3-3: Extração, linking e query de entidades em memórias.

3 Layers de extração:
  Layer 1: Regex (~2ms) — UF, pedido, CNPJ, valor
  Layer 2: Voyage Semantic Search (~300ms) — transportadora, produto, cliente, fornecedor
  Layer 3: Haiku (0ms extra) — relações semânticas (piggyback no contextual retrieval)

Uso (WRITE PATH — chamado por memory_mcp_tool.py):
    from app.agente.services.knowledge_graph_service import (
        extract_and_link_entities,
        remove_memory_links,
    )
    extract_and_link_entities(user_id, memory_id, content, haiku_entities, haiku_relations)

Uso (READ PATH — chamado por client.py):
    from app.agente.services.knowledge_graph_service import query_graph_memories
    graph_memory_ids = query_graph_memories(user_id, prompt, exclude_ids={...})

Uso (STATS — chamado por insights_service.py):
    from app.agente.services.knowledge_graph_service import get_graph_stats
"""

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# =====================================================================
# CONSTANTES
# =====================================================================

_UFS_BRASIL = frozenset({
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
    'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
})

# Regex patterns para Layer 1
_RE_PEDIDO = re.compile(r'\b(V[CF][DB]\d{5,})\b', re.IGNORECASE)
_RE_CNPJ = re.compile(r'\b(\d{2}\.\d{3}\.\d{3})[/\d.-]*\b')
_RE_CNPJ_RAW = re.compile(r'\b(\d{8})\d{6}\b')  # 14 dígitos consecutivos → raiz 8
_RE_VALOR = re.compile(r'R\$\s*([\d.,]+)')

# Nota: SE e PA são UFs válidas mas também palavras comuns.
# Aceitamos como UFs porque o contexto de memórias do agente é logístico.


def _normalize_name(name: str) -> str:
    """
    Normaliza nome de entidade: uppercase, sem acentos, trim.

    >>> _normalize_name("Rodonaves Transporte")
    'RODONAVES TRANSPORTE'
    >>> _normalize_name("São Paulo")
    'SAO PAULO'
    """
    if not name:
        return ''
    # Remove acentos
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_text.upper().strip()


# =====================================================================
# LAYER 1: REGEX (~2ms, zero custo)
# =====================================================================

def _extract_entities_regex(content: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Extrai entidades estruturadas via regex.

    Returns:
        Lista de tuplas (entity_type, entity_name, entity_key)
    """
    if not content:
        return []

    entities: List[Tuple[str, str, Optional[str]]] = []

    # UFs — tokens de 2 chars MAIÚSCULAS que são UFs válidas
    # Usa texto ORIGINAL (não uppercase) para evitar falsos positivos:
    # "Se o cliente..." (conjunção) ≠ "SE" (Sergipe)
    # Em português, UFs são convencionalmente escritas em maiúsculas.
    seen_ufs: Set[str] = set()
    for match in re.finditer(r'\b([A-Z]{2})\b', content):
        token = match.group(1)
        if token in _UFS_BRASIL and token not in seen_ufs:
            seen_ufs.add(token)
            entities.append(('uf', token, token))

    # Pedidos — VCD/VCB/VFD/VFB + 5+ dígitos
    for match in _RE_PEDIDO.finditer(content):
        pedido = match.group(1).upper()
        entities.append(('pedido', pedido, pedido))

    # CNPJs — formato XX.XXX.XXX ou 14 dígitos consecutivos
    cnpj_raizes: Set[str] = set()
    for match in _RE_CNPJ.finditer(content):
        raiz = match.group(1).replace('.', '')
        if len(raiz) == 8 and raiz not in cnpj_raizes:
            cnpj_raizes.add(raiz)
            entities.append(('cnpj', raiz, raiz))

    for match in _RE_CNPJ_RAW.finditer(content):
        raiz = match.group(1)
        if raiz not in cnpj_raizes:
            cnpj_raizes.add(raiz)
            entities.append(('cnpj', raiz, raiz))

    # Valores monetários — R$ X.XXX,XX
    for match in _RE_VALOR.finditer(content):
        valor_str = match.group(0).strip()
        entities.append(('valor', valor_str, None))

    return entities


# =====================================================================
# LAYER 2: VOYAGE SEMANTIC SEARCH (~300-500ms, zero custo API novo)
# =====================================================================

def _extract_entities_voyage(content: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Resolve nomes de entidades usando embeddings já indexados.

    Reutiliza infra existente (product_search, entity_search, service.search_carriers).
    Thresholds altos (0.7+) para evitar falsos positivos.

    Returns:
        Lista de tuplas (entity_type, entity_name, entity_key)
    """
    if not content or len(content) < 5:
        return []

    entities: List[Tuple[str, str, Optional[str]]] = []

    # Truncar conteúdo para busca (economia de custo/latência)
    search_text = content[:300] if len(content) > 300 else content

    # --- Transportadoras ---
    try:
        from app.embeddings.service import EmbeddingService
        svc = EmbeddingService()
        carriers = svc.search_carriers(
            query=search_text,
            limit=3,
            min_similarity=0.70,
        )
        for c in carriers:
            name = _normalize_name(c.get('carrier_name', ''))
            cnpj = c.get('cnpj', '')
            if name:
                entities.append(('transportadora', name, cnpj or None))
    except Exception as e:
        logger.debug(f"[KG] Carrier search falhou (ignorado): {e}")

    # --- Entidades financeiras (clientes/fornecedores) ---
    try:
        from app.embeddings.entity_search import buscar_entidade_semantica
        for entity_type_search in ['customer', 'supplier']:
            results = buscar_entidade_semantica(
                nome=search_text,
                entity_type=entity_type_search,
                limite=3,
                min_similarity=0.70,
            )
            for r in results:
                name = _normalize_name(r.get('nome', ''))
                kg_type = 'cliente' if entity_type_search == 'customer' else 'fornecedor'
                if name:
                    entities.append((kg_type, name, r.get('cnpj_raiz', '')))
    except Exception as e:
        logger.debug(f"[KG] Entity search falhou (ignorado): {e}")

    # --- Produtos ---
    try:
        from app.embeddings.product_search import buscar_produtos_hibrido
        products = buscar_produtos_hibrido(
            search_text,
            modo='semantica',
            limite=3,
            min_similarity=0.70,
        )
        for p in products:
            name = _normalize_name(p.get('descricao', ''))
            if name:
                entities.append(('produto', name, str(p.get('cod_produto', ''))))
    except Exception as e:
        logger.debug(f"[KG] Product search falhou (ignorado): {e}")

    return entities


# =====================================================================
# LAYER 3: PARSE DA RESPOSTA HAIKU (piggyback no contextual retrieval)
# =====================================================================

def parse_contextual_response(text: str) -> Tuple[Optional[str], List[Tuple[str, str]], List[Tuple[str, str, str]]]:
    """
    Parse resposta Haiku no formato estruturado (T3-3).

    Formato esperado:
        CONTEXTO: 1-2 frases de contexto
        ENTIDADES: tipo:nome|tipo:nome
        RELACOES: origem>tipo>destino|origem>tipo>destino

    Fallback: se parse falhar, tudo vira contexto (compatibilidade T3-1).

    Args:
        text: Resposta do Haiku

    Returns:
        Tupla (contexto, entidades, relações)
        - contexto: str ou None
        - entidades: [(tipo, nome), ...]
        - relações: [(origem, tipo_relacao, destino), ...]
    """
    if not text or not text.strip():
        return None, [], []

    context = None
    entities: List[Tuple[str, str]] = []
    relations: List[Tuple[str, str, str]] = []

    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith('CONTEXTO:'):
            context = line[len('CONTEXTO:'):].strip()

        elif line.upper().startswith('ENTIDADES:'):
            raw = line[len('ENTIDADES:'):].strip()
            if 'nenhuma' in raw.lower():
                continue
            for part in raw.split('|'):
                part = part.strip()
                if ':' in part:
                    parts = part.split(':', 1)
                    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                        entities.append((parts[0].strip().lower(), parts[1].strip()))

        elif line.upper().startswith('RELACOES:') or line.upper().startswith('RELAÇÕES:'):
            raw = line.split(':', 1)[1].strip() if ':' in line else ''
            if 'nenhuma' in raw.lower():
                continue
            for part in raw.split('|'):
                part = part.strip()
                if '>' in part:
                    parts = part.split('>')
                    if len(parts) == 3 and all(p.strip() for p in parts):
                        relations.append((
                            parts[0].strip(),
                            parts[1].strip().lower(),
                            parts[2].strip(),
                        ))

    # Fallback: se contexto não encontrado, tudo é contexto
    if context is None:
        context = text.strip()

    return context, entities, relations


# =====================================================================
# WRITE PATH: Upsert de entidades e links
# =====================================================================

def _upsert_entity(
    conn,
    user_id: int,
    entity_type: str,
    entity_name: str,
    entity_key: Optional[str] = None,
) -> int:
    """
    Cria ou atualiza entidade no grafo. Retorna entity_id.

    Usa INSERT ON CONFLICT para atomicidade.
    """
    from sqlalchemy import text

    entity_name_norm = _normalize_name(entity_name)
    if not entity_name_norm:
        return 0

    now = agora_utc_naive()

    result = conn.execute(text("""
        INSERT INTO agent_memory_entities
            (user_id, entity_type, entity_name, entity_key, mention_count, first_seen_at, last_seen_at)
        VALUES
            (:user_id, :entity_type, :entity_name, :entity_key, 1, :now, :now)
        ON CONFLICT ON CONSTRAINT uq_user_entity
        DO UPDATE SET
            mention_count = agent_memory_entities.mention_count + 1,
            last_seen_at = :now,
            entity_key = COALESCE(EXCLUDED.entity_key, agent_memory_entities.entity_key)
        RETURNING id
    """), {
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_name": entity_name_norm,
        "entity_key": entity_key or None,
        "now": now,
    })

    row = result.fetchone()
    return row[0] if row else 0


def _link_entity_to_memory(
    conn,
    entity_id: int,
    memory_id: int,
    relation_type: str = 'mentions',
) -> None:
    """Cria link entre entidade e memória (idempotente)."""
    from sqlalchemy import text

    if not entity_id or not memory_id:
        return

    conn.execute(text("""
        INSERT INTO agent_memory_entity_links (entity_id, memory_id, relation_type, created_at)
        VALUES (:entity_id, :memory_id, :relation_type, :now)
        ON CONFLICT ON CONSTRAINT uq_entity_memory_link DO NOTHING
    """), {
        "entity_id": entity_id,
        "memory_id": memory_id,
        "relation_type": relation_type,
        "now": agora_utc_naive(),
    })


def _upsert_relation(
    conn,
    source_entity_id: int,
    target_entity_id: int,
    relation_type: str = 'co_occurs',
    weight: float = 1.0,
    memory_id: Optional[int] = None,
) -> None:
    """Cria ou atualiza relação entre entidades (idempotente)."""
    from sqlalchemy import text

    if not source_entity_id or not target_entity_id:
        return
    if source_entity_id == target_entity_id:
        return  # Sem self-loops

    conn.execute(text("""
        INSERT INTO agent_memory_entity_relations
            (source_entity_id, target_entity_id, relation_type, weight, memory_id, created_at)
        VALUES
            (:source_id, :target_id, :relation_type, :weight, :memory_id, :now)
        ON CONFLICT ON CONSTRAINT uq_entity_relation
        DO UPDATE SET
            weight = agent_memory_entity_relations.weight + :weight,
            memory_id = COALESCE(EXCLUDED.memory_id, agent_memory_entity_relations.memory_id)
    """), {
        "source_id": source_entity_id,
        "target_id": target_entity_id,
        "relation_type": relation_type,
        "weight": weight,
        "memory_id": memory_id,
        "now": agora_utc_naive(),
    })


def extract_and_link_entities(
    user_id: int,
    memory_id: int,
    content: str,
    haiku_entities: Optional[List[Tuple[str, str]]] = None,
    haiku_relations: Optional[List[Tuple[str, str, str]]] = None,
) -> Dict:
    """
    Extrai entidades de uma memória e cria links no grafo.

    Chamado por memory_mcp_tool.py após save/update.
    Best-effort: falhas são silenciosas.

    Pipeline:
    1. Layer 1: regex → entidades estruturais
    2. Layer 2: Voyage → entidades semânticas
    3. Layer 3: merge com haiku_entities (passadas do _generate_memory_context)
    4. Upsert entidades + links + relações

    Args:
        user_id: ID do usuário
        memory_id: ID da memória no banco
        content: Conteúdo da memória
        haiku_entities: Entidades extraídas pelo Haiku [(tipo, nome), ...]
        haiku_relations: Relações extraídas pelo Haiku [(origem, tipo, destino), ...]

    Returns:
        Dict com estatísticas {entities_count, links_count, relations_count}
    """
    from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
    if not MEMORY_KNOWLEDGE_GRAPH:
        return {'entities_count': 0, 'links_count': 0, 'relations_count': 0}

    stats = {'entities_count': 0, 'links_count': 0, 'relations_count': 0}

    try:
        from app import db

        # === Layer 1: Regex ===
        regex_entities = _extract_entities_regex(content)

        # === Layer 2: Voyage (best-effort, timeout 3s) ===
        voyage_entities: List[Tuple[str, str, Optional[str]]] = []
        try:
            voyage_entities = _extract_entities_voyage(content)
        except Exception as e:
            logger.debug(f"[KG] Layer 2 Voyage falhou (ignorado): {e}")

        # === Layer 3: Merge com Haiku ===
        # Converter haiku_entities para formato unificado (tipo, nome, key=None)
        haiku_converted: List[Tuple[str, str, Optional[str]]] = []
        if haiku_entities:
            for etype, ename in haiku_entities:
                haiku_converted.append((etype.lower(), ename, None))

        # === Deduplicate por (tipo, nome_normalizado) ===
        seen: Set[Tuple[str, str]] = set()
        all_entities: List[Tuple[str, str, Optional[str]]] = []

        for source_entities in [regex_entities, voyage_entities, haiku_converted]:
            for etype, ename, ekey in source_entities:
                norm_name = _normalize_name(ename)
                dedup_key = (etype, norm_name)
                if dedup_key not in seen and norm_name:
                    seen.add(dedup_key)
                    all_entities.append((etype, ename, ekey))

        if not all_entities:
            return stats

        # === Upsert no banco ===
        entity_id_map: Dict[str, int] = {}  # nome_normalizado → entity_id

        with db.engine.begin() as conn:
            # Upsert entidades
            for etype, ename, ekey in all_entities:
                eid = _upsert_entity(conn, user_id, etype, ename, ekey)
                if eid:
                    entity_id_map[_normalize_name(ename)] = eid
                    stats['entities_count'] += 1

            # Link entidades → memória
            for eid in entity_id_map.values():
                _link_entity_to_memory(conn, eid, memory_id, 'mentions')
                stats['links_count'] += 1

            # Relações do Haiku
            if haiku_relations:
                for source_name, rel_type, target_name in haiku_relations:
                    source_norm = _normalize_name(source_name)
                    target_norm = _normalize_name(target_name)
                    source_id = entity_id_map.get(source_norm)
                    target_id = entity_id_map.get(target_norm)

                    # Se entidade não foi criada acima, tentar criar agora
                    if not source_id:
                        source_id = _upsert_entity(conn, user_id, 'regra', source_name)
                        if source_id:
                            entity_id_map[source_norm] = source_id
                            _link_entity_to_memory(conn, source_id, memory_id, 'mentions')
                    if not target_id:
                        target_id = _upsert_entity(conn, user_id, 'regra', target_name)
                        if target_id:
                            entity_id_map[target_norm] = target_id
                            _link_entity_to_memory(conn, target_id, memory_id, 'mentions')

                    if source_id and target_id:
                        _upsert_relation(conn, source_id, target_id, rel_type, 1.0, memory_id)
                        stats['relations_count'] += 1

            # Co-occurrence: pares de entidades na mesma memória
            # Cap em 10 entidades para evitar explosão quadrática:
            # 10 entidades → 45 pares (aceitável), 30 → 435 pares (excessivo)
            _MAX_CO_OCCURS_ENTITIES = 10
            entity_ids = list(entity_id_map.values())
            if len(entity_ids) >= 2:
                co_ids = entity_ids[:_MAX_CO_OCCURS_ENTITIES]
                for i in range(len(co_ids)):
                    for j in range(i + 1, len(co_ids)):
                        _upsert_relation(
                            conn,
                            co_ids[i], co_ids[j],
                            'co_occurs', 0.5, memory_id,
                        )
                        stats['relations_count'] += 1

        logger.debug(
            f"[KG] Extracted for memory_id={memory_id}: "
            f"{stats['entities_count']} entities, "
            f"{stats['links_count']} links, "
            f"{stats['relations_count']} relations"
        )

    except Exception as e:
        logger.debug(f"[KG] extract_and_link_entities falhou: {e}")

    return stats


# =====================================================================
# DELETE PATH: Cleanup ao deletar memória
# =====================================================================

def remove_memory_links(memory_id: int) -> int:
    """
    Remove links de uma memória no grafo.

    FK CASCADE em entity_links.memory_id cuida da remoção automática,
    mas chamamos explicitamente para tracking.

    Args:
        memory_id: ID da memória sendo deletada

    Returns:
        Número de links removidos
    """
    try:
        from app import db
        from sqlalchemy import text

        with db.engine.begin() as conn:
            result = conn.execute(text("""
                DELETE FROM agent_memory_entity_links
                WHERE memory_id = :memory_id
            """), {"memory_id": memory_id})

            count = result.rowcount
            if count > 0:
                logger.debug(f"[KG] Removed {count} links for memory_id={memory_id}")
            return count

    except Exception as e:
        logger.debug(f"[KG] remove_memory_links falhou: {e}")
        return 0


# =====================================================================
# READ PATH: Query do grafo para retrieval
# =====================================================================

def query_graph_memories(
    user_id: int,
    prompt: str,
    exclude_memory_ids: Optional[Set[int]] = None,
    limit: int = 10,
) -> List[Dict]:
    """
    Busca memórias via knowledge graph a partir do prompt.

    Pipeline:
    1. Extrai entidades do prompt (Layer 1 regex + Layer 2 Voyage)
    2. Busca entity_ids por (user_id, entity_type, entity_name)
    3. Busca memory_ids via entity_links
    4. Filtra: exclui exclude_memory_ids (já encontradas por semântica)
    5. Retorna com similarity proxy = 0.5

    Args:
        user_id: ID do usuário
        prompt: Prompt do usuário (texto de busca)
        exclude_memory_ids: IDs a excluir (já retornados pela busca semântica)
        limit: Máximo de resultados

    Returns:
        Lista de dicts [{memory_id, similarity, source}]
    """
    from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
    if not MEMORY_KNOWLEDGE_GRAPH:
        return []

    if not prompt or not prompt.strip():
        return []

    try:
        from app import db
        from sqlalchemy import text

        # Extrair entidades do prompt
        prompt_entities = _extract_entities_regex(prompt)

        # Layer 2 para o prompt (best-effort)
        try:
            voyage_entities = _extract_entities_voyage(prompt)
            prompt_entities.extend(voyage_entities)
        except Exception:
            pass

        if not prompt_entities:
            return []

        # Normalizar nomes
        entity_names = list(set(
            _normalize_name(ename) for _, ename, _ in prompt_entities
            if _normalize_name(ename)
        ))

        if not entity_names:
            return []

        # Buscar entity_ids para o user
        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, entity_name
                FROM agent_memory_entities
                WHERE user_id = :user_id
                  AND entity_name = ANY(:names)
            """), {"user_id": user_id, "names": entity_names})

            entity_rows = result.fetchall()
            if not entity_rows:
                return []

            entity_ids = [row[0] for row in entity_rows]

            # Buscar memory_ids via links
            result = conn.execute(text("""
                SELECT DISTINCT memory_id
                FROM agent_memory_entity_links
                WHERE entity_id = ANY(:entity_ids)
                ORDER BY memory_id DESC
                LIMIT :limit
            """), {"entity_ids": entity_ids, "limit": limit * 2})

            memory_rows = result.fetchall()
            if not memory_rows:
                return []

            # Filtrar excluídos
            exclude = exclude_memory_ids or set()
            graph_results = []
            for row in memory_rows:
                mid = row[0]
                if mid not in exclude:
                    graph_results.append({
                        'memory_id': mid,
                        'similarity': 0.5,  # Proxy score para graph results
                        'source': 'graph',
                    })
                    if len(graph_results) >= limit:
                        break

            logger.debug(
                f"[KG] Graph query for user_id={user_id}: "
                f"{len(entity_names)} entity names → "
                f"{len(entity_ids)} entity_ids → "
                f"{len(graph_results)} memories"
            )

            return graph_results

    except Exception as e:
        logger.debug(f"[KG] query_graph_memories falhou: {e}")
        return []


# =====================================================================
# STATS: Métricas do grafo
# =====================================================================

def get_graph_stats(user_id: Optional[int] = None) -> Dict:
    """
    Retorna estatísticas do knowledge graph.

    Args:
        user_id: Filtrar por usuário (None = todos)

    Returns:
        Dict com total_entities, total_links, total_relations,
        entities_by_type, top_entities
    """
    try:
        from app import db
        from sqlalchemy import text

        user_filter = "WHERE user_id = :user_id" if user_id else ""
        params = {"user_id": user_id} if user_id else {}

        with db.engine.connect() as conn:
            # Total entidades
            total_entities = conn.execute(text(f"""
                SELECT COUNT(*) FROM agent_memory_entities {user_filter}
            """), params).scalar() or 0

            # Total links
            if user_id:
                total_links = conn.execute(text("""
                    SELECT COUNT(*) FROM agent_memory_entity_links l
                    JOIN agent_memory_entities e ON l.entity_id = e.id
                    WHERE e.user_id = :user_id
                """), params).scalar() or 0
            else:
                total_links = conn.execute(text(
                    "SELECT COUNT(*) FROM agent_memory_entity_links"
                )).scalar() or 0

            # Total relações
            if user_id:
                total_relations = conn.execute(text("""
                    SELECT COUNT(*) FROM agent_memory_entity_relations r
                    JOIN agent_memory_entities e ON r.source_entity_id = e.id
                    WHERE e.user_id = :user_id
                """), params).scalar() or 0
            else:
                total_relations = conn.execute(text(
                    "SELECT COUNT(*) FROM agent_memory_entity_relations"
                )).scalar() or 0

            # Entidades por tipo
            result = conn.execute(text(f"""
                SELECT entity_type, COUNT(*) as cnt
                FROM agent_memory_entities {user_filter}
                GROUP BY entity_type
                ORDER BY cnt DESC
            """), params)
            entities_by_type = {row[0]: row[1] for row in result.fetchall()}

            # Top entidades (mais mencionadas)
            result = conn.execute(text(f"""
                SELECT entity_type, entity_name, mention_count
                FROM agent_memory_entities {user_filter}
                ORDER BY mention_count DESC
                LIMIT 20
            """), params)
            top_entities = [
                {'type': row[0], 'name': row[1], 'mentions': row[2]}
                for row in result.fetchall()
            ]

            return {
                'total_entities': total_entities,
                'total_links': total_links,
                'total_relations': total_relations,
                'entities_by_type': entities_by_type,
                'top_entities': top_entities,
            }

    except Exception as e:
        logger.debug(f"[KG] get_graph_stats falhou: {e}")
        return {
            'total_entities': 0,
            'total_links': 0,
            'total_relations': 0,
            'entities_by_type': {},
            'top_entities': [],
            'error': str(e),
        }


# =====================================================================
# GC: Cleanup de entidades órfãs
# =====================================================================

def cleanup_orphan_entities(user_id: Optional[int] = None) -> int:
    """
    Remove entidades que não têm mais links para memórias.

    Chamado periodicamente (cron ou manual).

    Args:
        user_id: Filtrar por usuário (None = todos)

    Returns:
        Número de entidades removidas
    """
    try:
        from app import db
        from sqlalchemy import text

        user_clause = "AND e.user_id = :user_id" if user_id else ""
        params = {"user_id": user_id} if user_id else {}

        with db.engine.begin() as conn:
            result = conn.execute(text(f"""
                DELETE FROM agent_memory_entities e
                WHERE NOT EXISTS (
                    SELECT 1 FROM agent_memory_entity_links l
                    WHERE l.entity_id = e.id
                )
                {user_clause}
            """), params)

            count = result.rowcount
            if count > 0:
                logger.info(f"[KG] Cleaned up {count} orphan entities (user_id={user_id})")
            return count

    except Exception as e:
        logger.debug(f"[KG] cleanup_orphan_entities falhou: {e}")
        return 0
