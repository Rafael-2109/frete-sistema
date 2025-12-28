-- ============================================================
-- EVOLUCAO: Regras de Comissao - Hierarquia de Especificidade
-- Para executar no Render Shell (psql)
-- ============================================================

-- 1. ADICIONAR CAMPO vendedor (standalone, diferente de cliente_vendedor)
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'regra_comissao'
        AND column_name = 'vendedor'
    ) THEN
        ALTER TABLE regra_comissao
        ADD COLUMN vendedor VARCHAR(100);

        CREATE INDEX IF NOT EXISTS idx_regra_comissao_vendedor ON regra_comissao(vendedor);

        COMMENT ON COLUMN regra_comissao.vendedor IS
            'Vendedor para regra tipo VENDEDOR ou VENDEDOR_PRODUTO';
    END IF;
END $$;


-- 2. REMOVER CONSTRAINT ANTIGA E ADICIONAR NOVA COM MAIS TIPOS
-- ============================================================

DO $$
BEGIN
    -- Remover constraint antiga se existir
    ALTER TABLE regra_comissao DROP CONSTRAINT IF EXISTS chk_tipo_regra;

    -- Adicionar nova constraint com todos os tipos
    ALTER TABLE regra_comissao ADD CONSTRAINT chk_tipo_regra
        CHECK (tipo_regra IN (
            'CLIENTE_PRODUTO',    -- 1. Mais especifico
            'GRUPO_PRODUTO',      -- 2.
            'VENDEDOR_PRODUTO',   -- 3.
            'CLIENTE',            -- 4.
            'GRUPO',              -- 5.
            'VENDEDOR',           -- 6.
            'PRODUTO'             -- 7. Menos especifico
        ));
END $$;


-- 3. ADICIONAR PARAMETRO COMISSAO_PADRAO (3%)
-- ============================================================

INSERT INTO parametro_custeio (chave, valor, descricao, atualizado_em, atualizado_por)
VALUES (
    'COMISSAO_PADRAO',
    3.00,
    'Comissao padrao (%) quando nenhuma regra especifica se aplica',
    NOW(),
    'migracao'
)
ON CONFLICT (chave) DO NOTHING;


-- 4. ATUALIZAR COMMENT DO CAMPO
-- ============================================================

COMMENT ON COLUMN carteira_principal.comissao_percentual IS
    'Percentual de comissao (regra mais especifica ou padrao 3%)';


-- 5. VERIFICACAO
-- ============================================================

SELECT 'Campo vendedor' as item,
       CASE WHEN EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_name = 'regra_comissao' AND column_name = 'vendedor'
       ) THEN 'OK' ELSE 'ERRO' END as status;

SELECT 'Parametro COMISSAO_PADRAO' as item,
       CASE WHEN EXISTS (
           SELECT 1 FROM parametro_custeio WHERE chave = 'COMISSAO_PADRAO'
       ) THEN 'OK' ELSE 'ERRO' END as status;

SELECT chave, valor, descricao FROM parametro_custeio
WHERE chave IN ('COMISSAO_PADRAO', 'PERCENTUAL_PERDA')
ORDER BY chave;


-- 6. ORDEM DE ESPECIFICIDADE (referencia)
-- ============================================================
-- 1. CLIENTE_PRODUTO   = cliente + produto (mais especifico)
-- 2. GRUPO_PRODUTO     = grupo empresarial + produto
-- 3. VENDEDOR_PRODUTO  = vendedor + produto
-- 4. CLIENTE           = apenas cliente
-- 5. GRUPO             = apenas grupo empresarial
-- 6. VENDEDOR          = apenas vendedor
-- 7. PRODUTO           = apenas produto (menos especifico)
-- 8. (nenhuma regra)   = COMISSAO_PADRAO (3%)
