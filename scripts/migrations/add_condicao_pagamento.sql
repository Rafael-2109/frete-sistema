-- Migration: Adicionar campo condicao_pagamento em cotacoes e fretes
-- Data: 2026-03-30
-- Descricao: Campo para armazenar condicao de pagamento ("A Vista" ou "XX dias")

ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(50);
ALTER TABLE fretes ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(50);
