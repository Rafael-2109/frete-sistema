-- Fix: Remove 7 memorias empresa duplicadas causadas por bug no dedup.
--
-- Causa raiz: _check_memory_duplicate() comparava XML raw contra embeddings
-- contextuais, resultando em similarity ~0.69 < threshold 0.90.
--
-- Cascades:
--   agent_memory_entity_links: ON DELETE CASCADE (auto)
--   agent_memory_entity_relations: ON DELETE SET NULL (auto)
--   agent_memory_embeddings: FK logica (delete manual)
--
-- Executar no Render Shell em ordem.

-- 1. Verificar que duplicatas existem
SELECT id, path, created_at FROM agent_memories WHERE id IN (155, 156, 157, 158, 160, 161, 162);

-- 2. Deletar embeddings (FK logica, sem cascade no DB)
DELETE FROM agent_memory_embeddings WHERE memory_id IN (155, 156, 157, 158, 160, 161, 162);

-- 3. Deletar memorias (entity_links CASCADE, relations SET NULL)
DELETE FROM agent_memories WHERE id IN (155, 156, 157, 158, 160, 161, 162);

-- 4. Verificar limpeza
SELECT COUNT(*) AS memorias_empresa FROM agent_memories WHERE user_id = 0;
SELECT COUNT(*) AS links_orfaos FROM agent_memory_entity_links WHERE memory_id IN (155, 156, 157, 158, 160, 161, 162);
SELECT COUNT(*) AS relations_null FROM agent_memory_entity_relations WHERE memory_id IS NULL;
