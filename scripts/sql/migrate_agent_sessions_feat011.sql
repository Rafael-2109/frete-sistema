-- ============================================
-- MIGRAÇÃO: Expandir tabela agent_sessions
-- FEAT-011: Lista de Sessões
-- Para uso no Shell do Render ou psql
-- ============================================
--
-- INSTRUÇÕES:
-- 1. Se tabela NÃO existe: execute create_agent_sessions.sql
-- 2. Se tabela JÁ existe: execute ESTE script para adicionar novos campos
-- ============================================

-- Adiciona novos campos se não existem
DO $$
BEGIN
    -- title
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'agent_sessions' AND column_name = 'title'
    ) THEN
        ALTER TABLE agent_sessions ADD COLUMN title VARCHAR(200);
        RAISE NOTICE 'Coluna title adicionada';
    END IF;

    -- message_count
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'agent_sessions' AND column_name = 'message_count'
    ) THEN
        ALTER TABLE agent_sessions ADD COLUMN message_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Coluna message_count adicionada';
    END IF;

    -- total_cost_usd
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'agent_sessions' AND column_name = 'total_cost_usd'
    ) THEN
        ALTER TABLE agent_sessions ADD COLUMN total_cost_usd DECIMAL(10, 6) DEFAULT 0;
        RAISE NOTICE 'Coluna total_cost_usd adicionada';
    END IF;

    -- last_message
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'agent_sessions' AND column_name = 'last_message'
    ) THEN
        ALTER TABLE agent_sessions ADD COLUMN last_message TEXT;
        RAISE NOTICE 'Coluna last_message adicionada';
    END IF;

    -- model
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'agent_sessions' AND column_name = 'model'
    ) THEN
        ALTER TABLE agent_sessions ADD COLUMN model VARCHAR(100);
        RAISE NOTICE 'Coluna model adicionada';
    END IF;

    RAISE NOTICE '✅ Migração FEAT-011 concluída!';
END $$;

-- Verifica estrutura final
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agent_sessions'
ORDER BY ordinal_position;
