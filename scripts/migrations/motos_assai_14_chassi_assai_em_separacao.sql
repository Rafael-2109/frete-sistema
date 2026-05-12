-- Motos Assaí — Migration 14: chassi_assai em `separacao` Nacom + ajuste UNIQUE
-- Idempotente.
--
-- Bug pre-existente (descoberto 2026-05-12 em code review): UNIQUE antiga
-- `uq_separacao_assai_lote_produto` em (separacao_lote_id, cod_produto) bloqueava
-- 2 chassis do mesmo modelo na mesma separacao Assai. Mirror falhava silenciosamente
-- ao espelhar sep com qtd > 1 do mesmo modelo.
--
-- DECISAO: 1 linha por chassi (granularidade real). Adicionar coluna `chassi_assai`
-- em `separacao` que identifica unicamente cada linha de lote ASSAI-SEP-*.
-- Para lotes Nacom (LOTE_*, CARVIA-*) o campo fica NULL — preserva comportamento.

-- 1. Adicionar coluna chassi_assai (nullable; usada apenas em lotes Assai)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'separacao' AND column_name = 'chassi_assai'
    ) THEN
        ALTER TABLE separacao ADD COLUMN chassi_assai VARCHAR(50);
    END IF;
END $$;

-- 2. Drop UNIQUE antiga (era (lote, cod_produto) — incorreto para multi-chassi)
DROP INDEX IF EXISTS uq_separacao_assai_lote_produto;

-- 3. Criar UNIQUE nova em (lote, chassi_assai) parcial
-- 1 linha por chassi por lote ASSAI-SEP-*. NULL chassi_assai (lotes Nacom) nao
-- entra no indice (Postgres permite multiplos NULLs em UNIQUE parcial NOT NULL não exigido).
CREATE UNIQUE INDEX IF NOT EXISTS uq_separacao_assai_lote_chassi
    ON separacao (separacao_lote_id, chassi_assai)
    WHERE separacao_lote_id LIKE 'ASSAI-SEP-%' AND chassi_assai IS NOT NULL;

-- 4. Index auxiliar para lookups por chassi_assai (sincronizacao_espelho)
CREATE INDEX IF NOT EXISTS ix_separacao_chassi_assai
    ON separacao (chassi_assai)
    WHERE chassi_assai IS NOT NULL;
