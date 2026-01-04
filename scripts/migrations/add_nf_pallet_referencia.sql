-- Migration: Adiciona campos nf_pallet_referencia e nf_pallet_origem em embarque_itens
-- Data: 04/01/2026
-- Descrição: Esses campos rastreiam qual NF de pallet cobre cada NF de venda

-- 1. Adicionar campo nf_pallet_referencia
ALTER TABLE embarque_itens
ADD COLUMN IF NOT EXISTS nf_pallet_referencia VARCHAR(20);

-- 2. Adicionar campo nf_pallet_origem ('EMBARQUE' ou 'ITEM')
ALTER TABLE embarque_itens
ADD COLUMN IF NOT EXISTS nf_pallet_origem VARCHAR(10);
