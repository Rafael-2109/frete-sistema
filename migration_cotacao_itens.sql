-- =====================================================
-- Migration: Adicionar separacao_lote_id em cotacao_itens
-- Data: 2025-09-03
-- Descrição: Adiciona campo separacao_lote_id para substituir pedido_id
-- =====================================================

-- 1. Primeiro, renomeia a coluna pedido_id atual para pedido_id_old (se existir)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'cotacao_itens' 
               AND column_name = 'pedido_id'
               AND column_name != 'pedido_id_old') THEN
        ALTER TABLE cotacao_itens RENAME COLUMN pedido_id TO pedido_id_old;
        RAISE NOTICE 'Coluna pedido_id renomeada para pedido_id_old';
    ELSE
        RAISE NOTICE 'Coluna pedido_id não existe ou já foi renomeada';
    END IF;
END $$;

-- 2. Adiciona a nova coluna separacao_lote_id se não existir
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cotacao_itens' 
                   AND column_name = 'separacao_lote_id') THEN
        ALTER TABLE cotacao_itens 
        ADD COLUMN separacao_lote_id VARCHAR(50);
        
        RAISE NOTICE 'Coluna separacao_lote_id adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna separacao_lote_id já existe';
    END IF;
END $$;

-- 3. Adiciona pedido_id_old se não existir (para backup)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cotacao_itens' 
                   AND column_name = 'pedido_id_old') THEN
        ALTER TABLE cotacao_itens 
        ADD COLUMN pedido_id_old INTEGER;
        
        RAISE NOTICE 'Coluna pedido_id_old adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna pedido_id_old já existe';
    END IF;
END $$;

-- 4. Cria índice para separacao_lote_id para melhor performance
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes 
                   WHERE tablename = 'cotacao_itens' 
                   AND indexname = 'ix_cotacao_itens_separacao_lote_id') THEN
        CREATE INDEX ix_cotacao_itens_separacao_lote_id 
        ON cotacao_itens(separacao_lote_id);
        
        RAISE NOTICE 'Índice ix_cotacao_itens_separacao_lote_id criado';
    ELSE
        RAISE NOTICE 'Índice ix_cotacao_itens_separacao_lote_id já existe';
    END IF;
END $$;

-- 5. OPCIONAL: Popular separacao_lote_id baseado em pedido_id_old
-- Este passo tenta encontrar os separacao_lote_id correspondentes
-- baseado nos pedidos existentes
DO $$ 
BEGIN
    -- Atualiza cotacao_itens com separacao_lote_id dos pedidos correspondentes
    -- Usa a VIEW pedidos que tem a relação com separacao_lote_id
    UPDATE cotacao_itens ci
    SET separacao_lote_id = p.separacao_lote_id
    FROM pedidos p
    WHERE ci.pedido_id_old IS NOT NULL
    AND ci.separacao_lote_id IS NULL
    AND p.num_pedido IN (
        -- Tenta encontrar o pedido pelo ID antigo se houver alguma relação
        SELECT DISTINCT s.num_pedido 
        FROM separacao s 
        WHERE s.num_pedido IS NOT NULL
    );
    
    RAISE NOTICE 'Tentativa de popular separacao_lote_id concluída. Linhas afetadas: %', ROW_COUNT();
END $$;

-- 6. Verifica o resultado da migration
SELECT 
    'RESUMO DA MIGRATION' as info,
    COUNT(*) as total_registros,
    COUNT(separacao_lote_id) as registros_com_lote_id,
    COUNT(pedido_id_old) as registros_com_pedido_old,
    COUNT(*) - COUNT(separacao_lote_id) as registros_sem_lote_id
FROM cotacao_itens;

-- 7. Lista alguns exemplos de registros para verificação
SELECT 
    id,
    cotacao_id,
    pedido_id_old,
    separacao_lote_id,
    cnpj_cliente,
    cliente
FROM cotacao_itens
LIMIT 10;

-- =====================================================
-- ROLLBACK (caso precise reverter)
-- =====================================================
-- Para reverter, execute:
-- ALTER TABLE cotacao_itens DROP COLUMN IF EXISTS separacao_lote_id;
-- ALTER TABLE cotacao_itens RENAME COLUMN pedido_id_old TO pedido_id;
-- DROP INDEX IF EXISTS ix_cotacao_itens_separacao_lote_id;