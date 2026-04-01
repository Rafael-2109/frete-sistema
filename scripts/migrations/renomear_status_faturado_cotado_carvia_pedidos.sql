-- Migration: Renomear status FATURADO -> COTADO em carvia_pedidos
-- Fluxo final: ABERTO -> COTADO -> EMBARCADO (sem FATURADO)
-- COTADO = pedido em embarque (ha cotacao de compra associada)
--
-- Executar no Render Shell ou psql

-- 1. Converter registros existentes (status_calculado recalcula dinamicamente)
UPDATE carvia_pedidos SET status = 'ABERTO' WHERE status = 'FATURADO';

-- 2. Recriar CHECK constraint
ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status;
ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status
    CHECK (status IN ('ABERTO','COTADO','EMBARCADO','CANCELADO'));
