-- ============================================================
-- ATUALIZAÇÃO DE CNPJ DOS PEDIDOS DE COMPRA
-- ============================================================
-- NOTA: Este script não pode ser executado diretamente no Render
-- pois requer acesso ao Odoo para buscar os CNPJs.
--
-- Use o script Python: python scripts/atualizar_cnpj_pedidos_compras.py
--
-- Este SQL serve apenas para consultas de verificação.
-- ============================================================

-- Verificar situação atual
SELECT
    COUNT(*) as total,
    COUNT(cnpj_fornecedor) as com_cnpj,
    COUNT(*) - COUNT(cnpj_fornecedor) as sem_cnpj
FROM pedido_compras;

-- Ver fornecedores únicos sem CNPJ
SELECT DISTINCT raz_social
FROM pedido_compras
WHERE cnpj_fornecedor IS NULL
  AND raz_social IS NOT NULL
ORDER BY raz_social;

-- Ver distribuição por data de criação
SELECT
    DATE(criado_em) as data_criacao,
    COUNT(*) as total,
    COUNT(cnpj_fornecedor) as com_cnpj
FROM pedido_compras
GROUP BY DATE(criado_em)
ORDER BY DATE(criado_em) DESC;
