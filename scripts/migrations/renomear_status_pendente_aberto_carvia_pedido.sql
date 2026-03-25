-- Migration: Renomear status PENDENTE -> ABERTO em carvia_pedidos
-- Alinha nomenclatura com Separacao Nacom (status ABERTO)

-- 1. Atualizar dados existentes
UPDATE carvia_pedidos SET status = 'ABERTO' WHERE status = 'PENDENTE';

-- 2. Recriar CHECK constraint
ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status;
ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status
    CHECK (status IN ('ABERTO','FATURADO','EMBARCADO','CANCELADO'));

-- 3. Alterar DEFAULT
ALTER TABLE carvia_pedidos ALTER COLUMN status SET DEFAULT 'ABERTO';
