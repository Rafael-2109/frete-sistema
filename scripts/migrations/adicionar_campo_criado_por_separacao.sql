-- =========================================================
-- Migration: Adicionar campo criado_por na tabela Separacao
-- =========================================================
--
-- OBJETIVO: Registrar o usuário que criou cada separação
-- AUTOR: Claude AI
-- DATA: 22/11/2025
--
-- EXECUTAR NO SHELL DO RENDER:
-- psql $DATABASE_URL -f adicionar_campo_criado_por_separacao.sql
-- =========================================================

-- Verificar se campo já existe e adicionar se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'separacao'
        AND column_name = 'criado_por'
    ) THEN
        ALTER TABLE separacao ADD COLUMN criado_por VARCHAR(100) NULL;
        RAISE NOTICE 'Campo criado_por adicionado com sucesso!';
    ELSE
        RAISE NOTICE 'Campo criado_por já existe. Nada a fazer.';
    END IF;
END $$;

-- Verificar resultado
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'separacao'
AND column_name = 'criado_por';
