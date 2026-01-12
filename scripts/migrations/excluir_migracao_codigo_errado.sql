-- ======================================================================
-- IDENTIFICAR E EXCLUIR MOVIMENTAÇÕES COM CÓDIGO ERRADO
-- Movimentações com "Migração retroativa" e [###] no nome_produto
-- ======================================================================

-- ======================================================================
-- 1. CONTAR CASOS
-- ======================================================================

SELECT
    DATE(criado_em) as data_criacao,
    DATE(data_movimentacao) as data_mov,
    local_movimentacao,
    COUNT(*) as quantidade
FROM movimentacao_estoque
WHERE observacao ILIKE '%Migração retroativa%'
  AND nome_produto ~ '^\[\d+\]'
  AND ativo = TRUE
GROUP BY DATE(criado_em), DATE(data_movimentacao), local_movimentacao
ORDER BY data_criacao, data_mov, local_movimentacao;

-- Total geral
SELECT COUNT(*) as total_registros_com_codigo_errado
FROM movimentacao_estoque
WHERE observacao ILIKE '%Migração retroativa%'
  AND nome_produto ~ '^\[\d+\]'
  AND ativo = TRUE;

-- ======================================================================
-- 2. VER EXEMPLOS (opcional)
-- ======================================================================

SELECT id, cod_produto, nome_produto, numero_nf, local_movimentacao,
       data_movimentacao, DATE(criado_em) as criado_em
FROM movimentacao_estoque
WHERE observacao ILIKE '%Migração retroativa%'
  AND nome_produto ~ '^\[\d+\]'
  AND ativo = TRUE
LIMIT 10;

-- ======================================================================
-- 3. EXCLUIR (soft delete - marcar como inativo)
-- ======================================================================

UPDATE movimentacao_estoque
SET ativo = FALSE,
    atualizado_em = NOW(),
    atualizado_por = 'Exclusão Migração Código Errado'
WHERE observacao ILIKE '%Migração retroativa%'
  AND nome_produto ~ '^\[\d+\]'
  AND ativo = TRUE;

-- ======================================================================
-- 4. VERIFICAR EXCLUSÃO
-- ======================================================================

SELECT COUNT(*) as restantes_com_codigo_errado
FROM movimentacao_estoque
WHERE observacao ILIKE '%Migração retroativa%'
  AND nome_produto ~ '^\[\d+\]'
  AND ativo = TRUE;

-- Deve retornar 0
