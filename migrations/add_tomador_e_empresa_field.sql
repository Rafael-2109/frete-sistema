-- ============================================================================
-- Script SQL para adicionar campo tomador_e_empresa
-- Banco: PostgreSQL (Render)
-- ============================================================================

-- 1. Adicionar coluna tomador_e_empresa
ALTER TABLE conhecimento_transporte
ADD COLUMN IF NOT EXISTS tomador_e_empresa BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_cte_tomador_empresa
ON conhecimento_transporte(tomador_e_empresa);

-- 3. Atualizar valores existentes baseado na lógica de negócio
-- Regra: tomador_e_empresa = TRUE se CNPJ do tomador começa com '61724241'

-- Atualizar para tomador = '0' ou '1' (Remetente)
UPDATE conhecimento_transporte
SET tomador_e_empresa = TRUE
WHERE (tomador = '0' OR tomador = '1')
AND cnpj_remetente IS NOT NULL
AND SUBSTRING(REPLACE(REPLACE(REPLACE(cnpj_remetente, '.', ''), '/', ''), '-', ''), 1, 8) = '61724241';

-- Atualizar para tomador = '2' (Expedidor)
UPDATE conhecimento_transporte
SET tomador_e_empresa = TRUE
WHERE tomador = '2'
AND cnpj_expedidor IS NOT NULL
AND SUBSTRING(REPLACE(REPLACE(REPLACE(cnpj_expedidor, '.', ''), '/', ''), '-', ''), 1, 8) = '61724241';

-- Atualizar para tomador = '3' ou '4' (Recebedor/Destinatário)
UPDATE conhecimento_transporte
SET tomador_e_empresa = TRUE
WHERE (tomador = '3' OR tomador = '4')
AND cnpj_destinatario IS NOT NULL
AND SUBSTRING(REPLACE(REPLACE(REPLACE(cnpj_destinatario, '.', ''), '/', ''), '-', ''), 1, 8) = '61724241';

-- 4. Verificar resultado
SELECT
    tomador_e_empresa,
    COUNT(*) as total
FROM conhecimento_transporte
GROUP BY tomador_e_empresa
ORDER BY tomador_e_empresa;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
