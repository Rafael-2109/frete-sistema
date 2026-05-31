"""
Context Enrichment — Onda 4 (F4/F5 + D5).

F4/F5 — Skill Hints Advisory (AGENT_SKILL_RAG)
-----------------------------------------------
Aconselha o agente quais skills são mais relevantes para o turno atual.
Injetado como bloco <skill_hints priority="advisory"> no hook UserPromptSubmit.

LIMITAÇÃO ARQUITETURAL DO SDK (documentada):
  O SDK fixa `skills=` no connect() e não expõe set_skills() por turno.
  Portanto, NÃO é possível filtrar o listing real de skills por turno.
  Esta implementação é ADVISORY: informa o agente quais skills são mais
  relevantes, mas não altera o listing visível na meta-tool Skill.
  Evoluir para filtro real quando/se o SDK expuser `set_skills()`.

D5 — World Model Injection (AGENT_WORLD_MODEL_INJECT)
------------------------------------------------------
Injeta entidades canônicas da ontologia (D4 query_ontology_entities) como
bloco <world_model priority="advisory"> no mesmo hook.

Este bloco é ADITIVO: _DOMAIN_KEYWORDS em memory_injection.py permanece
como fallback cold-start. D5 NÃO remove nem substitui o routing_context
existente — apenas adiciona entidades canônicas quando a ontologia tem dados.

Todas as funções são best-effort: exceções internas retornam None/[]
sem propagar para o hook (que NUNCA deve quebrar).

Flags:
  USE_AGENT_SKILL_RAG         (AGENT_SKILL_RAG, default false)
  USE_AGENT_WORLD_MODEL_INJECT (AGENT_WORLD_MODEL_INJECT, default false)
"""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger("sistema_fretes")

# Importação de módulos externos — lazy dentro das funções para tolerância
# a contextos sem Flask app (testes unitários, importação parcial).
# O módulo capability_registry é importado no nível de módulo para permitir
# monkeypatch direto em testes (ver test_context_enrichment.py).
from app.agente.config import capability_registry  # noqa: E402

# query_ontology_entities importada no nível de módulo para monkeypatch em testes.
# Segue o mesmo padrão de plan_triage.py.
from app.agente.tools.ontology_query_tool import query_ontology_entities  # noqa: E402


# ---------------------------------------------------------------------------
# F4/F5 — rank_skills_for_query
# ---------------------------------------------------------------------------

def rank_skills_for_query(query: str, limit: int = 8) -> List[str]:
    """Ranqueia skills relevantes para a query via keyword matching zero-LLM.

    Usa capability_registry.build_registry() para obter skills disponíveis
    ao principal (available_to_principal=True) e pontua cada uma por
    overlap de tokens entre a query e name+description da skill.

    Args:
        query: Texto do turno atual do usuário.
        limit: Máximo de skill names a retornar (top-N).

    Returns:
        Lista de skill names ordenados por relevância descrescente.
        Retorna [] em caso de erro (best-effort — nunca propaga exceção).

    Notes:
        F4/F5 ADVISORY: não altera o listing real do SDK.
        Zero LLM — apenas substring/token overlap.
    """
    try:
        reg = capability_registry.build_registry()

        # Tokenizar a query (lowercase, split em espaços e pontuação)
        import re
        query_tokens = set(re.findall(r'\w+', query.lower()))

        if not query_tokens:
            return []

        scored: list[tuple[int, str]] = []

        for skill in reg.skills:
            if not skill.available_to_principal:
                continue

            # Combinar name + description para scoring
            candidate_text = f"{skill.name} {skill.description}".lower()
            candidate_tokens = set(re.findall(r'\w+', candidate_text))

            # Score = número de tokens da query que aparecem no texto da skill
            score = len(query_tokens & candidate_tokens)

            # Fallback: substring direto para tokens compostos (ex: "separação")
            if score == 0:
                for token in query_tokens:
                    if len(token) >= 4 and token in candidate_text:
                        score += 1

            if score > 0:
                scored.append((score, skill.name))

        # Ordenar por score descendente, depois por nome (estabilidade)
        scored.sort(key=lambda x: (-x[0], x[1]))

        return [name for _, name in scored[:limit]]

    except Exception as e:
        logger.debug(
            "[CONTEXT_ENRICHMENT] rank_skills_for_query falhou (best-effort): %s", e
        )
        return []


# ---------------------------------------------------------------------------
# F4/F5 — build_skill_hints_block
# ---------------------------------------------------------------------------

def build_skill_hints_block(query: str, limit: int = 8) -> Optional[str]:
    """Constrói bloco XML <skill_hints> com as skills mais relevantes para a query.

    Retorna None quando não há skills relevantes (não injeta bloco vazio).

    Args:
        query: Texto do turno atual.
        limit: Máximo de skills a incluir no bloco.

    Returns:
        String XML ou None. Nunca propaga exceção.

    Example output:
        <skill_hints priority="advisory">
        Skills mais relevantes para esta query: gerindo-expedicao, cotando-frete
        </skill_hints>
    """
    try:
        skills = rank_skills_for_query(query, limit=limit)
        if not skills:
            return None

        skills_csv = ", ".join(skills)
        return (
            f'<skill_hints priority="advisory">\n'
            f'Skills mais relevantes para esta query: {skills_csv}\n'
            f'</skill_hints>'
        )

    except Exception as e:
        logger.debug(
            "[CONTEXT_ENRICHMENT] build_skill_hints_block falhou (best-effort): %s", e
        )
        return None


# ---------------------------------------------------------------------------
# D5 — build_world_model_block
# ---------------------------------------------------------------------------

# Mapeamento domínio → entity_types para busca focada na ontologia.
# Alinhado com _DOMAIN_SKILLS/_DOMAIN_KEYWORDS em memory_injection.py.
_DOMAIN_ENTITY_TYPES = {
    'expedicao': ['cliente', 'produto', 'transportadora'],
    'odoo_compras': ['cliente', 'fornecedor', 'produto'],
    'odoo_financeiro': ['cliente', 'fornecedor'],
    'frete': ['transportadora', 'cliente'],
    'ssw': ['transportadora'],
    'admin': ['usuario'],
}

# Número de entidades por tipo (para limitar tamanho do bloco)
_ENTITIES_PER_TYPE = 5


def build_world_model_block(user_id: int, query: str) -> Optional[str]:
    """Constrói bloco XML <world_model> com entidades canônicas relevantes.

    Busca entidades na ontologia (D4 query_ontology_entities) e as formata
    como contexto advisory. Se a ontologia estiver vazia, retorna None —
    o fallback _DOMAIN_KEYWORDS em memory_injection.py continua ativo.

    D5 é ADITIVO: não remove nem substitui routing_context existente.

    Args:
        user_id: ID do usuário para contextualizar a busca.
        query: Texto do turno (usado para determinar domínio relevante).

    Returns:
        String XML ou None. Nunca propaga exceção.

    Notes:
        - Se ontologia vazia → None (fallback _DOMAIN_KEYWORDS ativo).
        - Tolerante: exceções de DB/import retornam None.
    """
    try:
        # Determinar domínio para focar a busca de entidades
        entity_types_to_fetch = _resolve_entity_types_for_query(query)

        all_entities: list[dict] = []

        if entity_types_to_fetch:
            # Busca focada por tipo de entidade
            for etype in entity_types_to_fetch:
                entities = query_ontology_entities(
                    user_id=user_id,
                    entity_type=etype,
                    limit=_ENTITIES_PER_TYPE,
                )
                all_entities.extend(entities)
        else:
            # Sem domínio determinado: buscar top entidades gerais
            for etype in ['cliente', 'produto', 'transportadora']:
                entities = query_ontology_entities(
                    user_id=user_id,
                    entity_type=etype,
                    limit=_ENTITIES_PER_TYPE,
                )
                all_entities.extend(entities)

        if not all_entities:
            return None

        # Deduplica por (entity_type, entity_name) mantendo ordem
        seen: set[tuple[str, str]] = set()
        unique_entities: list[dict] = []
        for ent in all_entities:
            key = (ent.get('entity_type', ''), ent.get('entity_name', ''))
            if key not in seen:
                seen.add(key)
                unique_entities.append(ent)

        if not unique_entities:
            return None

        # Formatar bloco XML
        lines = ['<world_model priority="advisory">']
        lines.append('Entidades canônicas relevantes:')
        for ent in unique_entities:
            etype = ent.get('entity_type', 'entidade')
            ename = ent.get('entity_name', '')
            ekey = ent.get('entity_key')
            if ekey:
                lines.append(f'  [{etype}] {ename} ({ekey})')
            else:
                lines.append(f'  [{etype}] {ename}')
        lines.append('</world_model>')

        return '\n'.join(lines)

    except Exception as e:
        logger.debug(
            "[CONTEXT_ENRICHMENT] build_world_model_block falhou (best-effort): %s", e
        )
        return None


def _resolve_entity_types_for_query(query: str) -> list[str]:
    """Determina entity_types relevantes para a query via keyword matching.

    Reutiliza _DOMAIN_KEYWORDS de memory_injection.py para consistência.
    Retorna lista de entity_types ou [] se domínio não determinado.
    """
    try:
        from app.agente.sdk.memory_injection import _DOMAIN_KEYWORDS
        query_lower = query.lower()

        domain_scores: dict[str, int] = {}
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw.lower() in query_lower)
            if hits > 0:
                domain_scores[domain] = hits

        if not domain_scores:
            return []

        best_domain = max(domain_scores, key=domain_scores.get)
        return _DOMAIN_ENTITY_TYPES.get(best_domain, [])

    except Exception as e:
        logger.debug("[CONTEXT_ENRICHMENT] _resolve_entity_types_for_query falhou: %s", e)
        return []
