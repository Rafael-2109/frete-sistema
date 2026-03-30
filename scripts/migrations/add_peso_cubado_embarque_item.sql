-- Adicionar peso_cubado ao embarque_itens (nullable, CarVia only)
ALTER TABLE embarque_itens ADD COLUMN IF NOT EXISTS peso_cubado FLOAT;
COMMENT ON COLUMN embarque_itens.peso_cubado IS 'Peso cubado (CarVia motos). NULL = usar peso bruto.';
