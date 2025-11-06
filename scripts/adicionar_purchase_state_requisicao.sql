-- Script SQL para adicionar campo purchase_state à tabela requisicao_compras
-- Data: 05/11/2025
-- Objetivo: Armazenar status da linha de requisição no Odoo

-- Adicionar coluna purchase_state
ALTER TABLE requisicao_compras
ADD COLUMN IF NOT EXISTS purchase_state VARCHAR(20);

-- Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_requisicao_purchase_state
ON requisicao_compras(purchase_state);

-- Verificar resultado
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'requisicao_compras'
AND column_name = 'purchase_state';
