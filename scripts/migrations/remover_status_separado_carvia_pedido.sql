-- Migration: Remover status SEPARADO de carvia_pedidos
-- Data: 22/03/2026
-- Motivo: status_calculado property substituiu dropdown manual. SEPARADO nunca é retornado.

-- 1. Atualizar pedidos existentes com SEPARADO → PENDENTE
UPDATE carvia_pedidos SET status = 'PENDENTE' WHERE status = 'SEPARADO';

-- 2. Recriar CheckConstraint sem SEPARADO
ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status;
ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status
    CHECK (status IN ('PENDENTE', 'FATURADO', 'EMBARCADO', 'CANCELADO'));
