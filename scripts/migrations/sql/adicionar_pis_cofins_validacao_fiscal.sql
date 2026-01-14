-- Migration: Adicionar campos PIS e COFINS nas tabelas de validacao fiscal
-- Para executar no Shell do Render

-- 1. perfil_fiscal_produto_fornecedor
ALTER TABLE perfil_fiscal_produto_fornecedor ADD COLUMN IF NOT EXISTS cst_pis_esperado VARCHAR(5);
ALTER TABLE perfil_fiscal_produto_fornecedor ADD COLUMN IF NOT EXISTS aliquota_pis_esperada NUMERIC(5,2);
ALTER TABLE perfil_fiscal_produto_fornecedor ADD COLUMN IF NOT EXISTS cst_cofins_esperado VARCHAR(5);
ALTER TABLE perfil_fiscal_produto_fornecedor ADD COLUMN IF NOT EXISTS aliquota_cofins_esperada NUMERIC(5,2);

-- 2. cadastro_primeira_compra
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS cst_pis VARCHAR(5);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS aliquota_pis NUMERIC(5,2);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS bc_pis NUMERIC(15,2);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS cst_cofins VARCHAR(5);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS aliquota_cofins NUMERIC(5,2);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS bc_cofins NUMERIC(15,2);
