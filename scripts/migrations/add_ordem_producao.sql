-- Script SQL: Adicionar campo ordem_producao na tabela programacao_producao
-- Para rodar no Shell do Render
-- Data: 2025-12-09

-- Verificar se coluna já existe antes de adicionar
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'programacao_producao'
        AND column_name = 'ordem_producao'
    ) THEN
        ALTER TABLE programacao_producao
        ADD COLUMN ordem_producao VARCHAR(50) NULL;

        RAISE NOTICE 'Coluna ordem_producao adicionada com sucesso!';
    ELSE
        RAISE NOTICE 'Coluna ordem_producao já existe.';
    END IF;
END $$;

-- OU, se preferir SQL simples (vai dar erro se já existir):
-- ALTER TABLE programacao_producao ADD COLUMN ordem_producao VARCHAR(50) NULL;
