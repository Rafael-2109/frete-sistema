-- Migration: Adicionar campo ordem_producao na tabela movimentacao_estoque
-- Data: 2026-02-02
-- Descrição: Campo para identificar a Ordem de Produção (OP) associada à movimentação.
--            Propagado da produção RAIZ para todos os componentes consumidos.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'movimentacao_estoque' AND column_name = 'ordem_producao'
    ) THEN
        ALTER TABLE movimentacao_estoque ADD COLUMN ordem_producao VARCHAR(50) NULL;
        RAISE NOTICE '✅ Coluna ordem_producao adicionada em movimentacao_estoque';
    ELSE
        RAISE NOTICE '✅ Coluna ordem_producao já existe em movimentacao_estoque';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_movimentacao_ordem_producao ON movimentacao_estoque(ordem_producao);
