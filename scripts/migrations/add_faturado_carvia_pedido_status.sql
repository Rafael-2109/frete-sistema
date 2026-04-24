-- Migration: Adicionar 'FATURADO' ao CHECK constraint de carvia_pedidos.status
-- Data: 2026-04-24 (P7 — transicao EMBARCADO -> FATURADO para paridade com Nacom)
-- Idempotente: DROP + ADD constraint.
-- Risco: baixo — aditivo, nao remove valores existentes.

ALTER TABLE carvia_pedidos
    DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status;

ALTER TABLE carvia_pedidos
    ADD CONSTRAINT ck_carvia_pedido_status
    CHECK (status IN ('ABERTO','COTADO','EMBARCADO','FATURADO','CANCELADO'));
