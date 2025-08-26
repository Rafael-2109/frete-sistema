-- =====================================================
-- MIGRAÇÃO LOCAL PARA SISTEMA ASSÍNCRONO COM REDIS QUEUE
-- Para SQLite (desenvolvimento local)
-- =====================================================

-- SQLite não suporta ALTER TABLE ADD COLUMN IF NOT EXISTS
-- Então vamos fazer de forma mais simples

-- 1. Adicionar campo job_id na tabela portal_integracoes
-- No SQLite, se a coluna já existir, vai dar erro (ignorar)
ALTER TABLE portal_integracoes ADD COLUMN job_id VARCHAR(100);

-- 2. Criar índice para busca rápida
CREATE INDEX IF NOT EXISTS idx_portal_integracoes_job_id ON portal_integracoes(job_id);

-- 3. Verificar estrutura
SELECT sql FROM sqlite_master WHERE name = 'portal_integracoes';

-- 4. Estatísticas
SELECT 'Total de registros: ' || COUNT(*) FROM portal_integracoes
UNION ALL
SELECT 'Registros com job_id: ' || COUNT(job_id) FROM portal_integracoes WHERE job_id IS NOT NULL
UNION ALL
SELECT 'Status aguardando: ' || COUNT(*) FROM portal_integracoes WHERE status = 'aguardando'
UNION ALL
SELECT 'Status enfileirado: ' || COUNT(*) FROM portal_integracoes WHERE status = 'enfileirado'
UNION ALL
SELECT 'Status erro: ' || COUNT(*) FROM portal_integracoes WHERE status = 'erro';

-- Mensagem final
SELECT '
✅ MIGRAÇÃO LOCAL CONCLUÍDA!
============================
Campo job_id adicionado à tabela portal_integracoes.
Sistema pronto para usar Redis Queue localmente.

PRÓXIMOS PASSOS:
1. Iniciar Redis: sudo service redis start (WSL)
2. Iniciar Worker: python worker_atacadao.py
3. Iniciar App: python app.py
' AS resultado;