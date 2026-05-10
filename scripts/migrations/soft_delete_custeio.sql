-- Migration: Soft delete em CustoFrete e ParametroCusteio
-- Sprint 3 - C17 (auditoria 2026-05-10)
-- Adiciona colunas ativo/desativado_em/desativado_por para preservar audit trail

-- CustoFrete
ALTER TABLE custo_frete ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE custo_frete ADD COLUMN IF NOT EXISTS desativado_em TIMESTAMP NULL;
ALTER TABLE custo_frete ADD COLUMN IF NOT EXISTS desativado_por VARCHAR(100) NULL;
CREATE INDEX IF NOT EXISTS ix_custo_frete_ativo ON custo_frete(ativo);

-- ParametroCusteio
ALTER TABLE parametro_custeio ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE parametro_custeio ADD COLUMN IF NOT EXISTS desativado_em TIMESTAMP NULL;
ALTER TABLE parametro_custeio ADD COLUMN IF NOT EXISTS desativado_por VARCHAR(100) NULL;
CREATE INDEX IF NOT EXISTS ix_parametro_custeio_ativo ON parametro_custeio(ativo);
