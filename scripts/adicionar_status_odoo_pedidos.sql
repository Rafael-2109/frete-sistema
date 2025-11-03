-- Script SQL para adicionar campo status_odoo em pedido_compras
-- ================================================================
--
-- Para executar no Shell do Render:
-- 1. Acesse o Shell SQL do banco
-- 2. Cole e execute este script
--
-- Autor: Sistema de Fretes
-- Data: 2025-11-03
-- ================================================================

-- Adicionar campo status_odoo
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS status_odoo VARCHAR(20);

-- Criar índice para otimizar consultas
CREATE INDEX IF NOT EXISTS idx_pedido_status_odoo
ON pedido_compras(status_odoo);

-- Verificar se foi criado
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND column_name = 'status_odoo';

-- Mostrar resumo
SELECT
    COUNT(*) as total_pedidos,
    status_odoo,
    COUNT(*) FILTER (WHERE status_odoo IS NULL) as sem_status
FROM pedido_compras
GROUP BY status_odoo;
