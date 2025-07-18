-- Script para adicionar colunas rota e sub_rota na tabela carteira_principal
-- Baseado na migração 0ae5f539b83f_adicionar_campos_rota_subrota_carteira.py

-- Verificar se as colunas já existem antes de adicionar
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

-- Opcional: Popular as colunas com dados dos cadastros de rota existentes
-- (Descomente se quiser popular imediatamente)

/*
UPDATE carteira_principal 
SET rota = (
    SELECT cr.rota 
    FROM cadastro_rota cr 
    WHERE cr.cod_uf = carteira_principal.cod_uf 
    AND cr.ativa = true 
    LIMIT 1
)
WHERE carteira_principal.rota IS NULL 
AND carteira_principal.cod_uf IS NOT NULL;

UPDATE carteira_principal 
SET sub_rota = (
    SELECT csr.sub_rota 
    FROM cadastro_sub_rota csr 
    WHERE csr.cod_uf = carteira_principal.cod_uf 
    AND csr.nome_cidade = carteira_principal.nome_cidade
    AND csr.ativa = true 
    LIMIT 1
)
WHERE carteira_principal.sub_rota IS NULL 
AND carteira_principal.cod_uf IS NOT NULL 
AND carteira_principal.nome_cidade IS NOT NULL;
*/

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