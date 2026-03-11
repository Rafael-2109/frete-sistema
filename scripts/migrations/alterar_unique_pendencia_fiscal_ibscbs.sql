-- Migration: Alterar unique constraint de pendencia_fiscal_ibscbs
-- =================================================================
--
-- Problema: chave_acesso tinha UNIQUE simples, mas NF-es podem gerar
-- multiplas pendencias (uma por NCM prefixo) com a mesma chave_acesso.
-- Isso causava UniqueViolation (PYTHON-FLASK-19).
--
-- Solucao: Trocar unique simples por composite unique (chave_acesso, ncm_prefixo).
-- Para CTes (ncm_prefixo IS NULL), PostgreSQL trata (key, NULL) como distinto,
-- entao o check previo por chave_acesso no codigo Python continua garantindo unicidade.
--
-- Data: 2026-03-11
-- Idempotente: SIM

-- 1. Remover unique constraint antiga (se existir)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pendencia_fiscal_ibscbs_chave_acesso_key'
    ) THEN
        ALTER TABLE pendencia_fiscal_ibscbs
            DROP CONSTRAINT pendencia_fiscal_ibscbs_chave_acesso_key;
        RAISE NOTICE 'Constraint pendencia_fiscal_ibscbs_chave_acesso_key removida';
    ELSE
        RAISE NOTICE 'Constraint pendencia_fiscal_ibscbs_chave_acesso_key nao existe — OK';
    END IF;
END
$$;

-- 2. Criar nova unique constraint composta (se nao existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_pendencia_fiscal_chave_ncm'
    ) THEN
        ALTER TABLE pendencia_fiscal_ibscbs
            ADD CONSTRAINT uq_pendencia_fiscal_chave_ncm
            UNIQUE (chave_acesso, ncm_prefixo);
        RAISE NOTICE 'Constraint uq_pendencia_fiscal_chave_ncm criada';
    ELSE
        RAISE NOTICE 'Constraint uq_pendencia_fiscal_chave_ncm ja existe — OK';
    END IF;
END
$$;

-- 3. Garantir que indice simples em chave_acesso continua existindo (para queries)
CREATE INDEX IF NOT EXISTS ix_pendencia_fiscal_ibscbs_chave_acesso
    ON pendencia_fiscal_ibscbs (chave_acesso);
