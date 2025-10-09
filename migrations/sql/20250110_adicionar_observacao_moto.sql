-- Migração: Adicionar campo observacao na tabela moto
-- Data: 2025-01-10
-- Descrição: Campo para registrar observações de avarias, substituições, etc

-- Adicionar coluna observacao
ALTER TABLE moto ADD COLUMN IF NOT EXISTS observacao TEXT;

-- Comentário na coluna
COMMENT ON COLUMN moto.observacao IS 'Observações sobre avarias, substituições e outras ocorrências';
