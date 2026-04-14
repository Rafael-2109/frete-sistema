-- Migration: criar tabela carvia_historico_match_extrato
-- Feature: Historico de Match Extrato <-> Pagador (append-only log)
-- Cada conciliacao fatura_cliente gera um evento novo. Ocorrencias via COUNT GROUP BY.
-- SEM UNIQUE: 1 descricao pode fazer match com N CNPJs (append-only, sem race).
-- Idempotente: pode ser rodada multiplas vezes no Render Shell sem erro.

CREATE TABLE IF NOT EXISTS carvia_historico_match_extrato (
    id SERIAL PRIMARY KEY,
    descricao_linha_raw VARCHAR(500) NOT NULL,
    descricao_tokens VARCHAR(500) NOT NULL,
    cnpj_pagador VARCHAR(20) NOT NULL,
    tipo_documento VARCHAR(30) NOT NULL DEFAULT 'fatura_cliente',
    conciliacao_id INTEGER,
    registrado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FIX M4: remover indice standalone ix_carvia_histmatch_tokens — e redundante
-- porque o composto (descricao_tokens, tipo_documento) ja cobre queries
-- filtrando por descricao_tokens (prefix rule do PostgreSQL).
-- DROP IF EXISTS limpa instancias onde este script ja rodou com a versao antiga.
DROP INDEX IF EXISTS ix_carvia_histmatch_tokens;

-- Indices (IF NOT EXISTS nativo em CREATE INDEX)
CREATE INDEX IF NOT EXISTS ix_carvia_histmatch_cnpj
    ON carvia_historico_match_extrato (cnpj_pagador);

-- Indice composto para consulta principal: WHERE tokens=X AND tipo_documento=Y
-- Cobre tambem queries so por descricao_tokens (prefix rule).
CREATE INDEX IF NOT EXISTS ix_carvia_histmatch_tokens_tipo
    ON carvia_historico_match_extrato (descricao_tokens, tipo_documento);

-- Indice parcial para backfill idempotente (DELETE por conciliacao_id)
CREATE INDEX IF NOT EXISTS ix_carvia_histmatch_conciliacao_id
    ON carvia_historico_match_extrato (conciliacao_id)
    WHERE conciliacao_id IS NOT NULL;

-- Verificacao final
SELECT
    'Tabela criada' as status,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_name = 'carvia_historico_match_extrato') as colunas,
    (SELECT COUNT(*) FROM pg_indexes
     WHERE tablename = 'carvia_historico_match_extrato') as indices;
