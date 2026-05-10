-- Migration: CHECK constraints no modulo de Custeio
-- Objetivo: garantir integridade de valores enumerados e ranges em nivel de banco.
-- Sprint 2 - C12 (auditoria 2026-05-10)
-- Validado em prod: 354 registros 'PRODUCAO' (incluido nos tipos validos)

-- 1. tipo_custo_selecionado em custo_considerado
ALTER TABLE custo_considerado DROP CONSTRAINT IF EXISTS chk_tipo_custo_selecionado;
ALTER TABLE custo_considerado ADD CONSTRAINT chk_tipo_custo_selecionado
  CHECK (tipo_custo_selecionado IN ('MEDIO_MES', 'ULTIMO_CUSTO', 'MEDIO_ESTOQUE', 'BOM', 'MANUAL', 'PRODUCAO'));

-- 2. tipo_produto em custo_considerado
ALTER TABLE custo_considerado DROP CONSTRAINT IF EXISTS chk_tipo_produto_considerado;
ALTER TABLE custo_considerado ADD CONSTRAINT chk_tipo_produto_considerado
  CHECK (tipo_produto IN ('COMPRADO', 'INTERMEDIARIO', 'ACABADO'));

-- 3. tipo_produto em custo_mensal
ALTER TABLE custo_mensal DROP CONSTRAINT IF EXISTS chk_tipo_produto_mensal;
ALTER TABLE custo_mensal ADD CONSTRAINT chk_tipo_produto_mensal
  CHECK (tipo_produto IN ('COMPRADO', 'INTERMEDIARIO', 'ACABADO'));

-- 4. status em custo_mensal
ALTER TABLE custo_mensal DROP CONSTRAINT IF EXISTS chk_status_mensal;
ALTER TABLE custo_mensal ADD CONSTRAINT chk_status_mensal
  CHECK (status IN ('ABERTO', 'FECHADO'));

-- 5. mes/ano validos em custo_mensal
ALTER TABLE custo_mensal DROP CONSTRAINT IF EXISTS chk_mes_ano_validos;
ALTER TABLE custo_mensal ADD CONSTRAINT chk_mes_ano_validos
  CHECK (mes BETWEEN 1 AND 12 AND ano >= 2020);

-- 6. percentual_frete (0-100) em custo_frete
ALTER TABLE custo_frete DROP CONSTRAINT IF EXISTS chk_percentual_frete;
ALTER TABLE custo_frete ADD CONSTRAINT chk_percentual_frete
  CHECK (percentual_frete >= 0 AND percentual_frete <= 100);

-- 7. comissao_percentual (0-30) em regra_comissao
ALTER TABLE regra_comissao DROP CONSTRAINT IF EXISTS chk_comissao_percentual;
ALTER TABLE regra_comissao ADD CONSTRAINT chk_comissao_percentual
  CHECK (comissao_percentual >= 0 AND comissao_percentual <= 30);

-- 8. vigencia coerente em custo_frete
ALTER TABLE custo_frete DROP CONSTRAINT IF EXISTS chk_vigencia_coerente_frete;
ALTER TABLE custo_frete ADD CONSTRAINT chk_vigencia_coerente_frete
  CHECK (vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio);

-- 9. vigencia coerente em regra_comissao
ALTER TABLE regra_comissao DROP CONSTRAINT IF EXISTS chk_vigencia_coerente_comissao;
ALTER TABLE regra_comissao ADD CONSTRAINT chk_vigencia_coerente_comissao
  CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio);
