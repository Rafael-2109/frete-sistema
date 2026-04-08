-- OPT-B7: Indice parcial composto para filtro base da carteira_simples
-- WHERE ativo=true AND qtd_saldo_produto_pedido > 0 e usado em TODA query
-- Cobre: query principal, qtd_carteira agregada, busca por produto
-- Idempotente: IF NOT EXISTS

CREATE INDEX IF NOT EXISTS idx_carteira_ativo_saldo
ON carteira_principal (num_pedido, cod_produto)
WHERE ativo = true AND qtd_saldo_produto_pedido > 0;
