-- ============================================================================
-- MIGRAÇÃO 001: Corrigir razao_empresa_compradora em validacao_nf_po_dfe
-- ============================================================================
-- Problema:
--   100% dos registros (181) estão com razao_empresa_compradora = NULL
--   Campo cnpj_empresa_compradora está preenchido em 93% dos registros
--
-- Solução:
--   Usar mapeamento de CNPJs das empresas do grupo para preencher razão
--
-- Uso no Render Shell:
--   1. Conectar ao banco: psql $DATABASE_URL
--   2. Executar diagnóstico (SELECT abaixo)
--   3. Executar UPDATE se diagnóstico estiver correto
--   4. Verificar resultado
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
    COUNT(CASE WHEN razao_empresa_compradora IS NULL OR razao_empresa_compradora = '' THEN 1 END) as sem_razao
FROM validacao_nf_po_dfe;

-- Distribuição por CNPJ (para verificar mapeamento)
SELECT
    cnpj_empresa_compradora,
    razao_empresa_compradora,
    COUNT(*) as qtd
FROM validacao_nf_po_dfe
WHERE cnpj_empresa_compradora IS NOT NULL
  AND cnpj_empresa_compradora != ''
GROUP BY cnpj_empresa_compradora, razao_empresa_compradora
ORDER BY qtd DESC;

-- ============================================================================
-- PASSO 2: PREVIEW DO UPDATE (executar para ver o que será alterado)
-- ============================================================================

SELECT
    id,
    odoo_dfe_id,
    numero_nf,
    cnpj_empresa_compradora,
    razao_empresa_compradora as razao_atual,
    CASE cnpj_empresa_compradora
        WHEN '61724241000330' THEN 'NACOM GOYA - CD'
        WHEN '61724241000178' THEN 'NACOM GOYA - FB'
        WHEN '61724241000259' THEN 'NACOM GOYA - SC'
        WHEN '18467441000163' THEN 'LA FAMIGLIA - LF'
        ELSE '⚠ SEM MAPEAMENTO'
    END as razao_nova
FROM validacao_nf_po_dfe
WHERE (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '')
  AND cnpj_empresa_compradora IS NOT NULL
  AND cnpj_empresa_compradora != ''
ORDER BY id;

-- ============================================================================
-- PASSO 3: EXECUTAR CORREÇÃO
-- ============================================================================

-- ATENÇÃO: Confirme que o preview (PASSO 2) está correto antes de executar!

UPDATE validacao_nf_po_dfe
SET razao_empresa_compradora = CASE cnpj_empresa_compradora
    WHEN '61724241000330' THEN 'NACOM GOYA - CD'
    WHEN '61724241000178' THEN 'NACOM GOYA - FB'
    WHEN '61724241000259' THEN 'NACOM GOYA - SC'
    WHEN '18467441000163' THEN 'LA FAMIGLIA - LF'
END
WHERE (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '')
  AND cnpj_empresa_compradora IN ('61724241000330', '61724241000178', '61724241000259', '18467441000163');

-- Mensagem esperada: UPDATE <N> onde N = número de registros corrigidos

-- ============================================================================
-- PASSO 4: VERIFICAR RESULTADO
-- ============================================================================

-- Contagem após correção
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN razao_empresa_compradora IS NULL OR razao_empresa_compradora = '' THEN 1 END) as ainda_sem_razao,
    COUNT(CASE WHEN razao_empresa_compradora IS NOT NULL AND razao_empresa_compradora != '' THEN 1 END) as com_razao
FROM validacao_nf_po_dfe;

-- CNPJs que NÃO foram mapeados (se houver, adicionar em cnpj_utils.py)
SELECT DISTINCT cnpj_empresa_compradora, COUNT(*) as qtd
FROM validacao_nf_po_dfe
WHERE (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '')
  AND cnpj_empresa_compradora IS NOT NULL
  AND cnpj_empresa_compradora != ''
GROUP BY cnpj_empresa_compradora;

-- ============================================================================
-- ROLLBACK (se necessário)
-- ============================================================================

-- Para reverter, execute:
-- UPDATE validacao_nf_po_dfe
-- SET razao_empresa_compradora = NULL
-- WHERE razao_empresa_compradora IN ('NACOM GOYA - CD', 'NACOM GOYA - FB', 'NACOM GOYA - SC', 'LA FAMIGLIA - LF');
