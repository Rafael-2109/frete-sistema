-- =========================================================================
-- DIAGNÓSTICO DE MONTAGENS - Investigar dessincronia
-- =========================================================================

-- 1. VERIFICAR ITEM ID 26 ESPECIFICAMENTE
SELECT
    'ITEM ID 26' as secao,
    i.id as item_id,
    i.pedido_id,
    i.numero_chassi,
    i.montagem_contratada,
    i.montagem_paga as item_montagem_paga,
    i.valor_montagem as item_valor_montagem,
    i.fornecedor_montagem,
    t.id as titulo_id,
    t.status as titulo_status,
    t.valor_original as titulo_valor_original,
    t.valor_pago as titulo_valor_pago,
    t.valor_saldo as titulo_valor_saldo,
    t.data_criacao as titulo_data_criacao,
    t.data_liberacao as titulo_data_liberacao,
    t.data_pagamento as titulo_data_pagamento,
    CASE
        WHEN i.montagem_paga = true AND t.status IN ('ABERTO', 'PARCIAL') THEN '⚠️ DESSINCRONIA: Item pago mas Titulo aberto'
        WHEN i.montagem_paga = false AND t.status = 'PAGO' THEN '⚠️ DESSINCRONIA: Item não pago mas Titulo pago'
        WHEN t.id IS NULL THEN '❌ Titulo não encontrado'
        ELSE '✅ Sincronizado'
    END as diagnostico
FROM pedido_venda_moto_item i
LEFT JOIN titulo_a_pagar t ON (
    t.pedido_id = i.pedido_id
    AND t.numero_chassi = i.numero_chassi
    AND t.tipo = 'MONTAGEM'
)
WHERE i.id = 26;

-- 2. LISTAR TODAS AS DESSINCRONIAS
SELECT
    'DESSINCRONIAS' as secao,
    i.id as item_id,
    i.pedido_id,
    i.numero_chassi,
    i.montagem_paga as item_paga,
    t.id as titulo_id,
    t.status as titulo_status,
    t.valor_saldo,
    CASE
        WHEN t.id IS NULL THEN 'SEM_TITULO'
        WHEN i.montagem_paga = true AND t.status IN ('ABERTO', 'PARCIAL') THEN 'ITEM_PAGO_TITULO_ABERTO'
        WHEN i.montagem_paga = false AND t.status = 'PAGO' THEN 'ITEM_NAO_PAGO_TITULO_PAGO'
    END as tipo_problema
FROM pedido_venda_moto_item i
LEFT JOIN titulo_a_pagar t ON (
    t.pedido_id = i.pedido_id
    AND t.numero_chassi = i.numero_chassi
    AND t.tipo = 'MONTAGEM'
)
WHERE i.montagem_contratada = true
AND (
    t.id IS NULL
    OR (i.montagem_paga = true AND t.status IN ('ABERTO', 'PARCIAL'))
    OR (i.montagem_paga = false AND t.status = 'PAGO')
)
ORDER BY i.id;

-- 3. TÍTULOS VISÍVEIS EM CONTAS A PAGAR (com status do item)
SELECT
    'TITULOS_VISIVEIS_CONTAS_A_PAGAR' as secao,
    t.id as titulo_id,
    t.pedido_id,
    t.numero_chassi,
    t.status as titulo_status,
    t.valor_saldo as titulo_saldo,
    i.id as item_id,
    i.montagem_paga as item_paga,
    i.montagem_contratada as item_contratada,
    CASE
        WHEN i.montagem_paga = true THEN '⚠️ Item já pago (vai dar erro)'
        WHEN i.id IS NULL THEN '❌ Item não encontrado'
        ELSE '✅ OK'
    END as status_validacao
FROM titulo_a_pagar t
LEFT JOIN pedido_venda_moto_item i ON (
    i.pedido_id = t.pedido_id
    AND i.numero_chassi = t.numero_chassi
)
WHERE t.tipo = 'MONTAGEM'
AND t.status IN ('ABERTO', 'PARCIAL')
ORDER BY t.id
LIMIT 20;

-- 4. ESTATÍSTICAS GERAIS
SELECT
    'ESTATISTICAS' as secao,
    COUNT(*) as total_itens_montagem,
    SUM(CASE WHEN montagem_paga = true THEN 1 ELSE 0 END) as itens_pagos,
    SUM(CASE WHEN montagem_paga = false THEN 1 ELSE 0 END) as itens_nao_pagos
FROM pedido_venda_moto_item
WHERE montagem_contratada = true;

SELECT
    'ESTATISTICAS_TITULOS' as secao,
    COUNT(*) as total_titulos_montagem,
    SUM(CASE WHEN status = 'PAGO' THEN 1 ELSE 0 END) as titulos_pagos,
    SUM(CASE WHEN status = 'ABERTO' THEN 1 ELSE 0 END) as titulos_abertos,
    SUM(CASE WHEN status = 'PARCIAL' THEN 1 ELSE 0 END) as titulos_parciais,
    SUM(CASE WHEN status = 'PENDENTE' THEN 1 ELSE 0 END) as titulos_pendentes
FROM titulo_a_pagar
WHERE tipo = 'MONTAGEM';
