-- ==========================================================================================================
-- SCRIPT SQL PARA ATUALIZAR company_id EM REQUISIÇÕES BASEADO NO PREFIXO
-- Execução: Render PostgreSQL Shell ou Local
-- ==========================================================================================================

-- ==========================================================================================================
-- PASSO 1: VERIFICAR SITUAÇÃO ATUAL
-- ==========================================================================================================

SELECT 'SITUAÇÃO ATUAL' AS info;

SELECT
    SUBSTRING(num_requisicao FROM 1 FOR 7) as prefixo,
    COUNT(*) FILTER (WHERE company_id IS NULL) as sem_company,
    COUNT(*) FILTER (WHERE company_id IS NOT NULL) as com_company,
    COUNT(*) as total
FROM requisicao_compras
GROUP BY prefixo
ORDER BY total DESC;


-- ==========================================================================================================
-- PASSO 2: ATUALIZAR company_id BASEADO NO PREFIXO
-- ==========================================================================================================

-- Requisições FB (Fiberplast - NACOM GOYA)
UPDATE requisicao_compras
SET company_id = 'NACOM GOYA - FB'
WHERE num_requisicao LIKE 'REQ/FB/%'
  AND company_id IS NULL;

-- Requisições LF (La Famiglia)
UPDATE requisicao_compras
SET company_id = 'LA FAMIGLIA - LF'
WHERE num_requisicao LIKE 'REQ/LF/%'
  AND company_id IS NULL;

-- Requisições SC (Santa Catarina - verificar nome correto)
UPDATE requisicao_compras
SET company_id = 'NACOM GOYA - SC'
WHERE num_requisicao LIKE 'REQ/SC/%'
  AND company_id IS NULL;

-- Requisições CD (Centro de Distribuição)
UPDATE requisicao_compras
SET company_id = 'NACOM GOYA - CD'
WHERE num_requisicao LIKE 'REQ/CD/%'
  AND company_id IS NULL;


-- ==========================================================================================================
-- PASSO 3: VERIFICAR RESULTADO
-- ==========================================================================================================

SELECT 'RESULTADO APÓS UPDATE' AS info;

SELECT
    SUBSTRING(num_requisicao FROM 1 FOR 7) as prefixo,
    COUNT(*) FILTER (WHERE company_id IS NULL) as sem_company,
    COUNT(*) FILTER (WHERE company_id IS NOT NULL) as com_company,
    COUNT(*) as total
FROM requisicao_compras
GROUP BY prefixo
ORDER BY total DESC;


-- ==========================================================================================================
-- PASSO 4: LISTAR EMPRESAS E TOTAIS
-- ==========================================================================================================

SELECT 'EMPRESAS APÓS UPDATE' AS info;

SELECT
    company_id,
    COUNT(*) as total_requisicoes
FROM requisicao_compras
WHERE company_id IS NOT NULL
GROUP BY company_id
ORDER BY total_requisicoes DESC;


-- ==========================================================================================================
-- PASSO 5: VERIFICAR SE AINDA HÁ REQUISIÇÕES SEM company_id
-- ==========================================================================================================

SELECT 'REQUISIÇÕES SEM company_id (se houver)' AS info;

SELECT
    num_requisicao,
    cod_produto,
    data_requisicao_criacao
FROM requisicao_compras
WHERE company_id IS NULL
LIMIT 10;


-- ==========================================================================================================
-- PASSO 6: ATUALIZAR HISTÓRICO (OPCIONAL - SE NECESSÁRIO)
-- ==========================================================================================================

/*
-- Atualizar histórico de requisições também (se necessário)
UPDATE historico_requisicao_compras
SET company_id = 'NACOM GOYA - FB'
WHERE num_requisicao LIKE 'REQ/FB/%'
  AND company_id IS NULL;

UPDATE historico_requisicao_compras
SET company_id = 'LA FAMIGLIA - LF'
WHERE num_requisicao LIKE 'REQ/LF/%'
  AND company_id IS NULL;

UPDATE historico_requisicao_compras
SET company_id = 'NACOM GOYA - SC'
WHERE num_requisicao LIKE 'REQ/SC/%'
  AND company_id IS NULL;

UPDATE historico_requisicao_compras
SET company_id = 'NACOM GOYA - CD'
WHERE num_requisicao LIKE 'REQ/CD/%'
  AND company_id IS NULL;
*/


-- ==========================================================================================================
-- ✅ VERSÃO EXECUTÁVEL COMPLETA (COPIE E COLE TUDO DE UMA VEZ)
-- ==========================================================================================================

/*
BEGIN;

-- Atualizar requisições
UPDATE requisicao_compras SET company_id = 'NACOM GOYA - FB' WHERE num_requisicao LIKE 'REQ/FB/%' AND company_id IS NULL;
UPDATE requisicao_compras SET company_id = 'LA FAMIGLIA - LF' WHERE num_requisicao LIKE 'REQ/LF/%' AND company_id IS NULL;
UPDATE requisicao_compras SET company_id = 'NACOM GOYA - SC' WHERE num_requisicao LIKE 'REQ/SC/%' AND company_id IS NULL;
UPDATE requisicao_compras SET company_id = 'NACOM GOYA - CD' WHERE num_requisicao LIKE 'REQ/CD/%' AND company_id IS NULL;

-- Verificar resultado
SELECT
    SUBSTRING(num_requisicao FROM 1 FOR 7) as prefixo,
    COUNT(*) FILTER (WHERE company_id IS NULL) as sem_company,
    COUNT(*) FILTER (WHERE company_id IS NOT NULL) as com_company,
    COUNT(*) as total
FROM requisicao_compras
GROUP BY prefixo
ORDER BY total DESC;

-- Se estiver OK, commit. Se não, rollback.
COMMIT;
-- ROLLBACK;

*/


-- ==========================================================================================================
-- 📋 INSTRUÇÕES DE USO
-- ==========================================================================================================

/*
OPÇÃO 1 - EXECUTAR PASSO A PASSO:
1. Execute PASSO 1 para ver situação atual
2. Execute PASSO 2 para atualizar
3. Execute PASSO 3 para verificar resultado
4. Execute PASSO 4 para ver empresas
5. Execute PASSO 5 para verificar se sobrou algo

OPÇÃO 2 - EXECUTAR TUDO DE UMA VEZ:
1. Descomente o bloco BEGIN...COMMIT no final
2. Execute tudo de uma vez
3. Se o resultado estiver correto, mantenha COMMIT
4. Se algo estiver errado, mude para ROLLBACK

APÓS EXECUTAR:
1. Acesse /manufatura/requisicoes-compras
2. Busque por qualquer requisição
3. Você verá o company_id exibido: 🏢 Nome da Empresa
*/
