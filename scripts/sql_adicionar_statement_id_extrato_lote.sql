-- =============================================================================
-- Script SQL para adicionar campos de statement_id à tabela extrato_lote
-- Executar no Shell do Render
-- Data: 2025-12-11
-- =============================================================================

-- Adicionar coluna statement_id (referência ao account.bank.statement do Odoo)
ALTER TABLE extrato_lote
ADD COLUMN IF NOT EXISTS statement_id INTEGER UNIQUE;

-- Adicionar coluna statement_name (nome do statement no Odoo)
ALTER TABLE extrato_lote
ADD COLUMN IF NOT EXISTS statement_name VARCHAR(255);

-- Adicionar coluna data_extrato (data do statement)
ALTER TABLE extrato_lote
ADD COLUMN IF NOT EXISTS data_extrato DATE;

-- Criar índice para statement_id
CREATE INDEX IF NOT EXISTS idx_extrato_lote_statement_id
ON extrato_lote (statement_id);

-- Verificar resultado
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'extrato_lote'
ORDER BY ordinal_position;
