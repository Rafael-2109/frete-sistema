-- =============================================================================
-- Backfill fator_conversao — 3 tabelas De-Para
-- =============================================================================
-- Corrige registros De-Para com fator_conversao=1.0, MAS somente quando a
-- unidade do XML (nf_devolucao_linha) confirma ser tipo UNIDADE.
--
-- Regra de negócio:
-- - Mesmo cliente + mesmo código pode pedir em UND ou CX
-- - Se unidade XML = tipo UNIDADE → fator deve ser N (do NxM no nome)
-- - Se unidade XML = CX ou não encontrada → fator=1.0 está correto
--
-- Executar: Render Shell (PREVIEW primeiro, depois descomente UPDATE)
-- Data: 21/02/2026
-- =============================================================================


-- =====================================================================
-- FASE A: depara_produto_cliente
-- =====================================================================

-- PREVIEW A1: Candidatos com NxM + unidade do XML
SELECT
    dp.id,
    dp.prefixo_cnpj,
    dp.codigo_cliente,
    dp.nosso_codigo,
    dp.unidade_medida_cliente AS unidade_atual,
    cp.nome_produto,
    CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) AS novo_fator,
    latest_xml.unidade_medida AS unidade_xml,
    CASE
        WHEN latest_xml.unidade_medida IS NULL THEN 'SEM_XML'
        WHEN TRIM(UPPER(latest_xml.unidade_medida)) ~ '^(UND|UNID|UN|UNI|UNIDADE|PC|PCS|PECA|PECAS|BD|BALDE|BLD|SC|SACO|PT|POTE|BL|BA|SH|SACHE)$'
            THEN 'UNIDADE_OK'
        ELSE 'CAIXA_SKIP'
    END AS classificacao
FROM depara_produto_cliente dp
JOIN cadastro_palletizacao cp ON dp.nosso_codigo = cp.cod_produto
LEFT JOIN LATERAL (
    SELECT ndl.unidade_medida
    FROM nf_devolucao_linha ndl
    JOIN nf_devolucao nd ON ndl.nf_devolucao_id = nd.id
    WHERE ndl.codigo_produto_cliente = dp.codigo_cliente
      AND SUBSTRING(nd.cnpj_emitente, 1, 8) = dp.prefixo_cnpj
      AND ndl.unidade_medida IS NOT NULL
    ORDER BY nd.data_registro DESC
    LIMIT 1
) latest_xml ON true
WHERE dp.fator_conversao = 1.0
  AND dp.ativo = true
  AND cp.nome_produto ~ '\d+[Xx]\d+'
  AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
ORDER BY classificacao, dp.id;


-- PREVIEW A1 resumo: Contagem por classificação
SELECT
    CASE
        WHEN latest_xml.unidade_medida IS NULL THEN 'SEM_XML'
        WHEN TRIM(UPPER(latest_xml.unidade_medida)) ~ '^(UND|UNID|UN|UNI|UNIDADE|PC|PCS|PECA|PECAS|BD|BALDE|BLD|SC|SACO|PT|POTE|BL|BA|SH|SACHE)$'
            THEN 'UNIDADE_OK'
        ELSE 'CAIXA_SKIP'
    END AS classificacao,
    COUNT(*) AS qtd
FROM depara_produto_cliente dp
JOIN cadastro_palletizacao cp ON dp.nosso_codigo = cp.cod_produto
LEFT JOIN LATERAL (
    SELECT ndl.unidade_medida
    FROM nf_devolucao_linha ndl
    JOIN nf_devolucao nd ON ndl.nf_devolucao_id = nd.id
    WHERE ndl.codigo_produto_cliente = dp.codigo_cliente
      AND SUBSTRING(nd.cnpj_emitente, 1, 8) = dp.prefixo_cnpj
      AND ndl.unidade_medida IS NOT NULL
    ORDER BY nd.data_registro DESC
    LIMIT 1
) latest_xml ON true
WHERE dp.fator_conversao = 1.0
  AND dp.ativo = true
  AND cp.nome_produto ~ '\d+[Xx]\d+'
  AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
GROUP BY classificacao
ORDER BY classificacao;


-- UPDATE A1: Preencher unidade_medida_cliente com unidade do XML (onde NULL)
-- DESCOMENTE para executar após validar preview
/*
UPDATE depara_produto_cliente dp
SET
    unidade_medida_cliente = sub.unidade_xml,
    atualizado_em = NOW(),
    atualizado_por = 'backfill_fator_conversao'
FROM (
    SELECT DISTINCT ON (dp2.id)
        dp2.id,
        ndl.unidade_medida AS unidade_xml
    FROM depara_produto_cliente dp2
    JOIN nf_devolucao nd ON SUBSTRING(nd.cnpj_emitente, 1, 8) = dp2.prefixo_cnpj
    JOIN nf_devolucao_linha ndl ON ndl.nf_devolucao_id = nd.id
        AND ndl.codigo_produto_cliente = dp2.codigo_cliente
    JOIN cadastro_palletizacao cp ON dp2.nosso_codigo = cp.cod_produto
    WHERE dp2.unidade_medida_cliente IS NULL
      AND dp2.ativo = true
      AND dp2.fator_conversao = 1.0
      AND ndl.unidade_medida IS NOT NULL
      AND cp.nome_produto ~ '\d+[Xx]\d+'
      AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
    ORDER BY dp2.id, nd.data_registro DESC
) sub
WHERE dp.id = sub.id;
*/


-- UPDATE A2: Atualizar fator_conversao onde unidade é tipo UNIDADE
-- DESCOMENTE para executar após validar preview
/*
UPDATE depara_produto_cliente dp
SET
    fator_conversao = CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER),
    unidade_medida_nosso = COALESCE(dp.unidade_medida_nosso, 'CX'),
    atualizado_em = NOW(),
    atualizado_por = 'backfill_fator_conversao'
FROM cadastro_palletizacao cp
WHERE dp.nosso_codigo = cp.cod_produto
  AND dp.fator_conversao = 1.0
  AND dp.ativo = true
  AND cp.nome_produto ~ '\d+[Xx]\d+'
  AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
  AND dp.unidade_medida_cliente IS NOT NULL
  AND TRIM(UPPER(dp.unidade_medida_cliente)) ~ '^(UND|UNID|UN|UNI|UNIDADE|PC|PCS|PECA|PECAS|BD|BALDE|BLD|SC|SACO|PT|POTE|BL|BA|SH|SACHE)$';
*/


-- =====================================================================
-- FASE B: portal_atacadao_produto_depara
-- =====================================================================

-- PREVIEW B: Candidatos com NxM + unidade do XML
SELECT
    dp.id,
    dp.cnpj_cliente,
    dp.codigo_atacadao,
    dp.codigo_nosso,
    cp.nome_produto,
    CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) AS novo_fator,
    latest_xml.unidade_medida AS unidade_xml,
    CASE
        WHEN latest_xml.unidade_medida IS NULL THEN 'SEM_XML'
        WHEN TRIM(UPPER(latest_xml.unidade_medida)) ~ '^(UND|UNID|UN|UNI|UNIDADE|PC|PCS|PECA|PECAS|BD|BALDE|BLD|SC|SACO|PT|POTE|BL|BA|SH|SACHE)$'
            THEN 'UNIDADE_OK'
        ELSE 'CAIXA_SKIP'
    END AS classificacao
FROM portal_atacadao_produto_depara dp
JOIN cadastro_palletizacao cp ON dp.codigo_nosso = cp.cod_produto
LEFT JOIN LATERAL (
    SELECT ndl.unidade_medida
    FROM nf_devolucao_linha ndl
    JOIN nf_devolucao nd ON ndl.nf_devolucao_id = nd.id
    WHERE ndl.codigo_produto_cliente = dp.codigo_atacadao
      AND dp.cnpj_cliente IS NOT NULL
      AND SUBSTRING(nd.cnpj_emitente, 1, 8) = SUBSTRING(dp.cnpj_cliente, 1, 8)
      AND ndl.unidade_medida IS NOT NULL
    ORDER BY nd.data_registro DESC
    LIMIT 1
) latest_xml ON true
WHERE dp.fator_conversao = 1.0
  AND dp.ativo = true
  AND cp.nome_produto ~ '\d+[Xx]\d+'
  AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
ORDER BY classificacao, dp.id;


-- UPDATE B: Atualizar fator onde unidade XML é tipo UNIDADE
-- Nota: tabela NÃO tem atualizado_por
-- DESCOMENTE para executar após validar preview
/*
UPDATE portal_atacadao_produto_depara dp
SET
    fator_conversao = sub.novo_fator,
    atualizado_em = NOW()
FROM (
    SELECT DISTINCT ON (dp2.id)
        dp2.id,
        CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) AS novo_fator
    FROM portal_atacadao_produto_depara dp2
    JOIN cadastro_palletizacao cp ON dp2.codigo_nosso = cp.cod_produto
    JOIN nf_devolucao nd ON SUBSTRING(nd.cnpj_emitente, 1, 8) = SUBSTRING(dp2.cnpj_cliente, 1, 8)
    JOIN nf_devolucao_linha ndl ON ndl.nf_devolucao_id = nd.id
        AND ndl.codigo_produto_cliente = dp2.codigo_atacadao
    WHERE dp2.fator_conversao = 1.0
      AND dp2.ativo = true
      AND dp2.cnpj_cliente IS NOT NULL
      AND cp.nome_produto ~ '\d+[Xx]\d+'
      AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
      AND ndl.unidade_medida IS NOT NULL
      AND TRIM(UPPER(ndl.unidade_medida)) ~ '^(UND|UNID|UN|UNI|UNIDADE|PC|PCS|PECA|PECAS|BD|BALDE|BLD|SC|SACO|PT|POTE|BL|BA|SH|SACHE)$'
    ORDER BY dp2.id, nd.data_registro DESC
) sub
WHERE dp.id = sub.id;
*/


-- =====================================================================
-- FASE C: portal_sendas_produto_depara
-- =====================================================================

-- PREVIEW C: Candidatos com NxM + unidade do XML
SELECT
    dp.id,
    dp.cnpj_cliente,
    dp.codigo_sendas,
    dp.codigo_nosso,
    cp.nome_produto,
    CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) AS novo_fator,
    latest_xml.unidade_medida AS unidade_xml,
    CASE
        WHEN latest_xml.unidade_medida IS NULL THEN 'SEM_XML'
        WHEN TRIM(UPPER(latest_xml.unidade_medida)) ~ '^(UND|UNID|UN|UNI|UNIDADE|PC|PCS|PECA|PECAS|BD|BALDE|BLD|SC|SACO|PT|POTE|BL|BA|SH|SACHE)$'
            THEN 'UNIDADE_OK'
        ELSE 'CAIXA_SKIP'
    END AS classificacao
FROM portal_sendas_produto_depara dp
JOIN cadastro_palletizacao cp ON dp.codigo_nosso = cp.cod_produto
LEFT JOIN LATERAL (
    SELECT ndl.unidade_medida
    FROM nf_devolucao_linha ndl
    JOIN nf_devolucao nd ON ndl.nf_devolucao_id = nd.id
    WHERE ndl.codigo_produto_cliente = dp.codigo_sendas
      AND dp.cnpj_cliente IS NOT NULL
      AND SUBSTRING(nd.cnpj_emitente, 1, 8) = SUBSTRING(dp.cnpj_cliente, 1, 8)
      AND ndl.unidade_medida IS NOT NULL
    ORDER BY nd.data_registro DESC
    LIMIT 1
) latest_xml ON true
WHERE dp.fator_conversao = 1.0
  AND dp.ativo = true
  AND cp.nome_produto ~ '\d+[Xx]\d+'
  AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
ORDER BY classificacao, dp.id;


-- UPDATE C: Atualizar fator onde unidade XML é tipo UNIDADE
-- Nota: tabela NÃO tem atualizado_por
-- DESCOMENTE para executar após validar preview
/*
UPDATE portal_sendas_produto_depara dp
SET
    fator_conversao = sub.novo_fator,
    atualizado_em = NOW()
FROM (
    SELECT DISTINCT ON (dp2.id)
        dp2.id,
        CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) AS novo_fator
    FROM portal_sendas_produto_depara dp2
    JOIN cadastro_palletizacao cp ON dp2.codigo_nosso = cp.cod_produto
    JOIN nf_devolucao nd ON SUBSTRING(nd.cnpj_emitente, 1, 8) = SUBSTRING(dp2.cnpj_cliente, 1, 8)
    JOIN nf_devolucao_linha ndl ON ndl.nf_devolucao_id = nd.id
        AND ndl.codigo_produto_cliente = dp2.codigo_sendas
    WHERE dp2.fator_conversao = 1.0
      AND dp2.ativo = true
      AND dp2.cnpj_cliente IS NOT NULL
      AND cp.nome_produto ~ '\d+[Xx]\d+'
      AND CAST(SUBSTRING(cp.nome_produto FROM '(\d+)[Xx]\d+') AS INTEGER) > 1
      AND ndl.unidade_medida IS NOT NULL
      AND TRIM(UPPER(ndl.unidade_medida)) ~ '^(UND|UNID|UN|UNI|UNIDADE|PC|PCS|PECA|PECAS|BD|BALDE|BLD|SC|SACO|PT|POTE|BL|BA|SH|SACHE)$'
    ORDER BY dp2.id, nd.data_registro DESC
) sub
WHERE dp.id = sub.id;
*/


-- =====================================================================
-- VERIFICAÇÃO PÓS-EXECUÇÃO
-- =====================================================================

-- Executar após os UPDATEs para validar:
/*
SELECT 'depara_produto_cliente' AS tabela,
       COUNT(*) FILTER (WHERE fator_conversao > 1.0) AS fator_corrigido,
       COUNT(*) FILTER (WHERE fator_conversao = 1.0) AS fator_1,
       COUNT(*) AS total
FROM depara_produto_cliente WHERE ativo = true
UNION ALL
SELECT 'portal_atacadao',
       COUNT(*) FILTER (WHERE fator_conversao > 1.0),
       COUNT(*) FILTER (WHERE fator_conversao = 1.0),
       COUNT(*)
FROM portal_atacadao_produto_depara WHERE ativo = true
UNION ALL
SELECT 'portal_sendas',
       COUNT(*) FILTER (WHERE fator_conversao > 1.0),
       COUNT(*) FILTER (WHERE fator_conversao = 1.0),
       COUNT(*)
FROM portal_sendas_produto_depara WHERE ativo = true;
*/
