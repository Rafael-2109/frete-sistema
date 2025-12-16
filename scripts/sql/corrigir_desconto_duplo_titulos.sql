-- ============================================================================
-- CORREÇÃO: Bug de desconto duplo em títulos a receber
-- ============================================================================
-- PROBLEMA:
-- O Odoo aplica o desconto comercial 2 vezes: VALOR * (1-desc) * (1-desc)
--
-- O sistema estava salvando:
-- - valor_original = saldo_total (já com desconto 1x)
-- - valor_titulo = valor_original - desconto (desconto 2x - ERRADO!)
--
-- CORREÇÃO:
-- - valor_titulo = valor_original_antigo (que era o valor correto a pagar)
-- - valor_original = valor_titulo / (1 - desconto_percentual) (valor sem desconto)
-- - desconto = valor_original - valor_titulo (recalculado)
--
-- Data: 2025-12-15
-- ============================================================================

-- 1. VERIFICAR TÍTULOS AFETADOS (apenas visualização)
SELECT
    id,
    titulo_nf,
    parcela,
    SUBSTRING(raz_social_red, 1, 30) as cliente,
    desconto_percentual * 100 as desconto_pct,
    valor_original as valor_original_atual,
    desconto as desconto_atual,
    valor_titulo as valor_titulo_atual,
    -- Valores corrigidos:
    valor_original as valor_titulo_novo,  -- valor_original antigo = valor com desconto 1x
    valor_original / (1 - desconto_percentual) as valor_original_novo,
    (valor_original / (1 - desconto_percentual)) - valor_original as desconto_novo
FROM contas_a_receber
WHERE desconto_percentual > 0
AND desconto_percentual < 1
AND parcela_paga = false
ORDER BY titulo_nf;

-- 2. EXECUTAR CORREÇÃO (descomente para executar)
-- ⚠️  IMPORTANTE: Execute primeiro a query acima para verificar os dados!

/*
UPDATE contas_a_receber
SET
    -- valor_titulo NOVO = valor_original_antigo (que era o saldo_total do Odoo = desconto 1x)
    valor_titulo = valor_original,
    -- valor_original NOVO = valor_titulo_novo / (1 - desconto_pct)
    valor_original = valor_original / (1 - desconto_percentual),
    -- desconto NOVO = será valor_original_novo - valor_titulo_novo
    desconto = (valor_original / (1 - desconto_percentual)) - valor_original,
    -- Marcar que foi atualizado
    atualizado_por = 'Script Correção Desconto Duplo 2025-12-15',
    atualizado_em = NOW()
WHERE desconto_percentual > 0
AND desconto_percentual < 1
AND parcela_paga = false;
*/

-- 3. VERSÃO COM ORDEM CORRETA DE ATUALIZAÇÃO (recomendada)
-- Como todos os campos dependem uns dos outros, precisamos usar uma subconsulta

/*
WITH valores_calculados AS (
    SELECT
        id,
        valor_original as valor_titulo_correto,  -- valor_original antigo é o valor a pagar correto
        valor_original / (1 - desconto_percentual) as valor_original_correto
    FROM contas_a_receber
    WHERE desconto_percentual > 0
    AND desconto_percentual < 1
    AND parcela_paga = false
)
UPDATE contas_a_receber c
SET
    valor_titulo = vc.valor_titulo_correto,
    valor_original = vc.valor_original_correto,
    desconto = vc.valor_original_correto - vc.valor_titulo_correto,
    atualizado_por = 'Script Correção Desconto Duplo 2025-12-15',
    atualizado_em = NOW()
FROM valores_calculados vc
WHERE c.id = vc.id;
*/

-- ============================================================================
-- VERIFICAÇÃO PÓS-CORREÇÃO
-- ============================================================================

-- Verificar que os valores estão consistentes (desconto = valor_original - valor_titulo)
/*
SELECT
    titulo_nf,
    parcela,
    desconto_percentual * 100 as desconto_pct,
    valor_original,
    valor_titulo,
    desconto,
    valor_original - valor_titulo as desconto_calculado,
    valor_titulo / valor_original as percentual_titulo,
    CASE
        WHEN ABS(desconto - (valor_original - valor_titulo)) < 0.01 THEN 'OK'
        ELSE 'ERRO'
    END as status
FROM contas_a_receber
WHERE desconto_percentual > 0
AND desconto_percentual < 1
AND parcela_paga = false
ORDER BY titulo_nf;
*/
