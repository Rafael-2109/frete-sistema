-- Script para alterar precisão dos campos de margem percentual
-- Problema: NUMERIC(5,2) suporta apenas ±999.99
-- Solução: NUMERIC(7,2) suporta até ±99999.99%
-- Data: 2026-01-06

-- Executar no Shell do Render:

ALTER TABLE carteira_principal
ALTER COLUMN margem_bruta_percentual TYPE NUMERIC(7, 2);

ALTER TABLE carteira_principal
ALTER COLUMN margem_liquida_percentual TYPE NUMERIC(7, 2);
