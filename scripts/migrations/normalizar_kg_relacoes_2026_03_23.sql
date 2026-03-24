-- Migration: Normalizar KG - relações e entidades (auditoria 2026-03-23)
-- NOTA: O script Python é preferível por ter mapeamento completo.
-- Este SQL cobre os casos mais comuns para uso via Render Shell.

-- ============================================================
-- VERIFICAR ANTES
-- ============================================================
SELECT 'ANTES' as fase,
  COUNT(DISTINCT relation_type) as tipos_unicos,
  COUNT(*) as total_relacoes,
  COUNT(*) FILTER (WHERE relation_type = 'co_occurs') as co_occurs
FROM agent_memory_entity_relations;

SELECT 'ENTIDADES_ANTES' as fase,
  entity_type, COUNT(*) as total
FROM agent_memory_entities
GROUP BY entity_type ORDER BY total DESC;

-- ============================================================
-- PARTE 1: Normalizar tipos de relação mais comuns
-- ============================================================

-- Sinônimos de pertence_a
UPDATE agent_memory_entity_relations SET relation_type = 'pertence_a'
WHERE relation_type IN ('pertence', 'parte_de', 'faz_parte_de', 'pertence_ao', 'pertence_ao_setor')
AND NOT EXISTS (SELECT 1 FROM agent_memory_entity_relations r2
  WHERE r2.source_entity_id = agent_memory_entity_relations.source_entity_id
  AND r2.target_entity_id = agent_memory_entity_relations.target_entity_id
  AND r2.relation_type = 'pertence_a');

-- Sinônimos de responsavel_por
UPDATE agent_memory_entity_relations SET relation_type = 'responsavel_por'
WHERE relation_type IN ('atua_em', 'trabalha_em', 'executa', 'realiza', 'opera', 'opera_em')
AND NOT EXISTS (SELECT 1 FROM agent_memory_entity_relations r2
  WHERE r2.source_entity_id = agent_memory_entity_relations.source_entity_id
  AND r2.target_entity_id = agent_memory_entity_relations.target_entity_id
  AND r2.relation_type = 'responsavel_por');

-- Sinônimos de produz
UPDATE agent_memory_entity_relations SET relation_type = 'produz'
WHERE relation_type IN ('gera', 'origina', 'dispara', 'confirmacao_gera')
AND NOT EXISTS (SELECT 1 FROM agent_memory_entity_relations r2
  WHERE r2.source_entity_id = agent_memory_entity_relations.source_entity_id
  AND r2.target_entity_id = agent_memory_entity_relations.target_entity_id
  AND r2.relation_type = 'produz');

-- Sinônimos de precede
UPDATE agent_memory_entity_relations SET relation_type = 'precede'
WHERE relation_type IN ('antecede', 'transiciona_para', 'transita_para', 'transita', 'sequencia', 'evolui_para')
AND NOT EXISTS (SELECT 1 FROM agent_memory_entity_relations r2
  WHERE r2.source_entity_id = agent_memory_entity_relations.source_entity_id
  AND r2.target_entity_id = agent_memory_entity_relations.target_entity_id
  AND r2.relation_type = 'precede');

-- Sinônimos de complementa
UPDATE agent_memory_entity_relations SET relation_type = 'complementa'
WHERE relation_type IN ('vincula', 'vincula_a', 'relaciona_com', 'integra', 'possui', 'contem', 'define', 'identifica')
AND NOT EXISTS (SELECT 1 FROM agent_memory_entity_relations r2
  WHERE r2.source_entity_id = agent_memory_entity_relations.source_entity_id
  AND r2.target_entity_id = agent_memory_entity_relations.target_entity_id
  AND r2.relation_type = 'complementa');

-- ============================================================
-- PARTE 2: Remover relações singleton não mapeáveis
-- ============================================================
DELETE FROM agent_memory_entity_relations
WHERE relation_type NOT IN (
  'co_occurs', 'pertence_a', 'depende_de', 'substitui', 'conflita_com',
  'precede', 'bloqueia', 'usa', 'produz', 'fornece', 'consome',
  'localizado_em', 'responsavel_por', 'corrige', 'requer', 'complementa', 'atrasa_para'
);

-- ============================================================
-- PARTE 3: Mudar entidades 'regra' para 'conceito'
-- ============================================================
UPDATE agent_memory_entities SET entity_type = 'conceito' WHERE entity_type = 'regra';

-- ============================================================
-- VERIFICAR DEPOIS
-- ============================================================
SELECT 'APOS' as fase,
  COUNT(DISTINCT relation_type) as tipos_unicos,
  COUNT(*) as total_relacoes
FROM agent_memory_entity_relations;

SELECT 'ENTIDADES_APOS' as fase,
  entity_type, COUNT(*) as total
FROM agent_memory_entities
GROUP BY entity_type ORDER BY total DESC;
