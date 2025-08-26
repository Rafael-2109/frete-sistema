-- Migração para adicionar campo job_id na tabela portal_integracoes
-- Para suporte ao Redis Queue

-- Adicionar coluna job_id
ALTER TABLE portal_integracoes 
ADD COLUMN IF NOT EXISTS job_id VARCHAR(100);

-- Criar índice para busca rápida por job_id
CREATE INDEX IF NOT EXISTS idx_portal_integracoes_job_id 
ON portal_integracoes(job_id);

-- Adicionar comentário explicativo
COMMENT ON COLUMN portal_integracoes.job_id IS 'ID do job no Redis Queue para processamento assíncrono';