-- Migration: Adicionar origem_cnpj e destino_cnpj em carvia_sessao_demandas
-- Executar no Render Shell

ALTER TABLE carvia_sessao_demandas ADD COLUMN IF NOT EXISTS origem_cnpj VARCHAR(20);
ALTER TABLE carvia_sessao_demandas ADD COLUMN IF NOT EXISTS destino_cnpj VARCHAR(20);
