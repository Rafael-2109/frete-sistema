-- =====================================================
-- SQL PARA RENDER (PostgreSQL Production)
-- Adicionar campo modelo_rejeitado na tabela moto
-- =====================================================
-- Data: 2025-10-05
-- Autor: Sistema MotoChefe
-- Descrição: Adiciona suporte para motos rejeitadas (modelo não encontrado na importação)
-- =====================================================

-- 1. Verificar se a coluna já existe (executar primeiro para conferir)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name = 'modelo_rejeitado';

-- Se retornar vazio, a coluna não existe e pode prosseguir
-- Se retornar dados, a coluna já existe e NÃO precisa executar o resto

-- =====================================================
-- 2. ADICIONAR COLUNA modelo_rejeitado
-- =====================================================
ALTER TABLE moto
ADD COLUMN modelo_rejeitado VARCHAR(100) NULL;

-- Descrição do campo:
-- - Armazena o nome do modelo que NÃO foi encontrado durante a importação
-- - Usado apenas quando ativo=False (moto rejeitada)
-- - Permite identificar qual modelo precisa ser cadastrado

COMMENT ON COLUMN moto.modelo_rejeitado IS 'Nome do modelo não encontrado na importação (quando ativo=False)';

-- =====================================================
-- 3. CRIAR ÍNDICE PARA PERFORMANCE
-- =====================================================
-- Índice parcial: só indexa linhas com modelo_rejeitado preenchido
CREATE INDEX IF NOT EXISTS idx_moto_modelo_rejeitado
ON moto(modelo_rejeitado)
WHERE modelo_rejeitado IS NOT NULL;

-- Índice composto para busca de motos inativas por modelo
CREATE INDEX IF NOT EXISTS idx_moto_ativo_modelo_rejeitado
ON moto(ativo, modelo_rejeitado)
WHERE ativo = FALSE;

-- =====================================================
-- 4. VALIDAR ALTERAÇÕES
-- =====================================================
-- Verificar se a coluna foi criada com sucesso
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name = 'modelo_rejeitado';

-- Verificar índices criados
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'moto'
AND indexname LIKE '%modelo_rejeitado%';

-- =====================================================
-- 5. ESTATÍSTICAS (OPCIONAL - para conferir dados)
-- =====================================================
-- Ver quantas motos estão inativas atualmente
SELECT
    COUNT(*) as total_motos_inativas,
    COUNT(DISTINCT modelo_rejeitado) as modelos_diferentes_rejeitados
FROM moto
WHERE ativo = FALSE;

-- Ver lista de modelos rejeitados (se houver motos inativas)
SELECT
    modelo_rejeitado,
    COUNT(*) as quantidade_motos
FROM moto
WHERE ativo = FALSE
AND modelo_rejeitado IS NOT NULL
GROUP BY modelo_rejeitado
ORDER BY quantidade_motos DESC;

-- =====================================================
-- ROLLBACK (caso necessário desfazer)
-- =====================================================
-- ⚠️ ATENÇÃO: Só execute se precisar REVERTER a alteração!
-- Isso vai APAGAR a coluna e todos os dados nela!

-- DROP INDEX IF EXISTS idx_moto_modelo_rejeitado;
-- DROP INDEX IF EXISTS idx_moto_ativo_modelo_rejeitado;
-- ALTER TABLE moto DROP COLUMN modelo_rejeitado;

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================
