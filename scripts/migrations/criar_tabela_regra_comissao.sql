-- ============================================================
-- MIGRACAO: Regras de Comissao e Percentual de Perda
-- Para executar no Render Shell (psql)
-- ============================================================

-- 1. CRIAR TABELA regra_comissao
-- ============================================================

CREATE TABLE IF NOT EXISTS regra_comissao (
    id SERIAL PRIMARY KEY,

    -- Tipo de regra
    tipo_regra VARCHAR(20) NOT NULL,

    -- Criterio A: Grupo empresarial
    grupo_empresarial VARCHAR(100),

    -- Criterio B: Cliente
    raz_social_red VARCHAR(100),
    cliente_cod_uf VARCHAR(2),
    cliente_vendedor VARCHAR(100),
    cliente_equipe VARCHAR(100),

    -- Criterio C: Produto
    cod_produto VARCHAR(50),
    produto_grupo VARCHAR(100),
    produto_cliente VARCHAR(100),

    -- Percentual
    comissao_percentual NUMERIC(5, 2) NOT NULL,

    -- Vigencia
    vigencia_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
    vigencia_fim DATE,

    -- Controle
    prioridade INTEGER DEFAULT 0,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100),

    CONSTRAINT chk_tipo_regra CHECK (tipo_regra IN ('GRUPO', 'CLIENTE', 'PRODUTO'))
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_regra_comissao_tipo ON regra_comissao(tipo_regra);
CREATE INDEX IF NOT EXISTS idx_regra_comissao_grupo ON regra_comissao(grupo_empresarial);
CREATE INDEX IF NOT EXISTS idx_regra_comissao_cliente ON regra_comissao(raz_social_red);
CREATE INDEX IF NOT EXISTS idx_regra_comissao_produto ON regra_comissao(cod_produto);
CREATE INDEX IF NOT EXISTS idx_regra_comissao_ativo ON regra_comissao(ativo);
CREATE INDEX IF NOT EXISTS idx_regra_comissao_vigencia ON regra_comissao(vigencia_inicio, vigencia_fim);


-- 2. ADICIONAR CAMPO comissao_percentual em carteira_principal
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carteira_principal'
        AND column_name = 'comissao_percentual'
    ) THEN
        ALTER TABLE carteira_principal
        ADD COLUMN comissao_percentual NUMERIC(5, 2) DEFAULT 0;

        COMMENT ON COLUMN carteira_principal.comissao_percentual IS
            'Percentual de comissao calculado (soma das regras aplicaveis)';
    END IF;
END $$;


-- 3. ADICIONAR PARAMETRO PERCENTUAL_PERDA
-- ============================================================

INSERT INTO parametro_custeio (chave, valor, descricao, atualizado_em, atualizado_por)
VALUES (
    'PERCENTUAL_PERDA',
    0.00,
    'Percentual de perda aplicado sobre (custo_considerado + custo_producao). Ex: 0.5 = 0.5%',
    NOW(),
    'migracao'
)
ON CONFLICT (chave) DO NOTHING;


-- 4. VERIFICACAO
-- ============================================================

SELECT 'Tabela regra_comissao' as item,
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'regra_comissao')
            THEN 'OK' ELSE 'ERRO' END as status;

SELECT 'Campo comissao_percentual' as item,
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'carteira_principal' AND column_name = 'comissao_percentual')
            THEN 'OK' ELSE 'ERRO' END as status;

SELECT 'Parametro PERCENTUAL_PERDA' as item,
       CASE WHEN EXISTS (SELECT 1 FROM parametro_custeio WHERE chave = 'PERCENTUAL_PERDA')
            THEN 'OK' ELSE 'ERRO' END as status;

SELECT chave, valor, descricao FROM parametro_custeio WHERE chave = 'PERCENTUAL_PERDA';
