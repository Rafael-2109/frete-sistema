-- ============================================================================
-- CORREÇÃO DE DADOS IMPORTADOS - Carteira Não-Odoo
-- Data: 2025-01-15
-- ============================================================================

-- 1. VERIFICAR DADOS ATUAIS
SELECT
    COUNT(*) as total_registros,
    COUNT(CASE WHEN vendedor IS NULL OR vendedor = '' THEN 1 END) as sem_vendedor,
    COUNT(CASE WHEN equipe_vendas IS NULL OR equipe_vendas = '' THEN 1 END) as sem_equipe,
    COUNT(CASE WHEN nome_produto LIKE 'Produto %' THEN 1 END) as nome_generico
FROM carteira_copia
WHERE ativo = true;

-- 2. ATUALIZAR NOME DOS PRODUTOS DE CADASTRO_PALLETIZACAO
UPDATE carteira_copia cc
SET
    nome_produto = cp.nome_produto,
    updated_at = NOW()
FROM cadastro_palletizacao cp
WHERE cc.cod_produto = cp.cod_produto
  AND cc.ativo = true
  AND (cc.nome_produto LIKE 'Produto %' OR cc.nome_produto IS NULL);

-- 3. VERIFICAR SE HÁ CLIENTES COM VENDEDOR/EQUIPE VAZIOS
SELECT
    cc.cnpj_cpf,
    cc.raz_social_red,
    cc.vendedor,
    cc.equipe_vendas,
    cli.vendedor as vendedor_cadastro,
    cli.equipe_vendas as equipe_cadastro
FROM carteira_copia cc
LEFT JOIN cadastro_cliente cli ON cli.cnpj_cpf = REPLACE(REPLACE(REPLACE(cc.cnpj_cpf, '.', ''), '/', ''), '-', '')
WHERE cc.ativo = true
  AND (cc.vendedor IS NULL OR cc.vendedor = '' OR cc.equipe_vendas IS NULL OR cc.equipe_vendas = '')
LIMIT 20;

-- 4. ATUALIZAR VENDEDOR/EQUIPE DE CADASTRO_CLIENTE (se vazio)
UPDATE carteira_copia cc
SET
    vendedor = cli.vendedor,
    equipe_vendas = cli.equipe_vendas,
    updated_at = NOW()
FROM cadastro_cliente cli
WHERE REPLACE(REPLACE(REPLACE(cc.cnpj_cpf, '.', ''), '/', ''), '-', '') = cli.cnpj_cpf
  AND cc.ativo = true
  AND (cc.vendedor IS NULL OR cc.vendedor = '')
  AND cli.vendedor IS NOT NULL;

-- 5. SINCRONIZAR COM CARTEIRA_PRINCIPAL
UPDATE carteira_principal cp
SET
    nome_produto = cc.nome_produto,
    vendedor = cc.vendedor,
    equipe_vendas = cc.equipe_vendas,
    updated_at = NOW()
FROM carteira_copia cc
WHERE cp.num_pedido = cc.num_pedido
  AND cp.cod_produto = cc.cod_produto
  AND cp.ativo = true
  AND cc.ativo = true;

-- 6. VERIFICAR RESULTADO FINAL
SELECT
    COUNT(*) as total_registros,
    COUNT(CASE WHEN vendedor IS NULL OR vendedor = '' THEN 1 END) as sem_vendedor,
    COUNT(CASE WHEN equipe_vendas IS NULL OR equipe_vendas = '' THEN 1 END) as sem_equipe,
    COUNT(CASE WHEN nome_produto LIKE 'Produto %' THEN 1 END) as nome_generico
FROM carteira_copia
WHERE ativo = true;

-- 7. LISTAR PEDIDOS QUE AINDA PRECISAM DE AJUSTE MANUAL
SELECT
    num_pedido,
    cod_produto,
    nome_produto,
    cnpj_cpf,
    raz_social_red,
    vendedor,
    equipe_vendas
FROM carteira_copia
WHERE ativo = true
  AND (vendedor IS NULL OR vendedor = '' OR equipe_vendas IS NULL OR equipe_vendas = '')
ORDER BY num_pedido;
