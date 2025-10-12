-- ========================================
-- Script de Migração: Adicionar campo numero_nf_importada
-- Executar no SHELL DO RENDER via psql
-- ========================================

-- Adicionar campo numero_nf_importada
ALTER TABLE pedido_venda_moto
ADD COLUMN IF NOT EXISTS numero_nf_importada VARCHAR(20) NULL;

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_pedido_venda_moto_nf_importada
ON pedido_venda_moto(numero_nf_importada);

-- Verificar criação
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'pedido_venda_moto'
AND column_name = 'numero_nf_importada';
