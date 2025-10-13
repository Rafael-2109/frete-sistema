-- ============================================================================
-- Script SQL: Sincronização Retroativa de NFs FOB
-- ============================================================================
--
-- OBJETIVO:
--   1. Reativar NFs FOB que estão com ativo=False
--   2. Criar EntregaMonitorada para NFs FOB que não possuem monitoramento
--
-- ATENÇÃO: Este script MODIFICA e INSERE registros no banco
--          Certifique-se de que a modificação em app/utils/sincronizar_entregas.py
--          foi aplicada ANTES de executar este script!
--
-- Data: 13/10/2025
-- ============================================================================

-- ============================================================================
-- ETAPA 0: VERIFICAR E REATIVAR NFs FOB INATIVAS
-- ============================================================================
--
-- OBJETIVO: Algumas NFs FOB podem ter sido marcadas como ativo=False por engano.
--           Esta etapa verifica e reativa essas NFs.
--

-- 🔍 PASSO 1: LISTAR NFs FOB INATIVAS (para verificação)
-- ✅ Filtra apenas NFs a partir de 30/06/2025
SELECT
    rfi.numero_nf,
    rfi.nome_cliente,
    rfi.valor_total,
    rfi.data_fatura,
    rfi.incoterm,
    rfi.ativo,
    rfi.inativado_em,
    rfi.inativado_por
FROM relatorio_faturamento_importado rfi
WHERE rfi.incoterm ILIKE '%FOB%'
  AND rfi.ativo = FALSE
  AND rfi.data_fatura >= '2025-07-01'  -- ✅ Filtro de data adicionado
ORDER BY rfi.data_fatura DESC;

-- ⚠️ VERIFICAÇÃO: Execute o SELECT acima primeiro!
-- Se houver NFs FOB inativas e você quer reativá-las, execute o UPDATE abaixo:

-- 🔄 PASSO 2: REATIVAR NFs FOB a partir de 30/06/2025
-- ⚠️ IMPORTANTE: Apenas NFs com data_fatura >= 30/06/2025 serão reativadas
UPDATE relatorio_faturamento_importado
SET
    ativo = TRUE,
    inativado_em = NULL,
    inativado_por = NULL
WHERE incoterm ILIKE '%FOB%'
  AND ativo = FALSE
  AND data_fatura >= '2025-07-01';  -- ✅ Filtro de data: reativa apenas de 30/06/2025 em diante

-- 📊 PASSO 3: VERIFICAR quantas foram reativadas
SELECT
    COUNT(*) AS nfs_fob_reativadas,
    MIN(data_fatura) AS data_mais_antiga_reativada,
    MAX(data_fatura) AS data_mais_recente_reativada,
    SUM(valor_total) AS valor_total_reativado
FROM relatorio_faturamento_importado
WHERE incoterm ILIKE '%FOB%'
  AND ativo = TRUE
  AND data_fatura >= '2025-07-01';

-- ============================================================================
-- ETAPA 1: LISTAR NFs FOB SEM ENTREGA MONITORADA (para verificação)
-- Execute primeiro para ver quantas NFs serão afetadas
SELECT
    rfi.numero_nf,
    rfi.nome_cliente,
    rfi.valor_total,
    rfi.data_fatura,
    rfi.incoterm,
    rfi.municipio,
    rfi.estado
FROM relatorio_faturamento_importado rfi
WHERE rfi.incoterm ILIKE '%FOB%'
  AND rfi.ativo = TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM entregas_monitoradas em
      WHERE em.numero_nf = rfi.numero_nf
  )
ORDER BY rfi.data_fatura DESC;

-- ============================================================================
-- ETAPA 2: INSERIR EntregaMonitorada para NFs FOB
-- ============================================================================
--
-- Este INSERT cria EntregaMonitorada para cada NF FOB que:
-- 1. Está ativa no RelatorioFaturamentoImportado
-- 2. Ainda não possui EntregaMonitorada
-- 3. Possui EmbarqueItem (para pegar data_embarque)
--
-- CAMPOS PREENCHIDOS:
-- - Dados básicos da NF (cliente, valor, datas)
-- - data_embarque do Embarque
-- - data_hora_entrega_realizada = data_embarque (FOB entrega no CD)
-- - data_entrega_prevista = data_prevista_embarque
-- - entregue = TRUE (marcado como entregue automaticamente)
-- - status_finalizacao = 'FOB - Embarcado no CD'
--
-- ============================================================================

INSERT INTO entregas_monitoradas (
    numero_nf,
    cliente,
    cnpj_cliente,
    municipio,
    uf,
    vendedor,
    valor_nf,
    data_faturamento,
    data_embarque,
    data_entrega_prevista,
    data_hora_entrega_realizada,
    entregue,
    status_finalizacao,
    transportadora,
    separacao_lote_id,
    criado_em,
    criado_por
)
SELECT DISTINCT
    rfi.numero_nf,
    rfi.nome_cliente AS cliente,
    rfi.cnpj_cliente,
    rfi.municipio,
    rfi.estado AS uf,
    rfi.vendedor,
    rfi.valor_total AS valor_nf,
    rfi.data_fatura AS data_faturamento,
    e.data_embarque,
    -- ✅ CORREÇÃO: Usar data_prevista_embarque, com fallback para data_embarque
    COALESCE(e.data_prevista_embarque, e.data_embarque) AS data_entrega_prevista,
    -- ✅ Para FOB, data_hora_entrega_realizada = data_embarque (preenchimento automático)
    CASE
        WHEN e.data_embarque IS NOT NULL THEN e.data_embarque::timestamp
        ELSE NULL
    END AS data_hora_entrega_realizada,
    -- ✅ Marcar como entregue se tem data_embarque
    CASE
        WHEN e.data_embarque IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS entregue,
    -- ✅ Status de finalização: 'Entregue' se embarcado, NULL se não
    CASE
        WHEN e.data_embarque IS NOT NULL THEN 'Entregue'
        ELSE NULL
    END AS status_finalizacao,
    -- ✅ Transportadora (se houver)
    COALESCE(t.razao_social, '-') AS transportadora,
    -- ✅ separacao_lote_id do EmbarqueItem
    ei.separacao_lote_id,
    NOW() AS criado_em,
    'Sistema - Sincronização Automática' AS criado_por
FROM relatorio_faturamento_importado rfi
-- JOIN com EmbarqueItem para pegar dados do embarque
INNER JOIN embarque_itens ei ON ei.nota_fiscal = rfi.numero_nf
                             AND ei.status = 'ativo'
-- JOIN com Embarque para pegar datas
INNER JOIN embarques e ON e.id = ei.embarque_id
                       AND e.status = 'ativo'
-- JOIN opcional com Transportadora
LEFT JOIN transportadoras t ON t.id = e.transportadora_id
WHERE
    -- Filtros para NFs FOB
    rfi.incoterm ILIKE '%FOB%'
    AND rfi.ativo = TRUE
    -- Apenas NFs que NÃO têm EntregaMonitorada ainda
    AND NOT EXISTS (
        SELECT 1
        FROM entregas_monitoradas em
        WHERE em.numero_nf = rfi.numero_nf
    );

-- ============================================================================
-- ETAPA 3: VERIFICAÇÃO - Contar quantas foram criadas
-- ============================================================================

SELECT
    COUNT(*) AS total_entregas_fob_criadas
FROM entregas_monitoradas em
WHERE em.criado_por = 'Sistema - Sincronização Automática';

-- ============================================================================
-- ETAPA 4: LISTAR EntregaMonitorada FOB CRIADAS (para conferência)
-- ============================================================================

SELECT
    em.id,
    em.numero_nf,
    em.cliente,
    em.data_faturamento,
    em.data_embarque,
    em.data_hora_entrega_realizada,
    em.entregue,
    em.status_finalizacao,
    em.transportadora,
    em.separacao_lote_id
FROM entregas_monitoradas em
WHERE em.criado_por = 'Sistema - Sincronização Automática'
ORDER BY em.data_faturamento DESC;

-- ============================================================================
-- ETAPA 5: ESTATÍSTICAS FINAIS
-- ============================================================================

SELECT
    'Total NFs FOB ativas' AS descricao,
    COUNT(*) AS quantidade
FROM relatorio_faturamento_importado
WHERE incoterm ILIKE '%FOB%' AND ativo = TRUE

UNION ALL

SELECT
    'Total EntregaMonitorada FOB' AS descricao,
    COUNT(*) AS quantidade
FROM entregas_monitoradas em
JOIN relatorio_faturamento_importado rfi ON rfi.numero_nf = em.numero_nf
WHERE rfi.incoterm ILIKE '%FOB%'

UNION ALL

SELECT
    'NFs FOB sem EntregaMonitorada' AS descricao,
    COUNT(*) AS quantidade
FROM relatorio_faturamento_importado rfi
WHERE rfi.incoterm ILIKE '%FOB%'
  AND rfi.ativo = TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM entregas_monitoradas em
      WHERE em.numero_nf = rfi.numero_nf
  );

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
