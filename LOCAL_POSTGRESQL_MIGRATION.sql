-- =====================================================
-- MIGRAÇÃO LOCAL PARA POSTGRESQL
-- Sistema Assíncrono com Redis Queue
-- =====================================================

-- 1. Adicionar campo job_id se não existir
DO $$ 
BEGIN
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
END $$;

-- 2. Criar índice para busca rápida
CREATE INDEX IF NOT EXISTS idx_portal_integracoes_job_id 
ON portal_integracoes(job_id);

-- 3. Adicionar comentário explicativo
COMMENT ON COLUMN portal_integracoes.job_id IS 
'ID do job no Redis Queue para processamento assíncrono';

-- 4. Estatísticas
SELECT '📊 ESTATÍSTICAS DA TABELA portal_integracoes:' as info
UNION ALL
SELECT '   Total de registros: ' || COUNT(*)::text FROM portal_integracoes
UNION ALL
SELECT '   Registros com job_id: ' || COUNT(job_id)::text FROM portal_integracoes WHERE job_id IS NOT NULL
UNION ALL
SELECT '   Status aguardando: ' || COUNT(*)::text FROM portal_integracoes WHERE status = 'aguardando'
UNION ALL
SELECT '   Status enfileirado: ' || COUNT(*)::text FROM portal_integracoes WHERE status = 'enfileirado'
UNION ALL
SELECT '   Status erro: ' || COUNT(*)::text FROM portal_integracoes WHERE status = 'erro';

-- 5. Verificar estrutura final
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

-- Mensagem final
SELECT '
✅ MIGRAÇÃO LOCAL CONCLUÍDA COM SUCESSO!
=========================================
Campo job_id adicionado à tabela portal_integracoes.
Sistema pronto para usar Redis Queue.

PRÓXIMOS PASSOS:
1. No WSL: sudo service redis start
2. Terminal 1: python worker_atacadao.py
3. Terminal 2: python app.py
4. Testar agendamento assíncrono
' AS resultado;