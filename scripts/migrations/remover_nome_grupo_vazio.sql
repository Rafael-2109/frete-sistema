-- ============================================================
-- MIGRAÇÃO: Remover registros com nome_grupo vazio ou NULL
-- Data: 2026-01-15
-- Descrição: Remove duplicatas de previsao_demanda causadas por
--            importação com nome_grupo vazio ou NULL
-- ============================================================

-- ============================================================
-- PASSO 1: Verificar o que será deletado (EXECUTAR PRIMEIRO)
-- ============================================================
SELECT
    CASE
        WHEN nome_grupo IS NULL THEN 'NULL'
        WHEN nome_grupo = '' THEN 'VAZIO'
        ELSE nome_grupo
    END as tipo_grupo,
    COUNT(*) as registros,
    SUM(qtd_demanda_prevista) as total_qtd
FROM previsao_demanda
WHERE nome_grupo IS NULL OR nome_grupo = ''
GROUP BY nome_grupo;

-- ============================================================
-- PASSO 2: Deletar registros com nome_grupo vazio ou NULL
-- ============================================================
DELETE FROM previsao_demanda
WHERE nome_grupo IS NULL OR nome_grupo = '';

-- ============================================================
-- PASSO 3: Verificar resultado final
-- ============================================================
SELECT
    nome_grupo,
    COUNT(*) as registros,
    SUM(qtd_demanda_prevista) as total_qtd
FROM previsao_demanda
GROUP BY nome_grupo
ORDER BY nome_grupo;
