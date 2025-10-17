-- ============================================================================
-- Script SQL para Limpeza de SaldoStandby no Shell do Render
-- ============================================================================
--
-- OBJETIVO:
-- Excluir registros de SaldoStandby que:
-- 1. Têm qtd_saldo = 0 ou NULL (zerados)
-- 2. Não existem mais na CarteiraPrincipal (órfãos)
-- 3. Existem na CarteiraPrincipal mas com qtd_saldo_produto_pedido = 0 (zerados)
--
-- Data de Criação: 2025-01-29
-- Autor: Sistema de Fretes
-- ============================================================================

-- IMPORTANTE: Executar no Shell do Render PostgreSQL
-- Comando: \connect <nome_do_banco>

BEGIN;

-- ============================================================================
-- ETAPA 1: EXCLUIR REGISTROS COM QTD_SALDO = 0 OU NULL
-- ============================================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'ETAPA 1: Excluindo registros com qtd_saldo = 0 ou NULL...';
    RAISE NOTICE '=================================================================';

    -- Contar registros zerados
    SELECT COUNT(*) INTO v_count
    FROM saldo_standby
    WHERE qtd_saldo = 0 OR qtd_saldo IS NULL;

    RAISE NOTICE 'Registros zerados encontrados: %', v_count;

    -- Excluir registros zerados
    DELETE FROM saldo_standby
    WHERE qtd_saldo = 0 OR qtd_saldo IS NULL;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RAISE NOTICE '✅ Registros zerados excluídos: %', v_count;
END $$;


-- ============================================================================
-- ETAPA 2: EXCLUIR ÓRFÃOS (não existem na CarteiraPrincipal)
-- ============================================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'ETAPA 2: Excluindo órfãos (não existem na carteira)...';
    RAISE NOTICE '=================================================================';

    -- Contar órfãos
    SELECT COUNT(*) INTO v_count
    FROM saldo_standby ss
    WHERE NOT EXISTS (
        SELECT 1
        FROM carteira_principal cp
        WHERE cp.num_pedido = ss.num_pedido
          AND cp.cod_produto = ss.cod_produto
    );

    RAISE NOTICE 'Órfãos encontrados: %', v_count;

    -- Excluir órfãos
    DELETE FROM saldo_standby ss
    WHERE NOT EXISTS (
        SELECT 1
        FROM carteira_principal cp
        WHERE cp.num_pedido = ss.num_pedido
          AND cp.cod_produto = ss.cod_produto
    );

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RAISE NOTICE '✅ Órfãos excluídos: %', v_count;
END $$;


-- ============================================================================
-- ETAPA 3: EXCLUIR ZERADOS NA CARTEIRA (qtd_saldo_produto_pedido = 0)
-- ============================================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'ETAPA 3: Excluindo itens zerados na carteira...';
    RAISE NOTICE '=================================================================';

    -- Contar zerados na carteira
    SELECT COUNT(*) INTO v_count
    FROM saldo_standby ss
    INNER JOIN carteira_principal cp
        ON cp.num_pedido = ss.num_pedido
       AND cp.cod_produto = ss.cod_produto
    WHERE cp.qtd_saldo_produto_pedido = 0
       OR cp.qtd_saldo_produto_pedido IS NULL;

    RAISE NOTICE 'Itens zerados na carteira encontrados: %', v_count;

    -- Excluir zerados na carteira
    DELETE FROM saldo_standby ss
    WHERE EXISTS (
        SELECT 1
        FROM carteira_principal cp
        WHERE cp.num_pedido = ss.num_pedido
          AND cp.cod_produto = ss.cod_produto
          AND (cp.qtd_saldo_produto_pedido = 0 OR cp.qtd_saldo_produto_pedido IS NULL)
    );

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RAISE NOTICE '✅ Itens zerados na carteira excluídos: %', v_count;
END $$;


-- ============================================================================
-- ESTATÍSTICAS FINAIS
-- ============================================================================
DO $$
DECLARE
    v_total_restante INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'ESTATÍSTICAS FINAIS';
    RAISE NOTICE '=================================================================';

    -- Contar registros restantes
    SELECT COUNT(*) INTO v_total_restante
    FROM saldo_standby;

    RAISE NOTICE '📦 Total de registros restantes em SaldoStandby: %', v_total_restante;
    RAISE NOTICE '';
    RAISE NOTICE '✅ LIMPEZA CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '=================================================================';
END $$;

-- Confirmar transação
COMMIT;

-- ============================================================================
-- VERIFICAÇÃO FINAL (OPCIONAL - NÃO MODIFICA DADOS)
-- ============================================================================
-- Descomentar as queries abaixo para verificar os dados restantes:

-- Ver pedidos restantes em standby:
-- SELECT num_pedido, COUNT(*) as total_itens, SUM(qtd_saldo) as qtd_total
-- FROM saldo_standby
-- GROUP BY num_pedido
-- ORDER BY qtd_total DESC
-- LIMIT 20;

-- Ver status dos standbys:
-- SELECT status_standby, tipo_standby, COUNT(*) as total
-- FROM saldo_standby
-- GROUP BY status_standby, tipo_standby
-- ORDER BY total DESC;
