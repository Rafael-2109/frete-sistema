-- Migration: Limpeza de memorias baseada na auditoria de 2026-03-23
-- Contexto: Auditoria revelou 46 diretorios fantasma (29%) e termos ineficazes
--
-- Parte 1: Remover diretorios fantasma (content NULL, is_directory=True)
-- Parte 2: Mover termos ineficazes para cold tier

-- ============================================================
-- PARTE 1: Diretorios fantasma
-- Registros com is_directory=True e content NULL que nao servem
-- para nada (zero usage, zero embedding, zero KG links)
-- ============================================================

-- Verificar antes
SELECT 'ANTES_LIMPEZA' as fase,
  COUNT(*) as total_memorias,
  COUNT(*) FILTER (WHERE is_directory = true AND (content IS NULL OR content = '')) as diretorios_fantasma
FROM agent_memories;

-- Limpar embeddings orfaos primeiro (FK cascade pode nao cobrir)
DELETE FROM agent_memory_embeddings
WHERE memory_id IN (
  SELECT id FROM agent_memories
  WHERE is_directory = true AND (content IS NULL OR content = '')
);

-- Limpar entity links orfaos
DELETE FROM agent_memory_entity_links
WHERE memory_id IN (
  SELECT id FROM agent_memories
  WHERE is_directory = true AND (content IS NULL OR content = '')
);

-- Limpar versoes orfas
DELETE FROM agent_memory_versions
WHERE memory_id IN (
  SELECT id FROM agent_memories
  WHERE is_directory = true AND (content IS NULL OR content = '')
);

-- Remover diretorios fantasma
DELETE FROM agent_memories
WHERE is_directory = true AND (content IS NULL OR content = '');

-- ============================================================
-- PARTE 2: Termos ineficazes -> cold tier
-- Termos com muitas injecoes (>=20) mas zero efetividade
-- continuam gastando tokens de injecao sem agregar valor
-- ============================================================

-- Verificar antes
SELECT 'TERMOS_ANTES' as fase,
  COUNT(*) as total_termos,
  COUNT(*) FILTER (WHERE is_cold = true) as ja_cold,
  COUNT(*) FILTER (WHERE effective_count = 0 AND usage_count >= 20) as candidatos_cold
FROM agent_memories
WHERE path LIKE '/memories/empresa/termos/%'
  AND is_directory = false;

-- Mover para cold
UPDATE agent_memories
SET is_cold = true
WHERE path LIKE '/memories/empresa/termos/%'
  AND is_directory = false
  AND effective_count = 0
  AND usage_count >= 20
  AND is_cold = false;

-- Verificar depois
SELECT 'APOS_LIMPEZA' as fase,
  COUNT(*) as total_memorias,
  COUNT(*) FILTER (WHERE is_directory = true AND (content IS NULL OR content = '')) as diretorios_fantasma,
  COUNT(*) FILTER (WHERE is_cold = true) as total_cold
FROM agent_memories;
