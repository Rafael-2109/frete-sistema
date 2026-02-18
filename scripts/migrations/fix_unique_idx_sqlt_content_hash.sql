-- Migration: Trocar indice idx_sqlt_content_hash por unique parcial idx_sqlt_content_hash_unique
-- Habilita ON CONFLICT (content_hash) WHERE content_hash IS NOT NULL para upsert
-- em sql_template_embeddings — mesmo padrao de devolucao_reason_embeddings.
--
-- Executar via Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/fix_unique_idx_sqlt_content_hash.sql

DROP INDEX IF EXISTS idx_sqlt_content_hash;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sqlt_content_hash_unique
ON sql_template_embeddings (content_hash)
WHERE content_hash IS NOT NULL;
