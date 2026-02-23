-- ============================================================================
-- Cleanup de registros intercompany em contas_a_pagar e contas_a_receber
-- ============================================================================
--
-- Contexto:
--   O filtro intercompany foi adicionado em sincronizacao_contas_pagar_service.py:508
--   e contas_receber_service.py:314, mas registros importados ANTES do fix ainda
--   existem no banco. Este script remove esses registros.
--
-- CNPJs do grupo Nacom:
--   61.724.241 (Nacom Goya - matriz e filiais)
--   18.467.441 (La Famiglia)
--
-- Dependencias FK mapeadas:
--   extrato_item_titulo.titulo_pagar_id   → contas_a_pagar.id
--   extrato_item_titulo.titulo_receber_id → contas_a_receber.id
--   contas_a_receber_reconciliacao.conta_a_receber_id → contas_a_receber.id
--   baixa_pagamento_item.titulo_id        → Odoo line ID (NAO FK local) → nao precisa limpar
--
-- Uso no Render Shell:
--   1. Copiar FASE 1 e executar (verificacao)
--   2. Conferir contagens
--   3. Copiar FASE 2 e executar (cleanup)
--   4. Copiar FASE 3 e executar (verificacao pos)
--
-- Autor: Sistema de Fretes
-- Data: 2026-02-23
-- ============================================================================


-- ============================================================================
-- FASE 1: VERIFICACAO (apenas SELECT — nao modifica nada)
-- ============================================================================

-- 1a. Contas a pagar intercompany (esperado: ~1.188)
SELECT 'CONTAS_A_PAGAR intercompany' AS check,
       COUNT(*) AS total
FROM contas_a_pagar
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%';

-- 1b. Contas a receber intercompany (esperado: ~12)
SELECT 'CONTAS_A_RECEBER intercompany' AS check,
       COUNT(*) AS total
FROM contas_a_receber
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%';

-- 1c. extrato_item_titulo filhos (pagar) — esperado: 0 ou poucos
SELECT 'EXTRATO_ITEM_TITULO filhos (pagar)' AS check,
       COUNT(*) AS total
FROM extrato_item_titulo eit
WHERE eit.titulo_pagar_id IN (
    SELECT id FROM contas_a_pagar
    WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
       OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
);

-- 1d. extrato_item_titulo filhos (receber) — esperado: 0
SELECT 'EXTRATO_ITEM_TITULO filhos (receber)' AS check,
       COUNT(*) AS total
FROM extrato_item_titulo eit
WHERE eit.titulo_receber_id IN (
    SELECT id FROM contas_a_receber
    WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
       OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
);

-- 1e. contas_a_receber_reconciliacao filhos — esperado: 0
SELECT 'RECONCILIACAO filhos (receber)' AS check,
       COUNT(*) AS total
FROM contas_a_receber_reconciliacao carr
WHERE carr.conta_a_receber_id IN (
    SELECT id FROM contas_a_receber
    WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
       OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
);

-- 1f. Amostra de registros (para conferencia visual)
SELECT id, cnpj, raz_social_red, titulo_nf, parcela, empresa,
       valor_original, valor_residual, vencimento
FROM contas_a_pagar
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
LIMIT 10;

SELECT id, cnpj, raz_social, titulo_nf, parcela, empresa,
       valor_original, valor_residual, vencimento
FROM contas_a_receber
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
LIMIT 10;


-- ============================================================================
-- FASE 2: CLEANUP (executar DENTRO de transacao)
-- ============================================================================

BEGIN;

-- Step 1: Remover vinculos extrato ↔ titulo pagar intercompany
DELETE FROM extrato_item_titulo
WHERE titulo_pagar_id IN (
    SELECT id FROM contas_a_pagar
    WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
       OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
);

-- Step 2: Remover vinculos extrato ↔ titulo receber intercompany
DELETE FROM extrato_item_titulo
WHERE titulo_receber_id IN (
    SELECT id FROM contas_a_receber
    WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
       OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
);

-- Step 3: Remover reconciliacoes de receber intercompany
DELETE FROM contas_a_receber_reconciliacao
WHERE conta_a_receber_id IN (
    SELECT id FROM contas_a_receber
    WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
       OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%'
);

-- Step 4: Remover contas a pagar intercompany
DELETE FROM contas_a_pagar
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%';

-- Step 5: Remover contas a receber intercompany
DELETE FROM contas_a_receber
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%';

COMMIT;


-- ============================================================================
-- FASE 3: VERIFICACAO POS-CLEANUP
-- ============================================================================

-- Deve retornar 0 para ambas
SELECT 'CONTAS_A_PAGAR pos-cleanup' AS check,
       COUNT(*) AS total
FROM contas_a_pagar
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%';

SELECT 'CONTAS_A_RECEBER pos-cleanup' AS check,
       COUNT(*) AS total
FROM contas_a_receber
WHERE cnpj LIKE '61.724.241%' OR cnpj LIKE '18.467.441%'
   OR cnpj LIKE '61724241%'  OR cnpj LIKE '18467441%';
