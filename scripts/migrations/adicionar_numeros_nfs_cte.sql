-- ============================================================================
-- Migration: Adicionar campo numeros_nfs na tabela conhecimento_transporte
-- ============================================================================
-- OBJETIVO: Adicionar coluna para armazenar números de NFs contidas no CTe
-- DATA: 13/11/2025
-- EXECUTAR NO: Shell do Render (psql)
-- ============================================================================

-- Adicionar coluna numeros_nfs
ALTER TABLE conhecimento_transporte
ADD COLUMN IF NOT EXISTS numeros_nfs TEXT;

-- Verificar criação
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
AND column_name = 'numeros_nfs';
