-- Migration: Remover 'EMBARCADO' do CHECK constraint de carvia_pedidos.status
-- Data: 2026-04-24 (P12 — EMBARCADO vira badge visual, nao status)
-- Rodar na ordem: (1) migrar dados, (2) alterar constraint.
-- Idempotente.

-- 1. Migrar pedidos existentes EMBARCADO -> FATURADO.
--    No fluxo CarVia real, EMBARCADO implica NF ativa (saida portaria
--    so dispara apos NF anexada), entao FATURADO e o status fiscal correto.
UPDATE carvia_pedidos
    SET status = 'FATURADO'
    WHERE status = 'EMBARCADO';

-- 2. Substituir CHECK constraint.
ALTER TABLE carvia_pedidos
    DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status;

ALTER TABLE carvia_pedidos
    ADD CONSTRAINT ck_carvia_pedido_status
    CHECK (status IN ('ABERTO','COTADO','FATURADO','CANCELADO'));
