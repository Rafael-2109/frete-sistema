-- =============================================================================
-- Migration: Adicionar Empresa Compradora em tabelas NF-PO
-- =============================================================================
-- Bug Fix - Fase 1 Validacao Fiscal
-- Adiciona cnpj_empresa_compradora e razao_empresa_compradora nas tabelas:
-- 1. validacao_nf_po_dfe
-- 2. divergencia_nf_po
--
-- Data: 22/01/2026
-- Executar no Shell do Render
-- =============================================================================

-- 1. Adicionar campos em validacao_nf_po_dfe
ALTER TABLE validacao_nf_po_dfe
ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);

-- 2. Adicionar campos em divergencia_nf_po
ALTER TABLE divergencia_nf_po
ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);

-- 3. Criar indices
CREATE INDEX IF NOT EXISTS idx_validacao_nf_po_dfe_cnpj_empresa
ON validacao_nf_po_dfe(cnpj_empresa_compradora);

CREATE INDEX IF NOT EXISTS idx_divergencia_nf_po_cnpj_empresa
ON divergencia_nf_po(cnpj_empresa_compradora);

-- =============================================================================
-- Verificacao (executar apos migration)
-- =============================================================================
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name IN ('validacao_nf_po_dfe', 'divergencia_nf_po')
-- AND column_name IN ('cnpj_empresa_compradora', 'razao_empresa_compradora');
