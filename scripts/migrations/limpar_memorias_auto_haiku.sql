-- Limpeza de memorias residuais do auto_haiku (subagente Haiku removido em 2026-03-12)
-- 16 memorias em 6 usuarios, 100% auto_haiku, 0 conteudo misto MCP
-- Auditoria via MCP Render em 2026-03-12

-- Verificacao pre-delete
SELECT id, user_id, path, LENGTH(content) AS bytes,
       (LENGTH(content) - LENGTH(REPLACE(content, 'auto_haiku', ''))) / 10 AS auto_haiku_count
FROM agent_memories
WHERE id IN (9, 10, 14, 16, 17, 20, 22, 24, 25, 28, 31, 34, 35, 39, 40, 249)
  AND content LIKE '%auto_haiku%'
ORDER BY user_id, path;

-- Delete
DELETE FROM agent_memories
WHERE id IN (9, 10, 14, 16, 17, 20, 22, 24, 25, 28, 31, 34, 35, 39, 40, 249)
  AND content LIKE '%auto_haiku%';
