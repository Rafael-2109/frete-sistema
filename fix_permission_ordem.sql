-- Adicionar coluna ordem na tabela permission_module
ALTER TABLE permission_module 
ADD COLUMN IF NOT EXISTS ordem INTEGER DEFAULT 0;