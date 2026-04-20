-- Migration: indice GIN trigram para busca por substring rapida em
-- pessoal_transacoes.historico_completo. Acelera ILIKE '%texto%' na
-- listagem de transacoes (F1 do modulo pessoal).
-- Idempotente.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_hist_completo_trgm
    ON pessoal_transacoes
    USING gin (historico_completo gin_trgm_ops);
