-- =============================================================================
-- Dedup Memórias Empresa v2 — Limpeza definitiva de duplicatas
--
-- Grupos:
--   1. Atacadão NF: ID 165 (deletar) — duplicata do ID 139
--   2. Dry-run Odoo: ID 112 (deletar) — duplicata do ID 166
--   3. Assaí confirmação: IDs 110, 141 (deletar) — triplicata do ID 163
--   4. Rafael: ID 179 (merge → 125, depois deletar)
--
-- Pré-requisitos: trigger trg_delete_memory_embedding (BEFORE DELETE) já
--   limpa embeddings automaticamente. FK CASCADE em entity_links.
--
-- Uso (Render Shell):
--   psql $DATABASE_URL < dedup_memorias_empresa_v2.sql
-- =============================================================================

BEGIN;

-- ===================== BEFORE (auditoria) =====================
SELECT '=== BEFORE ===' AS step;

SELECT id, path, is_cold,
       LENGTH(content) AS len,
       usage_count, effective_count
FROM agent_memories
WHERE id IN (110, 112, 125, 139, 141, 163, 165, 166, 179)
ORDER BY id;

SELECT COUNT(*) AS embeddings_a_remover
FROM agent_memory_embeddings
WHERE memory_id IN (110, 112, 141, 165, 179);

SELECT COUNT(*) AS kg_links_a_remover
FROM agent_memory_entity_links
WHERE memory_id IN (110, 112, 141, 165, 179);

-- ===================== MERGE: Rafael (179 → 125) =====================
-- Antes:
--   125: <usuario nome="Rafael"><cargo>Administrador / TI</cargo></usuario>
--   179: <usuario nome="Rafael de Carvalho Nascimento"><cargo>usuario principal do sistema (ID: 1)</cargo></usuario>
-- Depois (125):
--   Nome completo + cargo + ID do sistema

UPDATE agent_memories
SET content = '<usuario nome="Rafael de Carvalho Nascimento">' || E'\n'
           || '  <cargo>Administrador / TI — usuario principal do sistema (ID: 1)</cargo>' || E'\n'
           || '</usuario>',
    updated_at = NOW()
WHERE id = 125
  AND content LIKE '%<usuario nome="Rafael"%';

-- ===================== DELETE: 5 duplicatas =====================
-- O trigger trg_delete_memory_embedding cuida dos embeddings.
-- FK CASCADE cuida dos entity_links.

DELETE FROM agent_memories
WHERE id IN (
    165,  -- Atacadão NF duplicata (manter 139)
    112,  -- Dry-run Odoo duplicata (manter 166)
    110,  -- Assaí triplicata (manter 163)
    141,  -- Assaí triplicata (manter 163)
    179   -- Rafael merge → 125
);

-- ===================== AFTER (verificação) =====================
SELECT '=== AFTER ===' AS step;

-- Sobreviventes devem ser: 125 (merged), 139, 163, 166
SELECT id, path, LEFT(content, 80) AS preview
FROM agent_memories
WHERE id IN (125, 139, 163, 166)
ORDER BY id;

-- Confirmar que deletados sumiram
SELECT COUNT(*) AS deletados_restantes
FROM agent_memories
WHERE id IN (110, 112, 141, 165, 179);
-- Esperado: 0

-- Confirmar embeddings limpos
SELECT COUNT(*) AS embeddings_orfaos
FROM agent_memory_embeddings
WHERE memory_id IN (110, 112, 141, 165, 179);
-- Esperado: 0

-- Confirmar KG links limpos
SELECT COUNT(*) AS kg_links_orfaos
FROM agent_memory_entity_links
WHERE memory_id IN (110, 112, 141, 165, 179);
-- Esperado: 0

COMMIT;
