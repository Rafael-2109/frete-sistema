-- Migration: Adicionar uf_origem e filial_ssw a carvia_emissao_cte
-- Motivo: Emissao de CTe precisa usar filial SSW conforme UF de origem
--         SP -> CAR, RJ -> GIG
-- Data: 2026-04-02

ALTER TABLE carvia_emissao_cte
    ADD COLUMN IF NOT EXISTS uf_origem VARCHAR(2),
    ADD COLUMN IF NOT EXISTS filial_ssw VARCHAR(10);

COMMENT ON COLUMN carvia_emissao_cte.uf_origem IS 'UF de origem da operacao (SP, RJ)';
COMMENT ON COLUMN carvia_emissao_cte.filial_ssw IS 'Filial SSW derivada da UF (CAR, GIG)';
