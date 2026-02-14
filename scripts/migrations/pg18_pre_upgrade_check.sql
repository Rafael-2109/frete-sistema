-- ============================================================
-- PRE-UPGRADE CHECK: PostgreSQL 16 → 18
-- ============================================================
-- Executar no Render Shell ANTES do upgrade.
-- Todas as queries sao read-only (seguro).
-- ============================================================

-- 1. Versao atual
SELECT version();

-- 2. Tamanho do banco
SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;

-- 3. Data checksums (deve ser ON para compatibilidade com PG 18)
SHOW data_checksums;

-- 4. Metodo de autenticacao (md5 gera warnings no PG 18)
SHOW password_encryption;

-- 5. Extensions instaladas
SELECT name, installed_version, default_version
FROM pg_available_extensions
WHERE installed_version IS NOT NULL
ORDER BY name;

-- 6. Collation do banco
SELECT datcollate, datctype, pg_encoding_to_char(encoding) AS encoding
FROM pg_database
WHERE datname = current_database();

-- 7. Triggers (AFTER triggers mudam comportamento de role no PG 18)
SELECT tgname AS trigger_name,
       c.relname AS table_name,
       p.proname AS function_name,
       CASE tgtype & 66
         WHEN 2 THEN 'BEFORE'
         WHEN 64 THEN 'INSTEAD OF'
         ELSE 'AFTER'
       END AS timing
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE NOT t.tgisinternal
ORDER BY timing DESC, c.relname;

-- 8. Contagem de indexes por tipo
SELECT
  count(*) AS total_indexes,
  count(*) FILTER (WHERE indexdef LIKE '%WHERE%') AS partial_indexes,
  count(*) FILTER (WHERE indexdef LIKE '%USING gin%') AS gin_indexes,
  count(*) FILTER (WHERE indexdef LIKE '%USING gist%') AS gist_indexes
FROM pg_indexes
WHERE schemaname = 'public';

-- 9. Verificar se funcoes de AFTER triggers usam SET ROLE
SELECT p.proname,
       CASE WHEN lower(p.prosrc) LIKE '%set role%'
                 OR lower(p.prosrc) LIKE '%set session authorization%'
            THEN 'ALERTA: USA SET ROLE'
            ELSE 'OK: sem SET ROLE'
       END AS role_check
FROM pg_trigger t
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE NOT t.tgisinternal
  AND (t.tgtype & 66) NOT IN (2, 64);  -- apenas AFTER triggers

-- 10. Verificar tabelas particionadas (nao devem existir)
SELECT c.relname, c.relkind
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public'
  AND c.relkind = 'p';  -- 'p' = partitioned table
