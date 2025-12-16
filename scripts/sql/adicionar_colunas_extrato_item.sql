-- Script SQL para adicionar colunas à tabela extrato_item
-- Execute no Shell do Render
-- Data: 2025-12-15

-- Adicionar coluna titulo_receber_id (FK para contas_a_receber)
ALTER TABLE extrato_item
ADD COLUMN IF NOT EXISTS titulo_receber_id INTEGER REFERENCES contas_a_receber(id);

-- Criar índice para titulo_receber_id
CREATE INDEX IF NOT EXISTS idx_extrato_item_titulo_receber
ON extrato_item(titulo_receber_id);

-- Adicionar coluna titulo_pagar_id (FK para contas_a_pagar)
ALTER TABLE extrato_item
ADD COLUMN IF NOT EXISTS titulo_pagar_id INTEGER REFERENCES contas_a_pagar(id);

-- Criar índice para titulo_pagar_id
CREATE INDEX IF NOT EXISTS idx_extrato_item_titulo_pagar
ON extrato_item(titulo_pagar_id);

-- Adicionar coluna titulo_cnpj (para busca por agrupamento)
ALTER TABLE extrato_item
ADD COLUMN IF NOT EXISTS titulo_cnpj VARCHAR(20);

-- Criar índice para titulo_cnpj
CREATE INDEX IF NOT EXISTS idx_extrato_item_titulo_cnpj
ON extrato_item(titulo_cnpj);

-- Verificar resultado
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'extrato_item'
AND column_name IN ('titulo_receber_id', 'titulo_pagar_id', 'titulo_cnpj')
ORDER BY column_name;
