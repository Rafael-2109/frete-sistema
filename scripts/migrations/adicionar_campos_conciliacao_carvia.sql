-- Migration: Adicionar campos total_conciliado e conciliado em 3 tabelas CarVia
-- Uso: Render Shell → psql

-- carvia_faturas_cliente
ALTER TABLE carvia_faturas_cliente
    ADD COLUMN IF NOT EXISTS total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0;
ALTER TABLE carvia_faturas_cliente
    ADD COLUMN IF NOT EXISTS conciliado BOOLEAN NOT NULL DEFAULT FALSE;

-- carvia_faturas_transportadora
ALTER TABLE carvia_faturas_transportadora
    ADD COLUMN IF NOT EXISTS total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0;
ALTER TABLE carvia_faturas_transportadora
    ADD COLUMN IF NOT EXISTS conciliado BOOLEAN NOT NULL DEFAULT FALSE;

-- carvia_despesas
ALTER TABLE carvia_despesas
    ADD COLUMN IF NOT EXISTS total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0;
ALTER TABLE carvia_despesas
    ADD COLUMN IF NOT EXISTS conciliado BOOLEAN NOT NULL DEFAULT FALSE;
