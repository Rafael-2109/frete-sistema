-- Migration HORA 02: hora_pedido_item.numero_chassi nullable + UNIQUE parcial
-- Data: 2026-04-18
-- Motivacao:
--   Formato de pedido pre-NF (ex.: cliente solicita motos sem chassi ainda)
--   deve ser aceito no sistema. Motochefe atribui chassis depois.
--   Unica excecao ao invariante 2 (chassi como FK em todas transacionais).
--   Demais tabelas (nf_entrada_item, recebimento_conferencia, venda_item,
--   moto_evento) continuam com chassi NOT NULL.
-- Idempotente: usa IF EXISTS.
-- RISCO: baixo. ALTER COLUMN DROP NOT NULL + recriar constraint UNIQUE parcial.

-- Passo 1: tornar numero_chassi nullable
ALTER TABLE hora_pedido_item
    ALTER COLUMN numero_chassi DROP NOT NULL;

-- Passo 2: dropar constraint UNIQUE antiga e recriar como parcial
-- (UNIQUE(pedido_id, chassi) so faz sentido quando chassi nao e NULL)
ALTER TABLE hora_pedido_item
    DROP CONSTRAINT IF EXISTS uq_hora_pedido_item_chassi;

-- Como o Postgres nao suporta UNIQUE parcial inline, usamos index
CREATE UNIQUE INDEX IF NOT EXISTS uq_hora_pedido_item_chassi_parcial
    ON hora_pedido_item (pedido_id, numero_chassi)
    WHERE numero_chassi IS NOT NULL;
