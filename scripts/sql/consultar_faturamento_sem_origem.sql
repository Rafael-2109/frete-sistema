-- Consultar FaturamentoProduto com origem vazia ou NULL
SELECT
    numero_nf,
    cod_produto,
    nome_produto,
    nome_cliente
FROM faturamento_produto
WHERE origem = 'false';
