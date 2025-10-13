-- Script SQL para adicionar campos de controle em embarque_moto
-- Execute no shell do Render

-- 1. Adicionar valor_frete_saldo
ALTER TABLE embarque_moto
ADD COLUMN IF NOT EXISTS valor_frete_saldo NUMERIC(15, 2) DEFAULT 0;

-- 2. Adicionar historico_status
ALTER TABLE embarque_moto
ADD COLUMN IF NOT EXISTS historico_status TEXT;

-- 3. Calcular saldo para embarques existentes
UPDATE embarque_moto
SET valor_frete_saldo = COALESCE(valor_frete_contratado, 0) - COALESCE(valor_frete_pago, 0)
WHERE valor_frete_saldo IS NULL;

-- 4. Verificar
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'embarque_moto'
AND column_name IN ('valor_frete_saldo', 'historico_status')
ORDER BY column_name;
