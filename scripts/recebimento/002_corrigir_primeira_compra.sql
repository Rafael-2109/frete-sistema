-- ============================================================================
-- MIGRAÇÃO 002: Corrigir dados em cadastro_primeira_compra
-- ============================================================================
-- Problema:
--   100% dos registros (345) estão com cnpj_empresa_compradora vazio
--   100% dos registros (345) estão com razao_empresa_compradora vazio
--   100% dos registros (345) têm cod_produto = product_id (numérico)
--
-- Solução parcial (apenas razao_empresa_compradora):
--   Este script corrige APENAS razao_empresa_compradora para registros
--   que JÁ tenham cnpj_empresa_compradora preenchido.
--
-- IMPORTANTE:
--   A correção completa (incluindo cnpj_empresa_compradora e cod_produto)
--   REQUER o script Python pois precisa consultar dados do Odoo:
--   - cnpj_empresa_compradora: vem do DFE no Odoo (nfe_infnfe_dest_cnpj)
--   - cod_produto: precisa converter product_id para default_code via Odoo
--
--   Use: python scripts/recebimento/002_corrigir_primeira_compra.py
--
-- CNPJs mapeados (fonte: app/utils/cnpj_utils.py):
--   61724241000330 -> NACOM GOYA - CD
--   61724241000178 -> NACOM GOYA - FB
--   61724241000259 -> NACOM GOYA - SC
--   18467441000163 -> LA FAMIGLIA - LF
--
-- Data: 26/01/2026
-- ============================================================================

-- ============================================================================
-- PASSO 1: DIAGNÓSTICO INICIAL (executar primeiro!)
-- ============================================================================

-- Contagem geral
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN cnpj_empresa_compradora IS NULL OR cnpj_empresa_compradora = '' THEN 1 END) as sem_cnpj,
    COUNT(CASE WHEN razao_empresa_compradora IS NULL OR razao_empresa_compradora = '' THEN 1 END) as sem_razao,
    COUNT(CASE WHEN cod_produto ~ '^[0-9]+$' THEN 1 END) as cod_numerico
FROM cadastro_primeira_compra;

-- Distribuição por CNPJ (se houver)
SELECT
    cnpj_empresa_compradora,
    razao_empresa_compradora,
    COUNT(*) as qtd
FROM cadastro_primeira_compra
WHERE cnpj_empresa_compradora IS NOT NULL
  AND cnpj_empresa_compradora != ''
GROUP BY cnpj_empresa_compradora, razao_empresa_compradora
ORDER BY qtd DESC;

-- Amostra de cod_produto (verificar se são numéricos = product_id)
SELECT id, odoo_dfe_id, cod_produto, nome_produto
FROM cadastro_primeira_compra
ORDER BY id
LIMIT 20;

-- ============================================================================
-- PASSO 2: CORRIGIR RAZÃO (apenas se CNPJ já estiver preenchido)
-- ============================================================================
-- NOTA: Se cnpj_empresa_compradora estiver vazio, este UPDATE não faz nada.
--       Use o script Python para preencher o CNPJ primeiro.

UPDATE cadastro_primeira_compra
SET razao_empresa_compradora = CASE cnpj_empresa_compradora
    WHEN '61724241000330' THEN 'NACOM GOYA - CD'
    WHEN '61724241000178' THEN 'NACOM GOYA - FB'
    WHEN '61724241000259' THEN 'NACOM GOYA - SC'
    WHEN '18467441000163' THEN 'LA FAMIGLIA - LF'
END
WHERE (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '')
  AND cnpj_empresa_compradora IN ('61724241000330', '61724241000178', '61724241000259', '18467441000163');

-- ============================================================================
-- PASSO 3: VERIFICAR RESULTADO
-- ============================================================================

-- Contagem após correção parcial
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN razao_empresa_compradora IS NULL OR razao_empresa_compradora = '' THEN 1 END) as ainda_sem_razao,
    COUNT(CASE WHEN razao_empresa_compradora IS NOT NULL AND razao_empresa_compradora != '' THEN 1 END) as com_razao
FROM cadastro_primeira_compra;

-- ============================================================================
-- CORREÇÃO COMPLETA (REQUER SCRIPT PYTHON)
-- ============================================================================
-- Se o diagnóstico mostrar que cnpj_empresa_compradora está vazio,
-- você DEVE usar o script Python que consulta o Odoo:
--
--   cd /home/rafaelnascimento/projetos/frete_sistema
--   source .venv/bin/activate
--   python scripts/recebimento/002_corrigir_primeira_compra.py --dry-run
--   python scripts/recebimento/002_corrigir_primeira_compra.py
--
-- O script Python faz:
-- 1. Busca cnpj do DFE no Odoo (nfe_infnfe_dest_cnpj)
-- 2. Preenche razao via mapeamento EMPRESAS_CNPJ_NOME
-- 3. Converte cod_produto (product_id -> default_code) consultando Odoo

-- ============================================================================
-- ROLLBACK (se necessário)
-- ============================================================================

-- Para reverter apenas razao:
-- UPDATE cadastro_primeira_compra
-- SET razao_empresa_compradora = NULL
-- WHERE razao_empresa_compradora IN ('NACOM GOYA - CD', 'NACOM GOYA - FB', 'NACOM GOYA - SC', 'LA FAMIGLIA - LF');

-- ============================================================================
-- INFORMAÇÃO ADICIONAL: Conversão de cod_produto
-- ============================================================================
-- A conversão de cod_produto (product_id -> default_code) NÃO pode ser feita
-- apenas com SQL pois requer mapeamento do Odoo (product.product).
--
-- Se você precisar de uma consulta SQL para verificar os product_ids:

-- SELECT
--     cpc.id,
--     cpc.cod_produto as product_id_atual,
--     cpc.nome_produto
-- FROM cadastro_primeira_compra cpc
-- WHERE cpc.cod_produto ~ '^[0-9]+$'
-- ORDER BY cpc.id;
--
-- O script Python faz a conversão correta consultando:
-- product.product onde id = cod_produto e retorna default_code
