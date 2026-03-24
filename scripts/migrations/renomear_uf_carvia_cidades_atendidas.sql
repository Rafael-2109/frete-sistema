-- Migration: Renomear uf → uf_destino + adicionar uf_origem em carvia_cidades_atendidas
-- Tabela vazia em producao — DDL segura
-- Executar via Render Shell

-- 1. Renomear coluna uf → uf_destino
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cidades_atendidas' AND column_name = 'uf'
    ) THEN
        ALTER TABLE carvia_cidades_atendidas RENAME COLUMN uf TO uf_destino;
        RAISE NOTICE 'Coluna uf renomeada para uf_destino';
    ELSE
        RAISE NOTICE 'Coluna uf ja nao existe (ja renomeada)';
    END IF;
END $$;

-- 2. Adicionar coluna uf_origem
ALTER TABLE carvia_cidades_atendidas
    ADD COLUMN IF NOT EXISTS uf_origem VARCHAR(2);

-- 3. Dropar unique antigo e indice antigo
ALTER TABLE carvia_cidades_atendidas
    DROP CONSTRAINT IF EXISTS uq_carvia_cidade_tabela;

DROP INDEX IF EXISTS ix_carvia_cidade_uf;

-- 4. Criar unique novo e indices novos
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_carvia_cidade_tabela_origem'
    ) THEN
        ALTER TABLE carvia_cidades_atendidas
            ADD CONSTRAINT uq_carvia_cidade_tabela_origem
            UNIQUE (codigo_ibge, nome_tabela, uf_origem);
        RAISE NOTICE 'Unique constraint uq_carvia_cidade_tabela_origem criada';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_carvia_cidade_uf_destino
    ON carvia_cidades_atendidas (uf_destino);

CREATE INDEX IF NOT EXISTS ix_carvia_cidade_uf_origem
    ON carvia_cidades_atendidas (uf_origem);

-- 5. Tornar uf_origem NOT NULL (tabela vazia, seguro)
ALTER TABLE carvia_cidades_atendidas
    ALTER COLUMN uf_origem SET NOT NULL;
