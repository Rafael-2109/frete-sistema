-- =====================================================
-- MIGRAÇÃO PARA SISTEMA ASSÍNCRONO COM REDIS QUEUE
-- Para aplicar no Render.com Database Shell
-- Data: 27/08/2024
-- =====================================================

-- INSTRUÇÕES DE USO NO RENDER:
-- 1. Acesse o Dashboard do Render
-- 2. Vá para seu Database PostgreSQL
-- 3. Clique em "PSQL Command"
-- 4. Copie e cole este script inteiro
-- 5. Execute pressionando Enter

-- =====================================================
-- 1. ADICIONAR CAMPO job_id NA TABELA portal_integracoes
-- =====================================================

-- Verificar se a tabela existe
DO $$ 
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'portal_integracoes'
    ) THEN
        RAISE NOTICE 'Tabela portal_integracoes encontrada. Adicionando campo job_id...';
        
        -- Adicionar coluna job_id se não existir
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'portal_integracoes' 
            AND column_name = 'job_id'
        ) THEN
            ALTER TABLE portal_integracoes 
            ADD COLUMN job_id VARCHAR(100);
            
            RAISE NOTICE '✅ Campo job_id adicionado com sucesso!';
        ELSE
            RAISE NOTICE '⚠️ Campo job_id já existe, pulando criação.';
        END IF;
        
        -- Criar índice para busca rápida
        IF NOT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'portal_integracoes' 
            AND indexname = 'idx_portal_integracoes_job_id'
        ) THEN
            CREATE INDEX idx_portal_integracoes_job_id 
            ON portal_integracoes(job_id);
            
            RAISE NOTICE '✅ Índice idx_portal_integracoes_job_id criado!';
        ELSE
            RAISE NOTICE '⚠️ Índice já existe, pulando criação.';
        END IF;
        
        -- Adicionar comentário explicativo
        COMMENT ON COLUMN portal_integracoes.job_id IS 
        'ID do job no Redis Queue para processamento assíncrono de agendamentos';
        
    ELSE
        RAISE NOTICE '❌ Tabela portal_integracoes não encontrada!';
        RAISE NOTICE 'Execute primeiro as migrações do Flask-Migrate.';
    END IF;
END $$;

-- =====================================================
-- 2. ADICIONAR NOVO STATUS 'enfileirado' (se necessário)
-- =====================================================

-- Atualizar registros com status NULL para 'aguardando'
UPDATE portal_integracoes 
SET status = 'aguardando' 
WHERE status IS NULL;

-- =====================================================
-- 3. ESTATÍSTICAS E VERIFICAÇÃO
-- =====================================================

-- Mostrar estatísticas da tabela
SELECT 
    '📊 ESTATÍSTICAS DA TABELA portal_integracoes:' as info
UNION ALL
SELECT 
    '   Total de registros: ' || COUNT(*)::text
FROM portal_integracoes
UNION ALL
SELECT 
    '   Registros com job_id: ' || COUNT(job_id)::text
FROM portal_integracoes
WHERE job_id IS NOT NULL
UNION ALL
SELECT 
    '   Status aguardando: ' || COUNT(*)::text
FROM portal_integracoes
WHERE status = 'aguardando'
UNION ALL
SELECT 
    '   Status enfileirado: ' || COUNT(*)::text
FROM portal_integracoes
WHERE status = 'enfileirado'
UNION ALL
SELECT 
    '   Status processando: ' || COUNT(*)::text
FROM portal_integracoes
WHERE status = 'processando'
UNION ALL
SELECT 
    '   Status erro: ' || COUNT(*)::text
FROM portal_integracoes
WHERE status = 'erro';

-- =====================================================
-- 4. VERIFICAR ESTRUTURA FINAL
-- =====================================================

SELECT 
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'portal_integracoes'
AND column_name IN ('job_id', 'status', 'protocolo')
ORDER BY ordinal_position;

-- =====================================================
-- RESULTADO ESPERADO:
-- =====================================================
-- column_name | data_type         | max_length | nullable
-- ------------|-------------------|------------|----------
-- protocolo   | character varying | 100        | YES
-- status      | character varying | 50         | YES  
-- job_id      | character varying | 100        | YES

-- =====================================================
-- FIM DA MIGRAÇÃO
-- =====================================================

-- Mensagem final
SELECT '
✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!
===================================
O campo job_id foi adicionado à tabela portal_integracoes.
O sistema está pronto para usar Redis Queue.

PRÓXIMOS PASSOS:
1. Configure a variável REDIS_URL no Render
2. Faça deploy da aplicação com as novas dependências
3. Inicie o worker com: python worker_atacadao.py

' AS resultado_final;