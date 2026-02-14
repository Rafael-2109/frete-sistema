-- ============================================================
-- POST-UPGRADE: PostgreSQL 16 → 18
-- ============================================================
-- Executar no Render Shell APOS o upgrade.
-- ATENCAO: REINDEX causa downtime. Executar em janela de manutencao.
-- ============================================================

-- 1. Confirmar versao nova
SELECT version();

-- 2. REINDEX DATABASE (obrigatorio apos major upgrade)
-- Reconstroi todos os indexes para garantir consistencia
-- com possiveis mudancas de collation e formato interno.
-- Tempo estimado: ~2-5 min para banco de 1.2 GB com 1.187 indexes.
REINDEX DATABASE sistema_fretes;

-- 3. ANALYZE (atualizar estatisticas do planner)
-- Necessario apos upgrade para que o query planner use
-- estatisticas corretas com as novas estruturas internas.
ANALYZE;

-- 4. Verificar extensions (atualizar se necessario)
SELECT name, installed_version, default_version,
       CASE WHEN installed_version != default_version
            THEN 'ATUALIZAR: ALTER EXTENSION ' || name || ' UPDATE;'
            ELSE 'OK'
       END AS acao
FROM pg_available_extensions
WHERE installed_version IS NOT NULL
ORDER BY name;

-- 5. Verificar triggers estao funcionando
-- (executar SELECT, nao modifica nada)
SELECT tgname, c.relname, p.proname,
       CASE tgtype & 66
         WHEN 2 THEN 'BEFORE'
         WHEN 64 THEN 'INSTEAD OF'
         ELSE 'AFTER'
       END AS timing,
       tgenabled AS enabled
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE NOT t.tgisinternal
ORDER BY c.relname;

-- 6. Verificar password encryption
SHOW password_encryption;

-- 7. Verificar data checksums
SHOW data_checksums;

-- 8. Verificar saude geral pos-upgrade
SELECT
  (SELECT count(*) FROM pg_indexes WHERE schemaname = 'public') AS total_indexes,
  (SELECT count(*) FROM pg_stat_user_tables) AS total_tables,
  pg_size_pretty(pg_database_size(current_database())) AS db_size;
