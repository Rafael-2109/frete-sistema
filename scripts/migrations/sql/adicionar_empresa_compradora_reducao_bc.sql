-- =============================================================================
-- Migration: Adicionar Empresa Compradora + Reducao BC ICMS
-- =============================================================================
-- Fase 1 - Validacao Fiscal - Alteracoes:
-- 1. Adicionar cnpj_empresa_compradora em 4 tabelas
-- 2. Adicionar reducao_bc_icms em perfil e primeira_compra
-- 3. Alterar constraint unica do perfil fiscal
--
-- Empresas Compradoras:
-- - NACOM GOYA - CD (ID 34): 61.724.241/0003-30
-- - NACOM GOYA - FB (ID 1): 61.724.241/0001-78
-- - NACOM GOYA - SC (ID 33): 61.724.241/0002-59
-- - LA FAMIGLIA - LF (ID 35): 18.467.441/0001-63
--
-- Data: 22/01/2026
-- Executar no Shell do Render
-- =============================================================================

-- 1. Adicionar campos em perfil_fiscal_produto_fornecedor
ALTER TABLE perfil_fiscal_produto_fornecedor
ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
ADD COLUMN IF NOT EXISTS reducao_bc_icms_esperada NUMERIC(5,2);

-- 2. Adicionar campos em divergencia_fiscal
ALTER TABLE divergencia_fiscal
ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);

-- 3. Adicionar campos em cadastro_primeira_compra
ALTER TABLE cadastro_primeira_compra
ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255),
ADD COLUMN IF NOT EXISTS reducao_bc_icms NUMERIC(5,2);

-- 4. Adicionar campos em validacao_fiscal_dfe
ALTER TABLE validacao_fiscal_dfe
ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);

-- 5. Criar indices
CREATE INDEX IF NOT EXISTS idx_perfil_fiscal_cnpj_empresa
ON perfil_fiscal_produto_fornecedor(cnpj_empresa_compradora);

CREATE INDEX IF NOT EXISTS idx_divergencia_cnpj_empresa
ON divergencia_fiscal(cnpj_empresa_compradora);

CREATE INDEX IF NOT EXISTS idx_primeira_compra_cnpj_empresa
ON cadastro_primeira_compra(cnpj_empresa_compradora);

CREATE INDEX IF NOT EXISTS idx_validacao_dfe_cnpj_empresa
ON validacao_fiscal_dfe(cnpj_empresa_compradora);

-- 6. Remover constraint antiga (se existir)
ALTER TABLE perfil_fiscal_produto_fornecedor
DROP CONSTRAINT IF EXISTS uq_perfil_fiscal_produto_fornecedor;

-- 7. Criar nova constraint unica
ALTER TABLE perfil_fiscal_produto_fornecedor
ADD CONSTRAINT uq_perfil_fiscal_empresa_fornecedor_produto
UNIQUE (cnpj_empresa_compradora, cnpj_fornecedor, cod_produto);

-- =============================================================================
-- Verificacao (executar apos migration)
-- =============================================================================
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'perfil_fiscal_produto_fornecedor'
-- AND column_name IN ('cnpj_empresa_compradora', 'reducao_bc_icms_esperada');
--
-- SELECT constraint_name
-- FROM information_schema.table_constraints
-- WHERE table_name = 'perfil_fiscal_produto_fornecedor'
-- AND constraint_type = 'UNIQUE';
