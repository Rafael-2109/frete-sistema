-- Migração para adicionar colunas rota e sub_rota
-- Execute este SQL diretamente no banco PostgreSQL

DO $$
BEGIN
    -- Adicionar coluna rota se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'carteira_principal' 
        AND column_name = 'rota'
    ) THEN
        ALTER TABLE carteira_principal ADD COLUMN rota VARCHAR(50);
        RAISE NOTICE 'Coluna rota adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna rota já existe';
    END IF;

    -- Adicionar coluna sub_rota se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'carteira_principal' 
        AND column_name = 'sub_rota'
    ) THEN
        ALTER TABLE carteira_principal ADD COLUMN sub_rota VARCHAR(50);
        RAISE NOTICE 'Coluna sub_rota adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna sub_rota já existe';
    END IF;
END $$;

-- Verificar se as colunas foram criadas
SELECT 
    column_name,
    data_type,
    is_nullable,
    character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'carteira_principal' 
AND column_name IN ('rota', 'sub_rota')
ORDER BY column_name;
