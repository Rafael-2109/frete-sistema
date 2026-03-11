-- =============================================================================
-- REMOVER EXTRATO OFX IMPORTADO ERRADO NA CARVIA
-- =============================================================================
-- USO: Executar no Render Shell (psql)
--
-- INSTRUCOES:
--   1. Altere o filtro WHERE na linha marcada com <<<< CONFIGURAR
--   2. Execute o bloco DIAGNOSTICO primeiro para verificar o que sera removido
--   3. Se estiver correto, execute o bloco REMOCAO
-- =============================================================================


-- =============================================================================
-- PASSO 1: DIAGNOSTICO — Verificar o que sera removido
-- =============================================================================

-- 1a) Listar arquivos OFX importados (para identificar qual remover)
SELECT
    arquivo_ofx,
    conta_bancaria,
    criado_por,
    criado_em::date AS importado_em,
    COUNT(*) AS qtd_linhas,
    MIN(data) AS data_inicio,
    MAX(data) AS data_fim,
    SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) AS total_creditos,
    SUM(CASE WHEN valor < 0 THEN ABS(valor) ELSE 0 END) AS total_debitos
FROM carvia_extrato_linhas
GROUP BY arquivo_ofx, conta_bancaria, criado_por, criado_em::date
;

-- 1b) Verificar linhas do extrato que sera removido
--     <<<< CONFIGURAR: Altere o arquivo_ofx abaixo
SELECT id, fitid, data, tipo, valor, descricao, status_conciliacao, total_conciliado
FROM carvia_extrato_linhas
WHERE arquivo_ofx = 'NOME_DO_ARQUIVO.ofx'  -- <<<< CONFIGURAR
ORDER BY data;

-- 1c) Verificar conciliacoes que serao perdidas (se houver)
SELECT
    c.id AS conciliacao_id,
    c.extrato_linha_id,
    c.tipo_documento,
    c.documento_id,
    c.valor_alocado,
    c.conciliado_por,
    c.conciliado_em::date
FROM carvia_conciliacoes c
JOIN carvia_extrato_linhas e ON e.id = c.extrato_linha_id
WHERE e.arquivo_ofx = 'NOME_DO_ARQUIVO.ofx'  -- <<<< CONFIGURAR
ORDER BY c.tipo_documento, c.documento_id;

-- 1d) Resumo de impacto
SELECT
    'Linhas do extrato a remover' AS item,
    COUNT(*)::text AS valor
FROM carvia_extrato_linhas
WHERE arquivo_ofx = 'NOME_DO_ARQUIVO.ofx'  -- <<<< CONFIGURAR

UNION ALL

SELECT
    'Conciliacoes que serao perdidas',
    COUNT(*)::text
FROM carvia_conciliacoes c
JOIN carvia_extrato_linhas e ON e.id = c.extrato_linha_id
WHERE e.arquivo_ofx = 'NOME_DO_ARQUIVO.ofx'  -- <<<< CONFIGURAR

UNION ALL

SELECT
    'Documentos afetados (totais serao recalculados)',
    COUNT(DISTINCT (c.tipo_documento, c.documento_id))::text
FROM carvia_conciliacoes c
JOIN carvia_extrato_linhas e ON e.id = c.extrato_linha_id
WHERE e.arquivo_ofx = 'NOME_DO_ARQUIVO.ofx';  -- <<<< CONFIGURAR


-- =============================================================================
-- PASSO 2: REMOCAO — Executar somente apos validar o diagnostico acima
-- =============================================================================

BEGIN;

-- 2a) Salvar documentos afetados ANTES de deletar (para recalcular totais depois)
CREATE TEMP TABLE _docs_afetados AS
SELECT DISTINCT c.tipo_documento, c.documento_id
FROM carvia_conciliacoes c
JOIN carvia_extrato_linhas e ON e.id = c.extrato_linha_id
WHERE e.arquivo_ofx = 'extrato-conta-corrente-ofx-unix_202601_20260130180622 1 (2).ofx';  -- <<<< CONFIGURAR

-- 2b) Deletar linhas do extrato (CASCADE remove conciliacoes automaticamente)
DELETE FROM carvia_extrato_linhas
WHERE arquivo_ofx = 'extrato-conta-corrente-ofx-unix_202601_20260130180622 1 (2).ofx';  -- <<<< CONFIGURAR

-- 2c) Recalcular total_conciliado e flag conciliado nas faturas cliente afetadas
UPDATE carvia_faturas_cliente fc
SET
    total_conciliado = COALESCE(sub.soma, 0),
    conciliado = COALESCE(sub.soma, 0) >= fc.valor_total
FROM (
    SELECT d.documento_id,
           SUM(c.valor_alocado) AS soma
    FROM _docs_afetados d
    LEFT JOIN carvia_conciliacoes c
        ON c.tipo_documento = 'fatura_cliente'
       AND c.documento_id = d.documento_id
    WHERE d.tipo_documento = 'fatura_cliente'
    GROUP BY d.documento_id
) sub
WHERE fc.id = sub.documento_id
  AND EXISTS (SELECT 1 FROM _docs_afetados da
              WHERE da.tipo_documento = 'fatura_cliente'
                AND da.documento_id = fc.id);

-- 2d) Recalcular total_conciliado e flag conciliado nas faturas transportadora afetadas
UPDATE carvia_faturas_transportadora ft
SET
    total_conciliado = COALESCE(sub.soma, 0),
    conciliado = COALESCE(sub.soma, 0) >= ft.valor_total
FROM (
    SELECT d.documento_id,
           SUM(c.valor_alocado) AS soma
    FROM _docs_afetados d
    LEFT JOIN carvia_conciliacoes c
        ON c.tipo_documento = 'fatura_transportadora'
       AND c.documento_id = d.documento_id
    WHERE d.tipo_documento = 'fatura_transportadora'
    GROUP BY d.documento_id
) sub
WHERE ft.id = sub.documento_id
  AND EXISTS (SELECT 1 FROM _docs_afetados da
              WHERE da.tipo_documento = 'fatura_transportadora'
                AND da.documento_id = ft.id);

-- 2e) Recalcular total_conciliado e flag conciliado nas despesas afetadas
UPDATE carvia_despesas dp
SET
    total_conciliado = COALESCE(sub.soma, 0),
    conciliado = COALESCE(sub.soma, 0) >= dp.valor
FROM (
    SELECT d.documento_id,
           SUM(c.valor_alocado) AS soma
    FROM _docs_afetados d
    LEFT JOIN carvia_conciliacoes c
        ON c.tipo_documento = 'despesa'
       AND c.documento_id = d.documento_id
    WHERE d.tipo_documento = 'despesa'
    GROUP BY d.documento_id
) sub
WHERE dp.id = sub.documento_id
  AND EXISTS (SELECT 1 FROM _docs_afetados da
              WHERE da.tipo_documento = 'despesa'
                AND da.documento_id = dp.id);

-- 2f) Limpar tabela temporaria
DROP TABLE _docs_afetados;

-- 2g) Verificacao pos-remocao
SELECT 'Linhas restantes do arquivo' AS verificacao,
       COUNT(*)::text AS resultado
FROM carvia_extrato_linhas
WHERE arquivo_ofx = 'extrato-conta-corrente-ofx-unix_202601_20260130180622 1 (2).ofx'  -- <<<< CONFIGURAR
UNION ALL
SELECT 'Conciliacoes orfas (deve ser 0)',
       COUNT(*)::text
FROM carvia_conciliacoes c
WHERE NOT EXISTS (
    SELECT 1 FROM carvia_extrato_linhas e WHERE e.id = c.extrato_linha_id
);

COMMIT;
