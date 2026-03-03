-- Fix: Remover faturas cliente CarVia duplicadas
-- ================================================
--
-- Problema: 21 faturas duplicadas (importacao 2x do mesmo PDF em 2025-12-17)
-- IDs duplicados: 27-47 (copias exatas dos originais 6-26)
-- 0 movimentacoes financeiras vinculadas
-- 0 duplicatas em carvia_faturas_transportadora
--
-- IMPORTANTE: Executar ANTES de add_unique_faturas_carvia.sql
--
-- Execucao: Render Shell (psql)

-- Verificar estado ANTES (diagnostico)
SELECT numero_fatura, cnpj_cliente, count(*) as qtd,
       array_agg(id ORDER BY id) as ids
FROM carvia_faturas_cliente
GROUP BY numero_fatura, cnpj_cliente
HAVING count(*) > 1
ORDER BY numero_fatura;

-- Re-apontar operacoes que referenciam duplicatas para originais
UPDATE carvia_operacoes o
SET fatura_cliente_id = orig.id
FROM carvia_faturas_cliente dup
JOIN carvia_faturas_cliente orig ON (
    orig.numero_fatura = dup.numero_fatura
    AND orig.cnpj_cliente = dup.cnpj_cliente
    AND orig.id < dup.id
)
WHERE o.fatura_cliente_id = dup.id
  AND dup.id IN (
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY numero_fatura, cnpj_cliente ORDER BY id
               ) as rn
        FROM carvia_faturas_cliente
    ) sub WHERE rn > 1
  );

-- 1. Remover itens das faturas duplicadas
DELETE FROM carvia_fatura_cliente_itens
WHERE fatura_cliente_id IN (
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY numero_fatura, cnpj_cliente ORDER BY id
               ) as rn
        FROM carvia_faturas_cliente
    ) sub WHERE rn > 1
);

-- 2. Remover faturas duplicadas (manter menor ID por grupo)
DELETE FROM carvia_faturas_cliente
WHERE id IN (
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY numero_fatura, cnpj_cliente ORDER BY id
               ) as rn
        FROM carvia_faturas_cliente
    ) sub WHERE rn > 1
);

-- Verificar estado DEPOIS
SELECT 'Duplicatas restantes' as check,
       count(*) as total
FROM (
    SELECT numero_fatura, cnpj_cliente
    FROM carvia_faturas_cliente
    GROUP BY numero_fatura, cnpj_cliente
    HAVING count(*) > 1
) sub;

SELECT 'Total faturas cliente' as check,
       count(*) as total
FROM carvia_faturas_cliente;
