-- Script SQL para verificar e corrigir o produto 4159301
-- Execute este script no banco de dados para diagnosticar e corrigir o problema

-- 1. Verificar se o produto existe na CarteiraPrincipal
SELECT 'CarteiraPrincipal' as tabela, COUNT(*) as total, 
       COUNT(CASE WHEN ativo = true THEN 1 END) as ativos,
       COUNT(CASE WHEN ativo = false THEN 1 END) as inativos
FROM carteira_principal 
WHERE cod_produto = '4159301';

-- Mostrar detalhes dos registros
SELECT num_pedido, nome_produto, qtd_saldo_produto_pedido, ativo, created_at
FROM carteira_principal 
WHERE cod_produto = '4159301'
LIMIT 5;

-- 2. Verificar se existe no CadastroPalletizacao
SELECT 'CadastroPalletizacao' as tabela, COUNT(*) as total
FROM cadastro_palletizacao 
WHERE cod_produto = '4159301';

-- Mostrar detalhes se existir
SELECT * FROM cadastro_palletizacao 
WHERE cod_produto = '4159301';

-- 3. Verificar MovimentacaoEstoque
SELECT 'MovimentacaoEstoque' as tabela, COUNT(*) as total, SUM(qtd_movimentacao) as saldo_total
FROM movimentacao_estoque 
WHERE cod_produto = '4159301' AND ativo = true;

-- 4. Verificar Separacao
SELECT 'Separacao' as tabela, COUNT(*) as total, status
FROM separacao 
WHERE cod_produto = '4159301'
GROUP BY status;

-- ========================================
-- CORREÇÃO: Se o produto NÃO existir no CadastroPalletizacao
-- mas EXISTIR na CarteiraPrincipal, execute:
-- ========================================

-- Verificar antes de inserir
DO $$
DECLARE
    v_existe INTEGER;
    v_nome_produto VARCHAR(255);
BEGIN
    -- Verificar se já existe
    SELECT COUNT(*) INTO v_existe
    FROM cadastro_palletizacao 
    WHERE cod_produto = '4159301';
    
    IF v_existe = 0 THEN
        -- Buscar nome do produto na carteira
        SELECT nome_produto INTO v_nome_produto
        FROM carteira_principal 
        WHERE cod_produto = '4159301'
        LIMIT 1;
        
        -- Inserir no cadastro
        INSERT INTO cadastro_palletizacao (
            cod_produto, 
            nome_produto, 
            palletizacao, 
            peso_bruto, 
            ativo,
            created_at,
            updated_at,
            created_by,
            updated_by
        ) VALUES (
            '4159301',
            COALESCE(v_nome_produto, 'PESSEGOS EM CALDA - LATA 12X485 GR - LA FAMIGLIA'),
            1.0,  -- Palletização padrão
            1.0,  -- Peso bruto padrão
            true, -- Ativo
            NOW(),
            NOW(),
            'CorrecaoSQL',
            'CorrecaoSQL'
        );
        
        RAISE NOTICE 'Produto 4159301 inserido no CadastroPalletizacao com sucesso!';
    ELSE
        RAISE NOTICE 'Produto 4159301 já existe no CadastroPalletizacao';
    END IF;
END $$;

-- Verificar resultado final
SELECT 'VERIFICAÇÃO FINAL' as status;
SELECT cp.num_pedido, cp.nome_produto, cp.qtd_saldo_produto_pedido,
       CASE WHEN cad.cod_produto IS NOT NULL THEN 'SIM' ELSE 'NÃO' END as tem_cadastro_pallet
FROM carteira_principal cp
LEFT JOIN cadastro_palletizacao cad ON cp.cod_produto = cad.cod_produto
WHERE cp.cod_produto = '4159301'
LIMIT 5;