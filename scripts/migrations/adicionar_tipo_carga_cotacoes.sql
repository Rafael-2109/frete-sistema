-- Migration: Adicionar tipo_carga em carvia_cotacoes
-- Executar via Render Shell

ALTER TABLE carvia_cotacoes
    ADD COLUMN IF NOT EXISTS tipo_carga VARCHAR(20);
