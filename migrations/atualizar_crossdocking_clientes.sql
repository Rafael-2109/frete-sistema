-- ============================================================
-- Script SQL para atualizar CrossDocking em Clientes
-- Data: 14/10/2025
-- Executar no Shell do Render
-- ============================================================

-- REGRA DE NEGÓCIO:
-- Marcar crossdocking=TRUE para clientes que atendam TODAS as condições:
-- 1. NÃO seja do vendedor "DANI" (vendedor_id diferente do ID do vendedor DANI)
-- 2. NÃO seja do estado de São Paulo (estado_cliente != 'SP')
-- 3. NÃO seja o CNPJ 62009696000174

-- ============================================================
-- PASSO 1: Verificar estado atual (CONSULTA)
-- ============================================================

-- Total de clientes ativos
SELECT COUNT(*) AS total_clientes_ativos
FROM cliente_moto
WHERE ativo = TRUE;

-- Clientes por status de crossdocking
SELECT
    crossdocking,
    COUNT(*) AS quantidade
FROM cliente_moto
WHERE ativo = TRUE
GROUP BY crossdocking
ORDER BY crossdocking;

-- Verificar ID do vendedor DANI (se existir)
SELECT id, vendedor, equipe_vendas_id
FROM vendedor_moto
WHERE vendedor ILIKE '%DANI%' AND ativo = TRUE;

-- ============================================================
-- PASSO 2: Simulação - Ver quais clientes serão marcados
-- ============================================================

-- Listar clientes que SERÃO marcados como CrossDocking=TRUE
SELECT
    c.id,
    c.cnpj_cliente,
    c.cliente,
    c.estado_cliente,
    v.vendedor,
    c.crossdocking AS crossdocking_atual,
    'TRUE' AS novo_crossdocking
FROM cliente_moto c
LEFT JOIN vendedor_moto v ON c.vendedor_id = v.id
WHERE c.ativo = TRUE
  -- NÃO é do vendedor DANI (assumindo que ID é diferente)
  AND (c.vendedor_id IS NULL OR c.vendedor_id NOT IN (
      SELECT id FROM vendedor_moto WHERE vendedor ILIKE '%DANI%' AND ativo = TRUE
  ))
  -- NÃO é de São Paulo
  AND (c.estado_cliente IS NULL OR UPPER(c.estado_cliente) != 'SP')
  -- NÃO é o CNPJ exceção
  AND REPLACE(REPLACE(REPLACE(c.cnpj_cliente, '.', ''), '/', ''), '-', '') != '62009696000174'
ORDER BY c.cliente;

-- Listar clientes que ficarão como CrossDocking=FALSE
SELECT
    c.id,
    c.cnpj_cliente,
    c.cliente,
    c.estado_cliente,
    v.vendedor,
    c.crossdocking AS crossdocking_atual,
    'FALSE' AS novo_crossdocking,
    CASE
        WHEN c.vendedor_id IN (SELECT id FROM vendedor_moto WHERE vendedor ILIKE '%DANI%' AND ativo = TRUE) THEN 'É do vendedor DANI'
        WHEN UPPER(c.estado_cliente) = 'SP' THEN 'É de São Paulo'
        WHEN REPLACE(REPLACE(REPLACE(c.cnpj_cliente, '.', ''), '/', ''), '-', '') = '62009696000174' THEN 'É o CNPJ exceção'
        ELSE 'Outro motivo'
    END AS motivo
FROM cliente_moto c
LEFT JOIN vendedor_moto v ON c.vendedor_id = v.id
WHERE c.ativo = TRUE
  AND (
      -- É do vendedor DANI
      c.vendedor_id IN (SELECT id FROM vendedor_moto WHERE vendedor ILIKE '%DANI%' AND ativo = TRUE)
      -- OU é de São Paulo
      OR UPPER(c.estado_cliente) = 'SP'
      -- OU é o CNPJ exceção
      OR REPLACE(REPLACE(REPLACE(c.cnpj_cliente, '.', ''), '/', ''), '-', '') = '62009696000174'
  )
ORDER BY c.cliente;

-- ============================================================
-- PASSO 3: EXECUTAR ATUALIZAÇÃO (CUIDADO!)
-- ============================================================

-- Atualizar para CrossDocking=TRUE (clientes fora de SP, não DANI, não CNPJ exceção)
UPDATE cliente_moto
SET
    crossdocking = TRUE,
    atualizado_em = NOW(),
    atualizado_por = 'Script SQL CrossDocking'
WHERE ativo = TRUE
  -- NÃO é do vendedor DANI
  AND (vendedor_id IS NULL OR vendedor_id NOT IN (
      SELECT id FROM vendedor_moto WHERE vendedor ILIKE '%DANI%' AND ativo = TRUE
  ))
  -- NÃO é de São Paulo
  AND (estado_cliente IS NULL OR UPPER(estado_cliente) != 'SP')
  -- NÃO é o CNPJ exceção
  AND REPLACE(REPLACE(REPLACE(cnpj_cliente, '.', ''), '/', ''), '-', '') != '62009696000174';

-- Atualizar para CrossDocking=FALSE (clientes de SP, DANI ou CNPJ exceção)
UPDATE cliente_moto
SET
    crossdocking = FALSE,
    atualizado_em = NOW(),
    atualizado_por = 'Script SQL CrossDocking'
WHERE ativo = TRUE
  AND (
      -- É do vendedor DANI
      vendedor_id IN (SELECT id FROM vendedor_moto WHERE vendedor ILIKE '%DANI%' AND ativo = TRUE)
      -- OU é de São Paulo
      OR UPPER(estado_cliente) = 'SP'
      -- OU é o CNPJ exceção
      OR REPLACE(REPLACE(REPLACE(cnpj_cliente, '.', ''), '/', ''), '-', '') = '62009696000174'
  );

-- ============================================================
-- PASSO 4: Verificar resultado (CONSULTA)
-- ============================================================

-- Novo estado após atualização
SELECT
    crossdocking,
    COUNT(*) AS quantidade
FROM cliente_moto
WHERE ativo = TRUE
GROUP BY crossdocking
ORDER BY crossdocking;

-- Clientes marcados como CrossDocking por estado
SELECT
    c.estado_cliente,
    COUNT(*) AS total_clientes,
    SUM(CASE WHEN c.crossdocking THEN 1 ELSE 0 END) AS com_crossdocking,
    SUM(CASE WHEN NOT c.crossdocking THEN 1 ELSE 0 END) AS sem_crossdocking
FROM cliente_moto c
WHERE c.ativo = TRUE
GROUP BY c.estado_cliente
ORDER BY total_clientes DESC;

-- ============================================================
-- NOTAS IMPORTANTES:
-- ============================================================

-- 1. EXECUTE PASSO 1 E 2 PRIMEIRO para ver o estado atual e simular
-- 2. EXECUTE PASSO 3 somente após confirmar que a simulação está correta
-- 3. EXECUTE PASSO 4 para verificar o resultado
-- 4. Este script NÃO consulta a Receita Federal (use o script Python para isso)
-- 5. Este script apenas aplica a regra de CrossDocking nos dados existentes

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================
