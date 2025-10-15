-- ============================================================
-- VERIFICAÇÃO DE TABELAS - CARGA INICIAL MOTOCHEFE
-- Data: 14/10/2025
--
-- OBJETIVO:
-- Verificar se todas as tabelas necessárias para carga inicial existem
--
-- EXECUÇÃO NO RENDER:
-- 1. Acesse: Shell do PostgreSQL no Render
-- 2. Cole este SQL completo
-- 3. Verifique a saída
-- ============================================================

-- Verificar tabelas necessárias
SELECT
    'VERIFICAÇÃO DE TABELAS - CARGA INICIAL MOTOCHEFE' AS titulo;

SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'equipe_vendas_moto')
        THEN '✅ equipe_vendas_moto'
        ELSE '❌ equipe_vendas_moto - FALTANDO'
    END AS status
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'transportadora_moto')
        THEN '✅ transportadora_moto'
        ELSE '❌ transportadora_moto - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'empresa_venda_moto')
        THEN '✅ empresa_venda_moto'
        ELSE '❌ empresa_venda_moto - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cross_docking')
        THEN '✅ cross_docking'
        ELSE '❌ cross_docking - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'custos_operacionais')
        THEN '✅ custos_operacionais'
        ELSE '❌ custos_operacionais - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tabela_preco_equipe')
        THEN '✅ tabela_preco_equipe'
        ELSE '❌ tabela_preco_equipe - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tabela_preco_crossdocking')
        THEN '✅ tabela_preco_crossdocking'
        ELSE '❌ tabela_preco_crossdocking - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vendedor_moto')
        THEN '✅ vendedor_moto'
        ELSE '❌ vendedor_moto - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'modelo_moto')
        THEN '✅ modelo_moto'
        ELSE '❌ modelo_moto - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cliente_moto')
        THEN '✅ cliente_moto'
        ELSE '❌ cliente_moto - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'moto')
        THEN '✅ moto'
        ELSE '❌ moto - FALTANDO'
    END;

-- Verificar campos críticos
SELECT
    '============================================================' AS separador
UNION ALL
SELECT 'VERIFICAÇÃO DE CAMPOS CRÍTICOS (MIGRATIONS)'
UNION ALL
SELECT '============================================================';

SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'cliente_moto' AND column_name = 'vendedor_id'
        )
        THEN '✅ cliente_moto.vendedor_id'
        ELSE '❌ cliente_moto.vendedor_id - FALTANDO'
    END AS status
UNION ALL
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'cliente_moto' AND column_name = 'crossdocking'
        )
        THEN '✅ cliente_moto.crossdocking'
        ELSE '❌ cliente_moto.crossdocking - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'equipe_vendas_moto' AND column_name = 'permitir_prazo'
        )
        THEN '✅ equipe_vendas_moto.permitir_prazo'
        ELSE '❌ equipe_vendas_moto.permitir_prazo - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'equipe_vendas_moto' AND column_name = 'permitir_parcelamento'
        )
        THEN '✅ equipe_vendas_moto.permitir_parcelamento'
        ELSE '❌ equipe_vendas_moto.permitir_parcelamento - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'equipe_vendas_moto' AND column_name = 'custo_movimentacao'
        )
        THEN '✅ equipe_vendas_moto.custo_movimentacao'
        ELSE '❌ equipe_vendas_moto.custo_movimentacao - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'equipe_vendas_moto' AND column_name = 'tipo_precificacao'
        )
        THEN '✅ equipe_vendas_moto.tipo_precificacao'
        ELSE '❌ equipe_vendas_moto.tipo_precificacao - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'moto' AND column_name = 'empresa_pagadora_id'
        )
        THEN '✅ moto.empresa_pagadora_id'
        ELSE '❌ moto.empresa_pagadora_id - FALTANDO'
    END
UNION ALL
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'moto' AND column_name = 'status_pagamento_custo'
        )
        THEN '✅ moto.status_pagamento_custo'
        ELSE '❌ moto.status_pagamento_custo - FALTANDO'
    END;

-- Resultado final
SELECT
    '============================================================' AS separador
UNION ALL
SELECT 'RESULTADO FINAL'
UNION ALL
SELECT '============================================================';

SELECT
    CASE
        WHEN (
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name IN (
                'equipe_vendas_moto', 'transportadora_moto', 'empresa_venda_moto',
                'cross_docking', 'custos_operacionais', 'tabela_preco_equipe',
                'tabela_preco_crossdocking', 'vendedor_moto', 'modelo_moto',
                'cliente_moto', 'moto'
            )
        ) = 11
        THEN '✅ SISTEMA PRONTO PARA CARGA INICIAL!'
        ELSE '❌ EXECUTE OS SCRIPTS DE CRIAÇÃO DE TABELAS'
    END AS resultado_final;

-- Instruções finais
SELECT
    '============================================================' AS separador
UNION ALL
SELECT 'PRÓXIMOS PASSOS'
UNION ALL
SELECT '============================================================'
UNION ALL
SELECT '1. Se tabelas faltando: Execute create_tables.sql'
UNION ALL
SELECT '2. Se campos faltando: Execute migrations pendentes'
UNION ALL
SELECT '3. Acesse: /motochefe/carga-inicial'
UNION ALL
SELECT '4. Baixe templates e importe dados'
UNION ALL
SELECT '============================================================';
