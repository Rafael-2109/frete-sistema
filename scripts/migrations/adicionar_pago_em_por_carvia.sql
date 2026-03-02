-- Migration: Adicionar pago_em/pago_por em carvia_faturas_cliente e carvia_despesas
-- carvia_faturas_transportadora JA tem esses campos
-- Executar via Render Shell (idempotente)

-- carvia_faturas_cliente
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pago_em TIMESTAMP;
ALTER TABLE carvia_faturas_cliente ADD COLUMN IF NOT EXISTS pago_por VARCHAR(100);

-- carvia_despesas
ALTER TABLE carvia_despesas ADD COLUMN IF NOT EXISTS pago_em TIMESTAMP;
ALTER TABLE carvia_despesas ADD COLUMN IF NOT EXISTS pago_por VARCHAR(100);
