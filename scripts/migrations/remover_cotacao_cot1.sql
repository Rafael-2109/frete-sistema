-- Remover cotacao COT-1 e todas as dependencias
-- Executar no Render Shell (PostgreSQL)
-- IMPORTANTE: Verificar antes de executar em producao

BEGIN;

-- 1. Identificar o ID da cotacao
-- SELECT id FROM carvia_cotacoes WHERE numero_cotacao = 'COT-1';

-- 2. Deletar itens de pedidos vinculados (cascade manual — carvia_pedidos nao tem ON DELETE CASCADE na FK cotacao_id)
DELETE FROM carvia_pedido_itens
WHERE pedido_id IN (
    SELECT id FROM carvia_pedidos
    WHERE cotacao_id = (SELECT id FROM carvia_cotacoes WHERE numero_cotacao = 'COT-1')
);

-- 3. Deletar pedidos vinculados
DELETE FROM carvia_pedidos
WHERE cotacao_id = (SELECT id FROM carvia_cotacoes WHERE numero_cotacao = 'COT-1');

-- 4. Deletar motos da cotacao (tem ON DELETE CASCADE, mas explicito por seguranca)
DELETE FROM carvia_cotacao_motos
WHERE cotacao_id = (SELECT id FROM carvia_cotacoes WHERE numero_cotacao = 'COT-1');

-- 5. Deletar a cotacao
DELETE FROM carvia_cotacoes
WHERE numero_cotacao = 'COT-1';

COMMIT;
