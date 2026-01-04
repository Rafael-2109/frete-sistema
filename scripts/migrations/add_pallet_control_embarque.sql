-- Migration: Adicionar campos de controle de pallets no Embarque
-- Execute este script no Shell do Render
--
-- Novos campos:
-- - qtd_pallets_separados: Total pallets expedidos
-- - qtd_pallets_trazidos: Pallets trazidos pela transportadora
--
-- O saldo pendente e calculado dinamicamente pela property:
-- saldo_pallets_pendentes = separados - trazidos - faturados
--
-- Criado em: 2026-01-04

ALTER TABLE embarques
ADD COLUMN IF NOT EXISTS qtd_pallets_separados INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS qtd_pallets_trazidos INTEGER DEFAULT 0;
