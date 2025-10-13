-- =========================================================================
-- CORREÇÃO DE DESSINCRONIA - Sincroniza PedidoVendaMotoItem com TituloAPagar
-- FONTE DA VERDADE: TituloAPagar.status
-- =========================================================================

-- ⚠️ ATENÇÃO: Execute PRIMEIRO o SELECT para verificar o que será alterado!

-- 1. PREVIEW: Ver o que será alterado
SELECT
    'PREVIEW_CORRECOES' as secao,
    i.id as item_id,
    i.pedido_id,
    i.numero_chassi,
    i.montagem_paga as estado_atual,
    CASE
        WHEN t.status = 'PAGO' THEN true
        ELSE false
    END as estado_correto,
    t.id as titulo_id,
    t.status as titulo_status,
    t.valor_saldo as titulo_saldo,
    CASE
        WHEN i.montagem_paga = true AND t.status != 'PAGO' THEN 'Corrigir: TRUE → FALSE'
        WHEN i.montagem_paga = false AND t.status = 'PAGO' THEN 'Corrigir: FALSE → TRUE'
    END as acao
FROM pedido_venda_moto_item i
INNER JOIN titulo_a_pagar t ON (
    t.pedido_id = i.pedido_id
    AND t.numero_chassi = i.numero_chassi
    AND t.tipo = 'MONTAGEM'
)
WHERE i.montagem_contratada = true
AND (
    (i.montagem_paga = true AND t.status != 'PAGO')
    OR (i.montagem_paga = false AND t.status = 'PAGO')
)
ORDER BY i.id;

-- 2. CORREÇÃO: Atualizar PedidoVendaMotoItem baseado em TituloAPagar
-- ⚠️ EXECUTAR APENAS APÓS VERIFICAR O SELECT ACIMA!

-- Corrigir itens que estão marcados como PAGO mas título NÃO está PAGO
UPDATE pedido_venda_moto_item i
SET montagem_paga = false,
    atualizado_em = NOW(),
    atualizado_por = 'SCRIPT_CORRECAO'
FROM titulo_a_pagar t
WHERE i.pedido_id = t.pedido_id
AND i.numero_chassi = t.numero_chassi
AND t.tipo = 'MONTAGEM'
AND i.montagem_contratada = true
AND i.montagem_paga = true
AND t.status != 'PAGO';

-- Corrigir itens que estão marcados como NÃO PAGO mas título está PAGO
UPDATE pedido_venda_moto_item i
SET montagem_paga = true,
    atualizado_em = NOW(),
    atualizado_por = 'SCRIPT_CORRECAO'
FROM titulo_a_pagar t
WHERE i.pedido_id = t.pedido_id
AND i.numero_chassi = t.numero_chassi
AND t.tipo = 'MONTAGEM'
AND i.montagem_contratada = true
AND i.montagem_paga = false
AND t.status = 'PAGO';

-- 3. VERIFICAR RESULTADO
SELECT
    'RESULTADO' as secao,
    COUNT(*) as total_itens,
    SUM(CASE WHEN i.montagem_paga = true THEN 1 ELSE 0 END) as itens_pagos,
    SUM(CASE WHEN t.status = 'PAGO' THEN 1 ELSE 0 END) as titulos_pagos,
    SUM(CASE
        WHEN (i.montagem_paga = true AND t.status = 'PAGO')
            OR (i.montagem_paga = false AND t.status != 'PAGO')
        THEN 1 ELSE 0
    END) as sincronizados,
    SUM(CASE
        WHEN (i.montagem_paga = true AND t.status != 'PAGO')
            OR (i.montagem_paga = false AND t.status = 'PAGO')
        THEN 1 ELSE 0
    END) as dessincronizados
FROM pedido_venda_moto_item i
INNER JOIN titulo_a_pagar t ON (
    t.pedido_id = i.pedido_id
    AND t.numero_chassi = i.numero_chassi
    AND t.tipo = 'MONTAGEM'
)
WHERE i.montagem_contratada = true;
