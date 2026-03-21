-- Migration: Adicionar campos de auditoria de impressao em embarques
-- Data: 2026-03-21
-- Descricao: Rastreamento de impressao e flag de reimpressao necessaria.
--   impresso_em: timestamp da ultima impressao.
--   impresso_por: usuario que imprimiu.
--   alterado_apos_impressao: sinaliza que embarque mudou apos impressao.
-- Uso: Executar no Render Shell (SQL idempotente)

-- Campo impresso_em (timestamp nullable)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embarques' AND column_name = 'impresso_em'
    ) THEN
        ALTER TABLE embarques
            ADD COLUMN impresso_em TIMESTAMP NULL;
    END IF;
END $$;

-- Campo impresso_por (varchar nullable)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embarques' AND column_name = 'impresso_por'
    ) THEN
        ALTER TABLE embarques
            ADD COLUMN impresso_por VARCHAR(100) NULL;
    END IF;
END $$;

-- Campo alterado_apos_impressao (boolean, default false)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embarques' AND column_name = 'alterado_apos_impressao'
    ) THEN
        ALTER TABLE embarques
            ADD COLUMN alterado_apos_impressao BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- Indice parcial para busca rapida de embarques que precisam reimprimir
CREATE INDEX IF NOT EXISTS ix_embarques_precisa_reimprimir
    ON embarques (id)
    WHERE alterado_apos_impressao = TRUE AND impresso_em IS NOT NULL;
