-- Migration: Adiciona campo documento_devolucao ao modelo Moto
-- Data: 11/10/2025
-- Descrição: Adiciona controle de documento de devolução para agrupar motas devolvidas ao fornecedor
-- Executar no Shell do Render

-- Adicionar coluna documento_devolucao
ALTER TABLE moto
ADD COLUMN documento_devolucao VARCHAR(20);

-- Criar índice
CREATE INDEX idx_moto_documento_devolucao
ON moto(documento_devolucao);

-- Verificar resultado
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name='moto'
AND column_name='documento_devolucao';
