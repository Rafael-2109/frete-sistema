-- ============================================================
-- Script SQL para Corrigir Valores Padrão de Motos
-- Data: 14/10/2025
-- Executar no Shell do Render
-- ============================================================

-- OBJETIVO:
-- Garantir que todas as motos tenham valores padrão corretos conforme o sistema espera

-- ============================================================
-- PASSO 1: Verificar estado atual (CONSULTA)
-- ============================================================

-- Total de motos ativas
SELECT COUNT(*) AS total_motos_ativas
FROM moto
WHERE ativo = TRUE;

-- Motos por status
SELECT
    status,
    COUNT(*) AS quantidade
FROM moto
WHERE ativo = TRUE
GROUP BY status
ORDER BY quantidade DESC;

-- Motos por status_pagamento_custo
SELECT
    status_pagamento_custo,
    COUNT(*) AS quantidade
FROM moto
WHERE ativo = TRUE
GROUP BY status_pagamento_custo
ORDER BY quantidade DESC;

-- ============================================================
-- PASSO 2: Identificar inconsistências (CONSULTA)
-- ============================================================

-- 2.1. Motos DISPONÍVEIS marcadas como reservadas
SELECT
    numero_chassi,
    status,
    reservado,
    'DISPONIVEL mas reservado=TRUE' AS inconsistencia
FROM moto
WHERE ativo = TRUE
  AND status = 'DISPONIVEL'
  AND reservado = TRUE;

-- 2.2. Motos RESERVADAS/VENDIDAS sem flag reservado
SELECT
    numero_chassi,
    status,
    reservado,
    'RESERVADA/VENDIDA mas reservado=FALSE' AS inconsistencia
FROM moto
WHERE ativo = TRUE
  AND status IN ('RESERVADA', 'VENDIDA')
  AND reservado = FALSE;

-- 2.3. Status de pagamento inconsistente com custo_pago
SELECT
    numero_chassi,
    custo_aquisicao,
    COALESCE(custo_pago, 0) AS custo_pago,
    status_pagamento_custo,
    CASE
        WHEN COALESCE(custo_pago, 0) = 0 THEN 'PENDENTE'
        WHEN COALESCE(custo_pago, 0) >= custo_aquisicao THEN 'PAGO'
        ELSE 'PARCIAL'
    END AS status_correto,
    'Status de pagamento inconsistente' AS inconsistencia
FROM moto
WHERE ativo = TRUE
  AND status_pagamento_custo != CASE
        WHEN COALESCE(custo_pago, 0) = 0 THEN 'PENDENTE'
        WHEN COALESCE(custo_pago, 0) >= custo_aquisicao THEN 'PAGO'
        ELSE 'PARCIAL'
    END;

-- 2.4. Motos PENDENTES com empresa_pagadora_id preenchido
SELECT
    numero_chassi,
    status_pagamento_custo,
    empresa_pagadora_id,
    'PENDENTE com empresa_pagadora_id' AS inconsistencia
FROM moto
WHERE ativo = TRUE
  AND status_pagamento_custo = 'PENDENTE'
  AND empresa_pagadora_id IS NOT NULL;

-- ============================================================
-- PASSO 3: EXECUTAR CORREÇÕES (CUIDADO!)
-- ============================================================

-- 3.1. Corrigir campo "reservado" de motos DISPONÍVEIS
UPDATE moto
SET
    reservado = FALSE,
    atualizado_em = NOW(),
    atualizado_por = 'Script SQL Correção Padrões'
WHERE ativo = TRUE
  AND status = 'DISPONIVEL'
  AND reservado = TRUE;

-- 3.2. Corrigir campo "reservado" de motos RESERVADAS/VENDIDAS
UPDATE moto
SET
    reservado = TRUE,
    atualizado_em = NOW(),
    atualizado_por = 'Script SQL Correção Padrões'
WHERE ativo = TRUE
  AND status IN ('RESERVADA', 'VENDIDA')
  AND reservado = FALSE;

-- 3.3. Corrigir status_pagamento_custo baseado em custo_pago
UPDATE moto
SET
    status_pagamento_custo = CASE
        WHEN COALESCE(custo_pago, 0) = 0 THEN 'PENDENTE'
        WHEN COALESCE(custo_pago, 0) >= custo_aquisicao THEN 'PAGO'
        ELSE 'PARCIAL'
    END,
    atualizado_em = NOW(),
    atualizado_por = 'Script SQL Correção Padrões'
WHERE ativo = TRUE
  AND status_pagamento_custo != CASE
        WHEN COALESCE(custo_pago, 0) = 0 THEN 'PENDENTE'
        WHEN COALESCE(custo_pago, 0) >= custo_aquisicao THEN 'PAGO'
        ELSE 'PARCIAL'
    END;

-- 3.4. Remover empresa_pagadora_id de motos PENDENTES
UPDATE moto
SET
    empresa_pagadora_id = NULL,
    atualizado_em = NOW(),
    atualizado_por = 'Script SQL Correção Padrões'
WHERE ativo = TRUE
  AND status_pagamento_custo = 'PENDENTE'
  AND empresa_pagadora_id IS NOT NULL;

-- ============================================================
-- PASSO 4: Verificar resultado (CONSULTA)
-- ============================================================

-- Estado final por status
SELECT
    status,
    COUNT(*) AS quantidade,
    SUM(CASE WHEN reservado THEN 1 ELSE 0 END) AS reservadas,
    SUM(CASE WHEN NOT reservado THEN 1 ELSE 0 END) AS nao_reservadas
FROM moto
WHERE ativo = TRUE
GROUP BY status
ORDER BY quantidade DESC;

-- Estado final por status_pagamento_custo
SELECT
    status_pagamento_custo,
    COUNT(*) AS quantidade,
    SUM(CASE WHEN empresa_pagadora_id IS NOT NULL THEN 1 ELSE 0 END) AS com_empresa_pagadora,
    SUM(CASE WHEN empresa_pagadora_id IS NULL THEN 1 ELSE 0 END) AS sem_empresa_pagadora
FROM moto
WHERE ativo = TRUE
GROUP BY status_pagamento_custo
ORDER BY quantidade DESC;

-- Verificar se ainda existem inconsistências
SELECT
    'Motos DISPONIVEL com reservado=TRUE' AS tipo_inconsistencia,
    COUNT(*) AS quantidade
FROM moto
WHERE ativo = TRUE
  AND status = 'DISPONIVEL'
  AND reservado = TRUE

UNION ALL

SELECT
    'Motos RESERVADA/VENDIDA com reservado=FALSE' AS tipo_inconsistencia,
    COUNT(*) AS quantidade
FROM moto
WHERE ativo = TRUE
  AND status IN ('RESERVADA', 'VENDIDA')
  AND reservado = FALSE

UNION ALL

SELECT
    'Status pagamento inconsistente' AS tipo_inconsistencia,
    COUNT(*) AS quantidade
FROM moto
WHERE ativo = TRUE
  AND status_pagamento_custo != CASE
        WHEN COALESCE(custo_pago, 0) = 0 THEN 'PENDENTE'
        WHEN COALESCE(custo_pago, 0) >= custo_aquisicao THEN 'PAGO'
        ELSE 'PARCIAL'
    END

UNION ALL

SELECT
    'PENDENTE com empresa_pagadora_id' AS tipo_inconsistencia,
    COUNT(*) AS quantidade
FROM moto
WHERE ativo = TRUE
  AND status_pagamento_custo = 'PENDENTE'
  AND empresa_pagadora_id IS NOT NULL;

-- ============================================================
-- NOTAS IMPORTANTES:
-- ============================================================

-- 1. EXECUTE PASSO 1 E 2 PRIMEIRO para ver o estado atual e identificar problemas
-- 2. EXECUTE PASSO 3 somente após confirmar que as correções estão corretas
-- 3. EXECUTE PASSO 4 para verificar se todas as inconsistências foram corrigidas
-- 4. Este script NÃO altera dados de negócio, apenas corrige flags de controle

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================
