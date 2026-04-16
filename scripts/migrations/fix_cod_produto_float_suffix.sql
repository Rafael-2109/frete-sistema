-- ============================================================================
-- FIX: Remover sufixo ".0" de cod_produto em tabelas afetadas
-- ============================================================================
-- CAUSA: pd.read_excel() sem dtype=str le inteiros como float64.
--        str(4210155.0) -> "4210155.0" em vez de "4210155".
-- REGEX: '^[0-9]+\.0$' garante que so afeta codigos puramente numericos
--        com sufixo .0 (nao afeta "V1.0" ou outros padroes).
-- SEGURANCA: Idempotente — rodar varias vezes e seguro.
-- ============================================================================

-- 1. Diagnostico ANTES (rodar para ver o que sera corrigido)
DO $$
DECLARE
    v_count_palletizacao INTEGER;
    v_count_movimentacao INTEGER;
    v_count_movimentacao_raiz INTEGER;
    v_count_programacao INTEGER;
    v_count_recursos INTEGER;
    v_count_previsao INTEGER;
    v_count_custo INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count_palletizacao FROM cadastro_palletizacao WHERE cod_produto ~ '^\d+\.0$';
    SELECT COUNT(*) INTO v_count_movimentacao FROM movimentacao_estoque WHERE cod_produto ~ '^\d+\.0$';
    SELECT COUNT(*) INTO v_count_movimentacao_raiz FROM movimentacao_estoque WHERE cod_produto_raiz ~ '^\d+\.0$';
    SELECT COUNT(*) INTO v_count_programacao FROM programacao_producao WHERE cod_produto ~ '^\d+\.0$';
    SELECT COUNT(*) INTO v_count_recursos FROM recursos_producao WHERE cod_produto ~ '^\d+\.0$';
    SELECT COUNT(*) INTO v_count_previsao FROM previsao_demanda WHERE cod_produto ~ '^\d+\.0$';
    SELECT COUNT(*) INTO v_count_custo FROM custo_considerado WHERE cod_produto ~ '^\d+\.0$';

    RAISE NOTICE '=== DIAGNOSTICO cod_produto com sufixo .0 ===';
    RAISE NOTICE 'cadastro_palletizacao:   % registros', v_count_palletizacao;
    RAISE NOTICE 'movimentacao_estoque:    % registros (cod_produto)', v_count_movimentacao;
    RAISE NOTICE 'movimentacao_estoque:    % registros (cod_produto_raiz)', v_count_movimentacao_raiz;
    RAISE NOTICE 'programacao_producao:    % registros', v_count_programacao;
    RAISE NOTICE 'recursos_producao:       % registros', v_count_recursos;
    RAISE NOTICE 'previsao_demanda:        % registros', v_count_previsao;
    RAISE NOTICE 'custo_considerado:       % registros', v_count_custo;
    RAISE NOTICE 'TOTAL:                   % registros',
        v_count_palletizacao + v_count_movimentacao + v_count_movimentacao_raiz +
        v_count_programacao + v_count_recursos + v_count_previsao + v_count_custo;
END $$;

-- 2. Correcao: remover ".0" de cod_produto onde padrao e numerico + .0

-- cadastro_palletizacao (UNIQUE index em cod_produto — verificar conflito)
UPDATE cadastro_palletizacao
SET cod_produto = REGEXP_REPLACE(cod_produto, '\.0$', ''),
    updated_at = NOW()
WHERE cod_produto ~ '^\d+\.0$'
  AND NOT EXISTS (
    SELECT 1 FROM cadastro_palletizacao cp2
    WHERE cp2.cod_produto = REGEXP_REPLACE(cadastro_palletizacao.cod_produto, '\.0$', '')
      AND cp2.id != cadastro_palletizacao.id
  );

-- movimentacao_estoque — cod_produto
UPDATE movimentacao_estoque
SET cod_produto = REGEXP_REPLACE(cod_produto, '\.0$', ''),
    atualizado_em = NOW(),
    atualizado_por = 'migration_fix_float_suffix'
WHERE cod_produto ~ '^\d+\.0$';

-- movimentacao_estoque — cod_produto_raiz
UPDATE movimentacao_estoque
SET cod_produto_raiz = REGEXP_REPLACE(cod_produto_raiz, '\.0$', ''),
    atualizado_em = NOW(),
    atualizado_por = 'migration_fix_float_suffix'
WHERE cod_produto_raiz ~ '^\d+\.0$';

-- programacao_producao
UPDATE programacao_producao
SET cod_produto = REGEXP_REPLACE(cod_produto, '\.0$', '')
WHERE cod_produto ~ '^\d+\.0$';

-- recursos_producao
UPDATE recursos_producao
SET cod_produto = REGEXP_REPLACE(cod_produto, '\.0$', '')
WHERE cod_produto ~ '^\d+\.0$';

-- previsao_demanda
UPDATE previsao_demanda
SET cod_produto = REGEXP_REPLACE(cod_produto, '\.0$', '')
WHERE cod_produto ~ '^\d+\.0$';

-- custo_considerado
UPDATE custo_considerado
SET cod_produto = REGEXP_REPLACE(cod_produto, '\.0$', '')
WHERE cod_produto ~ '^\d+\.0$';

-- 3. Diagnostico DEPOIS (confirmar que zerou)
DO $$
DECLARE
    v_total INTEGER;
BEGIN
    SELECT (
        (SELECT COUNT(*) FROM cadastro_palletizacao WHERE cod_produto ~ '^\d+\.0$') +
        (SELECT COUNT(*) FROM movimentacao_estoque WHERE cod_produto ~ '^\d+\.0$') +
        (SELECT COUNT(*) FROM movimentacao_estoque WHERE cod_produto_raiz ~ '^\d+\.0$') +
        (SELECT COUNT(*) FROM programacao_producao WHERE cod_produto ~ '^\d+\.0$') +
        (SELECT COUNT(*) FROM recursos_producao WHERE cod_produto ~ '^\d+\.0$') +
        (SELECT COUNT(*) FROM previsao_demanda WHERE cod_produto ~ '^\d+\.0$') +
        (SELECT COUNT(*) FROM custo_considerado WHERE cod_produto ~ '^\d+\.0$')
    ) INTO v_total;

    IF v_total = 0 THEN
        RAISE NOTICE '=== SUCESSO: 0 registros com sufixo .0 restantes ===';
    ELSE
        RAISE WARNING '=== ATENCAO: % registros ainda com sufixo .0 (possivelmente conflito UNIQUE) ===', v_total;
    END IF;
END $$;
