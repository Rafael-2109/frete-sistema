"""
Knowledge Graph Service — T3-3: Extração, linking e query de entidades em memórias.

3 Layers de extração:
  Layer 1: Regex (~2ms) — UF, pedido, CNPJ, valor
  Layer 2: Voyage Semantic Search (~300ms) — transportadora, produto, cliente, fornecedor
  Layer 3: Sonnet (0ms extra) — relações semânticas (piggyback no contextual retrieval)

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

# Hop 2 traversal limits
_HOP2_MAX_RELATED_ENTITIES = 15
_HOP2_MAX_MEMORIES = 5
_HOP2_SIMILARITY_FACTOR = 0.3
_HOP2_SIMILARITY_CAP = 0.5

# Vocabulário controlado de entity_types (auditoria 2026-03-23)
_VALID_ENTITY_TYPES = frozenset({
    'uf', 'pedido', 'cnpj', 'valor', 'transportadora', 'produto',
    'cliente', 'fornecedor', 'usuario', 'processo', 'conceito',
    'campo', 'termo',
})

# Vocabulário controlado de relation_types (auditoria 2026-03-23)
_VALID_RELATION_TYPES = frozenset({
    'pertence_a', 'depende_de', 'substitui', 'conflita_com',
    'precede', 'bloqueia', 'usa', 'produz', 'fornece', 'consome',
    'localizado_em', 'responsavel_por', 'corrige', 'requer',
    'complementa', 'atrasa_para', 'co_occurs',
    'resolves_to',  # Routing: termo ambíguo → domínio/skill resolvido
})

# Mapeamento de sinônimos para normalização de relation_types
_RELATION_SYNONYMS = {
    'pertence': 'pertence_a', 'parte_de': 'pertence_a', 'faz_parte_de': 'pertence_a',
    'pertence_ao': 'pertence_a', 'pertence_ao_setor': 'pertence_a',
    'depende': 'depende_de', 'requer_campo': 'requer', 'exige': 'requer',
    'obrigatorio_para': 'requer', 'exige_correspondencia': 'requer',
    'substitui_por': 'substitui', 'converte': 'substitui', 'converte_para': 'substitui',
    'conflita': 'conflita_com', 'contradiz_escolha': 'conflita_com',
    'nao_corresponde_a': 'conflita_com', 'distinto_de': 'conflita_com',
    'precede_a': 'precede', 'antecede': 'precede', 'transiciona_para': 'precede',
    'transita_para': 'precede', 'transita': 'precede', 'sequencia': 'precede',
    'evolui_para': 'precede', 'transiciona_de': 'precede',
    'bloqueia_sem': 'bloqueia', 'dificulta': 'bloqueia',
    'usa_formato': 'usa', 'utiliza_formato': 'usa', 'usa_variacao': 'usa',
    'le_de': 'usa', 'consulta': 'usa', 'referencia': 'usa',
    'produz_resultado': 'produz', 'gera': 'produz', 'origina': 'produz',
    'confirmacao_gera': 'produz', 'dispara': 'produz',
    'fornece_a': 'fornece', 'entrega_em': 'fornece',
    'consome_de': 'consome',
    'localizado': 'localizado_em', 'localiza_em': 'localizado_em',
    'presente_em': 'localizado_em', 'opera_em': 'localizado_em',
    'responsavel': 'responsavel_por', 'executa': 'responsavel_por',
    'realiza': 'responsavel_por', 'opera': 'responsavel_por',
    'atua_em': 'responsavel_por', 'trabalha_em': 'responsavel_por',
    'corrige_de': 'corrige', 'corrigido_de': 'corrige', 'resolve': 'corrige',
    'complementa_a': 'complementa', 'relaciona_com': 'complementa',
    'integra': 'complementa', 'vincula': 'complementa', 'vincula_a': 'complementa',
    'relaciona': 'complementa', 'associada_a': 'complementa',
    'atrasa': 'atrasa_para', 'demora_para': 'atrasa_para',
    # Tipos sem mapeamento claro -> None (descartar)
    'co_occurs': 'co_occurs',
}


def _normalize_relation_type(raw_type: str) -> Optional[str]:
    """
    Normaliza um tipo de relação para o vocabulário controlado.
    Retorna None se não for mapeável (descarta a relação).
    """
    if not raw_type:
        return None
    normalized = raw_type.strip().lower()
    if normalized in _VALID_RELATION_TYPES:
        return normalized
    if normalized in _RELATION_SYNONYMS:
        return _RELATION_SYNONYMS[normalized]
    return None


def _validate_entity_type(raw_type: str) -> Optional[str]:
    """
    Valida tipo de entidade contra vocabulário controlado.
    Retorna None se tipo inválido.
    """
    if not raw_type:
        return None
    normalized = raw_type.strip().lower()
    if normalized in _VALID_ENTITY_TYPES:
        return normalized
    # Sinônimos comuns
    _entity_synonyms = {
        'regra': None,  # "regra" era catch-all, descartar
        'regra_negocio': 'processo',
        'sistema': 'conceito',
        'setor': 'conceito',
        'cargo': 'conceito',
    }
    return _entity_synonyms.get(normalized)


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

def strip_xml_tags(content: str) -> str:
    """
    Remove tags XML/HTML, retornando texto puro.

    Usado para:
    - Regex extraction (KG Layer 1): evitar que tags poluam patterns
    - Fragment matching (effective_count): comparar texto puro vs resposta

    NOTA: Entidades XML (&amp;, &gt;, etc.) NÃO são decodificadas.
    Para comparação/dedup, usar clean_for_comparison() que inclui html.unescape().

    >>> strip_xml_tags('<memoria type="correcao"><content>SP bom</content></memoria>')
    'SP bom'
    >>> strip_xml_tags('texto sem tags')
    'texto sem tags'
    """
    if not content:
        return ''
    # Remove tags, preservando o texto entre elas
    cleaned = re.sub(r'<[^>]+>', ' ', content)
    # Normaliza espacos multiplos
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def clean_for_comparison(content: str) -> str:
    """
    Strip XML tags e decodifica entidades → texto puro para comparação.

    Combina strip_xml_tags() + html.unescape() para garantir que entidades
    XML (&amp;, &gt;, &lt;, &quot;, &apos;) não poluam embeddings nem
    comparações textuais.

    Usar em TODOS os pontos de comparação/dedup. strip_xml_tags() sozinha
    mantém entidades — causa assimetria cross-pipeline (extração com
    _xml_escape vs MCP tool sem escape).

    >>> clean_for_comparison('<tag>saldo &gt; 0 &amp; ativo</tag>')
    'saldo > 0 & ativo'
    >>> clean_for_comparison('texto sem tags')
    'texto sem tags'
    >>> clean_for_comparison('<x>&apos;teste&apos;</x>')
    "'teste'"
    """
    import html
    return html.unescape(strip_xml_tags(content))


def _extract_entities_regex(content: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Extrai entidades estruturadas via regex.

    Returns:
        Lista de tuplas (entity_type, entity_name, entity_key)
    """
    if not content:
        return []

    # Strip XML tags para regex operar em texto puro (fix KG morto — PRD v2.1 Fase 4)
    content = strip_xml_tags(content)

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
# LAYER 3: PARSE DA RESPOSTA LLM (piggyback no contextual retrieval)
# =====================================================================

def parse_contextual_response(text: str) -> Tuple[Optional[str], List[Tuple[str, str]], List[Tuple[str, str, str]]]:
    """
    Parse resposta do contextual retrieval (Sonnet) no formato estruturado (T3-3).

    Formato esperado (v2 — com relevancia/confianca opcionais):
        CONTEXTO: 1-2 frases de contexto
        ENTIDADES: tipo:nome:E|tipo:nome:A   (E=essencial, A=acidental — opcional)
        RELACOES: origem>tipo>destino:alta    (alta/media/baixa — opcional)

    Backward-compatible: formato sem flags (tipo:nome, origem>tipo>destino) continua funcionando.
    Fallback: se parse falhar, tudo vira contexto (compatibilidade T3-1).

    Args:
        text: Resposta do LLM

    Returns:
        Tupla (contexto, entidades, relações)
        - contexto: str ou None
        - entidades: [(tipo, nome), ...] — nome pode conter sufixo de relevancia
        - relações: [(origem, tipo_relacao, destino), ...] — destino pode conter sufixo de confianca
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
                    etype, rest = part.split(':', 1)
                    etype = etype.strip().lower()
                    rest = rest.strip()
                    if not etype or not rest:
                        continue
                    # v2: relevancia flag (E=essencial, A=acidental) — opcional
                    # Verifica se o ULTIMO segmento apos ':' e flag de relevancia
                    ename = rest
                    if ':' in rest:
                        name_part, maybe_flag = rest.rsplit(':', 1)
                        if maybe_flag.strip().upper() in ('E', 'A'):
                            # Sufixar relevancia ao nome para downstream processing
                            # KG save_entities pode usar isso para ajustar mention_count
                            ename = f"{name_part.strip()}:{maybe_flag.strip().upper()}"
                        # else: ':' faz parte do nome (ex: prioridade:alta)
                    entities.append((etype, ename))

        elif line.upper().startswith('RELACOES:') or line.upper().startswith('RELAÇÕES:'):
            raw = line.split(':', 1)[1].strip() if ':' in line else ''
            if 'nenhuma' in raw.lower():
                continue
            for part in raw.split('|'):
                part = part.strip()
                if '>' in part:
                    parts = part.split('>')
                    if len(parts) == 3 and all(p.strip() for p in parts):
                        destino = parts[2].strip()
                        # v2: confianca suffix (alta/media/baixa) — opcional
                        if ':' in destino:
                            dest_parts = destino.rsplit(':', 1)
                            if dest_parts[1].strip().lower() in ('alta', 'media', 'baixa'):
                                destino = f"{dest_parts[0].strip()}:{dest_parts[1].strip().lower()}"
                        relations.append((
                            parts[0].strip(),
                            parts[1].strip().lower(),
                            destino,
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
    3. Layer 3: merge com haiku_entities (nomes históricos; extraídos por Sonnet via _generate_memory_context)
    4. Upsert entidades + links + relações

    Args:
        user_id: ID do usuário
        memory_id: ID da memória no banco
        content: Conteúdo da memória
        haiku_entities: Entidades extraídas pelo LLM [(tipo, nome), ...] (nome histórico; atualmente Sonnet)
        haiku_relations: Relações extraídas pelo LLM [(origem, tipo, destino), ...] (nome histórico; atualmente Sonnet)

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

        # === Layer 3: Merge com LLM output (parâmetros haiku_* são nomes históricos) ===
        # Converter haiku_entities para formato unificado (tipo, nome, key=None)
        # Validar entity_type contra vocabulário controlado
        haiku_converted: List[Tuple[str, str, Optional[str]]] = []
        if haiku_entities:
            for etype, ename in haiku_entities:
                validated_type = _validate_entity_type(etype)
                if validated_type:
                    haiku_converted.append((validated_type, ename, None))
                else:
                    logger.debug(f"[KG] Entidade descartada (tipo '{etype}' invalido): {ename}")

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

            # Relações do LLM (parâmetros haiku_* são nomes históricos)
            if haiku_relations:
                for source_name, rel_type, target_name in haiku_relations:
                    # Normalizar relation_type contra vocabulário controlado
                    normalized_rel = _normalize_relation_type(rel_type)
                    if not normalized_rel:
                        logger.debug(
                            f"[KG] Relação descartada (tipo '{rel_type}' não mapeável): "
                            f"{source_name}>{rel_type}>{target_name}"
                        )
                        continue

                    source_norm = _normalize_name(source_name)
                    target_norm = _normalize_name(target_name)
                    source_id = entity_id_map.get(source_norm)
                    target_id = entity_id_map.get(target_norm)

                    # Se entidade não foi criada acima, tentar criar com tipo 'conceito'
                    # (antes: fallback 'regra' gerava 72% das entidades como genérico)
                    if not source_id:
                        source_id = _upsert_entity(conn, user_id, 'conceito', source_name)
                        if source_id:
                            entity_id_map[source_norm] = source_id
                            _link_entity_to_memory(conn, source_id, memory_id, 'mentions')
                    if not target_id:
                        target_id = _upsert_entity(conn, user_id, 'conceito', target_name)
                        if target_id:
                            entity_id_map[target_norm] = target_id
                            _link_entity_to_memory(conn, target_id, memory_id, 'mentions')

                    if source_id and target_id:
                        _upsert_relation(conn, source_id, target_id, normalized_rel, 1.0, memory_id)
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
    Busca memórias via knowledge graph a partir do prompt (2-hop traversal).

    Pipeline:
    1. Extrai entidades do prompt (Layer 1 regex + Layer 2 Voyage)
    2. Busca entity_ids por (user_id, entity_type, entity_name)
    3. HOP 1: Busca memory_ids via entity_links (match direto)
    4. HOP 2: Busca related_entity_ids via entity_relations → memory_ids adicionais
    5. Combina hop 1 + hop 2, filtrando duplicatas e exclude_memory_ids

    Hop 2 usa queries separadas com try/except próprio — se falhar, hop 1 é preservado.

    Args:
        user_id: ID do usuário
        prompt: Prompt do usuário (texto de busca)
        exclude_memory_ids: IDs a excluir (já retornados pela busca semântica)
        limit: Máximo de resultados hop 1

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

        # Buscar entity_ids para o user (PRD v2.1: incluir user_id=0 para empresa)
        user_ids = [user_id, 0] if user_id != 0 else [0]
        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, entity_name
                FROM agent_memory_entities
                WHERE user_id = ANY(:user_ids)
                  AND entity_name = ANY(:names)
            """), {"user_ids": user_ids, "names": entity_names})

            entity_rows = result.fetchall()
            if not entity_rows:
                return []

            entity_ids = [row[0] for row in entity_rows]

            # ── HOP 1: memory_ids via entity_links (match direto) ──
            result = conn.execute(text("""
                SELECT DISTINCT memory_id
                FROM agent_memory_entity_links
                WHERE entity_id = ANY(:entity_ids)
                ORDER BY memory_id DESC
                LIMIT :limit
            """), {"entity_ids": entity_ids, "limit": limit * 2})

            hop1_memory_ids = {row[0] for row in result.fetchall()}

            # Construir resultados hop 1
            exclude = exclude_memory_ids or set()
            graph_results = []
            for mid in sorted(hop1_memory_ids, reverse=True):
                if mid not in exclude:
                    graph_results.append({
                        'memory_id': mid,
                        # Design decision (GAP 11): 0.5 = proxy neutro para graph results.
                        # Graph results são link-based (não vetoriais), sem cosine similarity real.
                        # No composite scoring (0.3*decay + 0.3*importance + 0.4*similarity),
                        # 0.5 garante que graph results competem de forma justa com resultados semânticos.
                        'similarity': 0.5,
                        'source': 'graph',
                    })
                    if len(graph_results) >= limit:
                        break

            # ── HOP 2: related entities via relations ──
            # try/except independente — falha não afeta hop 1
            hop2_count = 0
            try:
                # Query 1: Buscar related_entity_ids (bidirecional, excluindo entity_ids originais)
                # ORDER BY max_weight DESC para priorizar relações mais fortes
                result = conn.execute(text("""
                    SELECT entity_id, MAX(weight) as max_weight
                    FROM (
                        SELECT target_entity_id AS entity_id, weight
                        FROM agent_memory_entity_relations
                        WHERE source_entity_id = ANY(:entity_ids)
                        UNION ALL
                        SELECT source_entity_id AS entity_id, weight
                        FROM agent_memory_entity_relations
                        WHERE target_entity_id = ANY(:entity_ids)
                    ) sub
                    WHERE NOT (entity_id = ANY(:entity_ids))
                    GROUP BY entity_id
                    ORDER BY max_weight DESC
                    LIMIT :max_entities
                """), {
                    "entity_ids": entity_ids,
                    "max_entities": _HOP2_MAX_RELATED_ENTITIES,
                })

                related_rows = result.fetchall()

                if related_rows:
                    # Mapa: related_entity_id → max_weight
                    related_entity_weights: Dict[int, float] = {
                        row[0]: row[1] for row in related_rows
                    }
                    related_entity_ids = list(related_entity_weights.keys())

                    # Query 2: Buscar memory_ids candidatos linkados aos related_entity_ids
                    # Busca 3x o limite para ter margem após filtrar excluídos
                    result = conn.execute(text("""
                        SELECT DISTINCT memory_id
                        FROM agent_memory_entity_links
                        WHERE entity_id = ANY(:related_entity_ids)
                        ORDER BY memory_id DESC
                        LIMIT :max_memories
                    """), {
                        "related_entity_ids": related_entity_ids,
                        "max_memories": _HOP2_MAX_MEMORIES * 3,
                    })

                    hop2_candidate_mids = [row[0] for row in result.fetchall()]

                    if hop2_candidate_mids:
                        # Query 3: Mapear entity_id → memory_id para calcular weight por memória
                        result = conn.execute(text("""
                            SELECT entity_id, memory_id
                            FROM agent_memory_entity_links
                            WHERE entity_id = ANY(:related_entity_ids)
                              AND memory_id = ANY(:memory_ids)
                        """), {
                            "related_entity_ids": related_entity_ids,
                            "memory_ids": hop2_candidate_mids,
                        })

                        # Calcular max weight por memória (a memória pode linkar a
                        # múltiplas entidades relacionadas — usamos o maior peso)
                        memory_max_weight: Dict[int, float] = {}
                        for eid, mid in result.fetchall():
                            w = related_entity_weights.get(eid, 0.0)
                            if mid not in memory_max_weight or w > memory_max_weight[mid]:
                                memory_max_weight[mid] = w

                        # IDs a excluir do hop 2: já em hop 1 + exclude_memory_ids
                        hop2_exclude = hop1_memory_ids | exclude

                        for mid in hop2_candidate_mids:
                            if mid in hop2_exclude:
                                continue
                            if hop2_count >= _HOP2_MAX_MEMORIES:
                                break

                            max_w = memory_max_weight.get(mid, 0.5)
                            similarity = min(
                                _HOP2_SIMILARITY_CAP,
                                _HOP2_SIMILARITY_FACTOR * max_w,
                            )

                            graph_results.append({
                                'memory_id': mid,
                                'similarity': round(similarity, 4),
                                'source': 'graph',
                            })
                            hop2_count += 1

            except Exception as e:
                logger.debug(f"[KG_QUERY] Hop 2 falhou (hop 1 preservado): {e}")

            logger.debug(
                f"[KG_QUERY] user_id={user_id}: "
                f"entities_found={len(entity_ids)}, "
                f"hop1_memories={len(hop1_memory_ids)}, "
                f"hop2_memories={hop2_count}"
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
