-- ============================================================
-- Script SQL para padronizar perfis fiscais no Render Shell
-- ============================================================
-- Uso: Copiar e colar no Render PostgreSQL Shell
--
-- IMPORTANTE: Este script NÃO infere/deduz cnpj_empresa_compradora.
-- Perfis sem empresa devem ser corrigidos manualmente via interface.
-- ============================================================

-- VERIFICAÇÃO INICIAL (rodar antes da migração)
SELECT
    'Diagnóstico Inicial' as etapa,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE cnpj_empresa_compradora IS NULL) as sem_empresa_corrigir_manual,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE reducao_bc_icms_esperada IS NULL) as reducao_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_icms_st_esperada IS NULL) as st_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_ipi_esperada IS NULL) as ipi_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_icms_esperada IS NULL) as icms_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_pis_esperada IS NULL) as pis_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_cofins_esperada IS NULL) as cofins_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor) as total;

-- ============================================================
-- ETAPA 1: Converter campos zeráveis NULL → 0.00
-- ============================================================

-- 1.1 Redução BC ICMS
UPDATE perfil_fiscal_produto_fornecedor
SET reducao_bc_icms_esperada = 0,
    atualizado_em = NOW()
WHERE reducao_bc_icms_esperada IS NULL;

-- 1.2 ICMS ST
UPDATE perfil_fiscal_produto_fornecedor
SET aliquota_icms_st_esperada = 0,
    atualizado_em = NOW()
WHERE aliquota_icms_st_esperada IS NULL;

-- 1.3 IPI
UPDATE perfil_fiscal_produto_fornecedor
SET aliquota_ipi_esperada = 0,
    atualizado_em = NOW()
WHERE aliquota_ipi_esperada IS NULL;

-- 1.4 ICMS
UPDATE perfil_fiscal_produto_fornecedor
SET aliquota_icms_esperada = 0,
    atualizado_em = NOW()
WHERE aliquota_icms_esperada IS NULL;

-- 1.5 PIS
UPDATE perfil_fiscal_produto_fornecedor
SET aliquota_pis_esperada = 0,
    atualizado_em = NOW()
WHERE aliquota_pis_esperada IS NULL;

-- 1.6 COFINS
UPDATE perfil_fiscal_produto_fornecedor
SET aliquota_cofins_esperada = 0,
    atualizado_em = NOW()
WHERE aliquota_cofins_esperada IS NULL;

-- NOTA: ETAPA 2 (inferir cnpj_empresa_compradora) foi REMOVIDA.
-- Perfis sem empresa compradora devem ser corrigidos MANUALMENTE via interface.
-- Para listar perfis sem empresa:
-- SELECT id, cod_produto, cnpj_fornecedor FROM perfil_fiscal_produto_fornecedor WHERE cnpj_empresa_compradora IS NULL;

-- ============================================================
-- ETAPA 2: Preencher nome_empresa onde ainda falta
-- ============================================================

UPDATE perfil_fiscal_produto_fornecedor
SET nome_empresa_compradora = CASE cnpj_empresa_compradora
        WHEN '61724241000330' THEN 'NACOM GOYA - CD'
        WHEN '61724241000178' THEN 'NACOM GOYA - FB'
        WHEN '61724241000259' THEN 'NACOM GOYA - SC'
        WHEN '18467441000163' THEN 'LA FAMIGLIA - LF'
        ELSE nome_empresa_compradora
    END,
    atualizado_em = NOW()
WHERE nome_empresa_compradora IS NULL
  AND cnpj_empresa_compradora IN ('61724241000330', '61724241000178', '61724241000259', '18467441000163');

-- ============================================================
-- ETAPA 3: Preencher campos fiscais do cadastro_primeira_compra
-- ============================================================

-- 3.1 CST ICMS
UPDATE perfil_fiscal_produto_fornecedor p
SET cst_icms_esperado = c.cst_icms,
    atualizado_em = NOW()
FROM cadastro_primeira_compra c
WHERE p.cst_icms_esperado IS NULL
  AND p.cnpj_fornecedor = c.cnpj_fornecedor
  AND p.cod_produto = c.cod_produto
  AND c.cst_icms IS NOT NULL
  AND c.status = 'validado';

-- 3.2 PIS
UPDATE perfil_fiscal_produto_fornecedor p
SET cst_pis_esperado = c.cst_pis,
    aliquota_pis_esperada = c.aliquota_pis,
    atualizado_em = NOW()
FROM cadastro_primeira_compra c
WHERE (p.cst_pis_esperado IS NULL OR p.aliquota_pis_esperada IS NULL)
  AND p.cnpj_fornecedor = c.cnpj_fornecedor
  AND p.cod_produto = c.cod_produto
  AND (c.cst_pis IS NOT NULL OR c.aliquota_pis IS NOT NULL)
  AND c.status = 'validado';

-- 3.3 COFINS
UPDATE perfil_fiscal_produto_fornecedor p
SET cst_cofins_esperado = c.cst_cofins,
    aliquota_cofins_esperada = c.aliquota_cofins,
    atualizado_em = NOW()
FROM cadastro_primeira_compra c
WHERE (p.cst_cofins_esperado IS NULL OR p.aliquota_cofins_esperada IS NULL)
  AND p.cnpj_fornecedor = c.cnpj_fornecedor
  AND p.cod_produto = c.cod_produto
  AND (c.cst_cofins IS NOT NULL OR c.aliquota_cofins IS NOT NULL)
  AND c.status = 'validado';

-- ============================================================
-- VERIFICAÇÃO FINAL (rodar após a migração)
-- ============================================================

SELECT
    'Verificação Final' as etapa,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE cnpj_empresa_compradora IS NULL) as sem_empresa_corrigir_manual,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE reducao_bc_icms_esperada IS NULL) as reducao_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_icms_st_esperada IS NULL) as st_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_ipi_esperada IS NULL) as ipi_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_icms_esperada IS NULL) as icms_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_pis_esperada IS NULL) as pis_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE aliquota_cofins_esperada IS NULL) as cofins_null,
    (SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor) as total;

-- Resultado esperado: reducao_null, st_null, ipi_null, icms_null, pis_null, cofins_null = 0
-- sem_empresa_corrigir_manual: corrigir via interface de edição
