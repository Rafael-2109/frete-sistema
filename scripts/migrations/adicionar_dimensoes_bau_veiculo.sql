-- Migration: Adicionar dimensoes do bau ao modelo Veiculo
-- Para uso no simulador 3D de carga de motos
-- Executar no Render Shell ou psql

ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS comprimento_bau FLOAT;
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS largura_bau FLOAT;
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS altura_bau FLOAT;

COMMENT ON COLUMN veiculos.comprimento_bau IS 'Comprimento interno do bau em centimetros';
COMMENT ON COLUMN veiculos.largura_bau IS 'Largura interna do bau em centimetros';
COMMENT ON COLUMN veiculos.altura_bau IS 'Altura interna do bau em centimetros';
