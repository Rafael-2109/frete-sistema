-- Migration: Adicionar status_pagamento em carvia_faturas_transportadora
-- ======================================================================
-- Adiciona campos de controle de pagamento (independente de status_conferencia)
--
-- Execucao:
--   Render Shell → copiar e colar este SQL

ALTER TABLE carvia_faturas_transportadora
    ADD COLUMN IF NOT EXISTS status_pagamento VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';

ALTER TABLE carvia_faturas_transportadora
    ADD COLUMN IF NOT EXISTS pago_por VARCHAR(100);

ALTER TABLE carvia_faturas_transportadora
    ADD COLUMN IF NOT EXISTS pago_em TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_carvia_fat_transp_status_pgto
    ON carvia_faturas_transportadora (status_pagamento);
