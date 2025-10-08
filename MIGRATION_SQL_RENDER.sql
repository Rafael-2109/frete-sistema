-- =====================================================================
-- MIGRAÇÃO: CrossDocking e Parcelamento - Sistema MotoChefe
-- Data: 07/10/2025
-- Banco: PostgreSQL (Render)
-- =====================================================================
-- INSTRUÇÕES:
-- 1. Abra o Shell do Render (Connect > Shell)
-- 2. Cole este script completo
-- 3. Execute
-- =====================================================================

-- ====================================================================
-- 1. CRIAR TABELA: cross_docking
-- ====================================================================
CREATE TABLE IF NOT EXISTS cross_docking (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,

    -- Movimentação
    responsavel_movimentacao VARCHAR(20),
    custo_movimentacao NUMERIC(15, 2) DEFAULT 0 NOT NULL,
    incluir_custo_movimentacao BOOLEAN DEFAULT FALSE NOT NULL,

    -- Precificação
    tipo_precificacao VARCHAR(20) DEFAULT 'TABELA' NOT NULL,
    markup NUMERIC(15, 2) DEFAULT 0 NOT NULL,

    -- Comissão
    tipo_comissao VARCHAR(20) DEFAULT 'FIXA_EXCEDENTE' NOT NULL,
    valor_comissao_fixa NUMERIC(15, 2) DEFAULT 0 NOT NULL,
    percentual_comissao NUMERIC(5, 2) DEFAULT 0 NOT NULL,
    comissao_rateada BOOLEAN DEFAULT TRUE NOT NULL,

    -- Montagem
    permitir_montagem BOOLEAN DEFAULT TRUE NOT NULL,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- ====================================================================
-- 2. CRIAR TABELA: tabela_preco_crossdocking
-- ====================================================================
CREATE TABLE IF NOT EXISTS tabela_preco_crossdocking (
    id SERIAL PRIMARY KEY,
    crossdocking_id INTEGER NOT NULL REFERENCES cross_docking(id),
    modelo_id INTEGER NOT NULL REFERENCES modelo_moto(id),
    preco_venda NUMERIC(15, 2) NOT NULL,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE NOT NULL,

    -- Constraint única
    CONSTRAINT uk_crossdocking_modelo_preco UNIQUE (crossdocking_id, modelo_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_tabela_preco_cd_crossdocking ON tabela_preco_crossdocking(crossdocking_id);
CREATE INDEX IF NOT EXISTS idx_tabela_preco_cd_modelo ON tabela_preco_crossdocking(modelo_id);

-- ====================================================================
-- 3. ADICIONAR CAMPOS EM: cliente_moto
-- ====================================================================
DO $$
BEGIN
    -- Adicionar vendedor_id (FK)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='cliente_moto' AND column_name='vendedor_id'
    ) THEN
        ALTER TABLE cliente_moto
        ADD COLUMN vendedor_id INTEGER REFERENCES vendedor_moto(id);

        CREATE INDEX idx_cliente_moto_vendedor ON cliente_moto(vendedor_id);
    END IF;

    -- Adicionar crossdocking (Boolean)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='cliente_moto' AND column_name='crossdocking'
    ) THEN
        ALTER TABLE cliente_moto
        ADD COLUMN crossdocking BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;

    -- Adicionar crossdocking_id (FK)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='cliente_moto' AND column_name='crossdocking_id'
    ) THEN
        ALTER TABLE cliente_moto
        ADD COLUMN crossdocking_id INTEGER REFERENCES cross_docking(id);

        CREATE INDEX idx_cliente_moto_crossdocking ON cliente_moto(crossdocking_id);
    END IF;
END $$;

-- ====================================================================
-- 4. ADICIONAR CAMPOS EM: equipe_vendas_moto
-- ====================================================================
DO $$
BEGIN
    -- Adicionar permitir_prazo
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='equipe_vendas_moto' AND column_name='permitir_prazo'
    ) THEN
        ALTER TABLE equipe_vendas_moto
        ADD COLUMN permitir_prazo BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;

    -- Adicionar permitir_parcelamento
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='equipe_vendas_moto' AND column_name='permitir_parcelamento'
    ) THEN
        ALTER TABLE equipe_vendas_moto
        ADD COLUMN permitir_parcelamento BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;
END $$;

-- ====================================================================
-- 5. ADICIONAR CAMPOS EM: pedido_venda_moto
-- ====================================================================
DO $$
BEGIN
    -- Adicionar prazo_dias
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='pedido_venda_moto' AND column_name='prazo_dias'
    ) THEN
        ALTER TABLE pedido_venda_moto
        ADD COLUMN prazo_dias INTEGER DEFAULT 0 NOT NULL;
    END IF;

    -- Adicionar numero_parcelas
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='pedido_venda_moto' AND column_name='numero_parcelas'
    ) THEN
        ALTER TABLE pedido_venda_moto
        ADD COLUMN numero_parcelas INTEGER DEFAULT 1 NOT NULL;
    END IF;
END $$;



-- ====================================================================
-- 8. VERIFICAÇÃO E VALIDAÇÃO
-- ====================================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Verificar tabelas criadas
    SELECT COUNT(*) INTO v_count
    FROM information_schema.tables
    WHERE table_name IN (
        'cross_docking',
        'tabela_preco_crossdocking',
        'parcela_pedido',
        'parcela_titulo'
    );

    IF v_count = 4 THEN
        RAISE NOTICE '✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!';
        RAISE NOTICE '📊 4 tabelas novas criadas';
        RAISE NOTICE '🔧 Campos adicionados em cliente_moto, equipe_vendas_moto, pedido_venda_moto';
    ELSE
        RAISE WARNING '⚠️  Apenas % de 4 tabelas foram criadas. Verifique!', v_count;
    END IF;
END $$;

-- ====================================================================
-- 9. RESUMO DA MIGRAÇÃO
-- ====================================================================
SELECT
    'Tabelas criadas' AS status,
    COUNT(*) AS quantidade
FROM information_schema.tables
WHERE table_name IN (
    'cross_docking',
    'tabela_preco_crossdocking',
    'parcela_pedido',
    'parcela_titulo'
)
UNION ALL
SELECT
    'Campos em cliente_moto' AS status,
    COUNT(*) AS quantidade
FROM information_schema.columns
WHERE table_name = 'cliente_moto'
AND column_name IN ('vendedor_id', 'crossdocking', 'crossdocking_id')
UNION ALL
SELECT
    'Campos em equipe_vendas_moto' AS status,
    COUNT(*) AS quantidade
FROM information_schema.columns
WHERE table_name = 'equipe_vendas_moto'
AND column_name IN ('permitir_prazo', 'permitir_parcelamento')
UNION ALL
SELECT
    'Campos em pedido_venda_moto' AS status,
    COUNT(*) AS quantidade
FROM information_schema.columns
WHERE table_name = 'pedido_venda_moto'
AND column_name IN ('prazo_dias', 'numero_parcelas');

-- ====================================================================
-- FIM DA MIGRAÇÃO
-- ====================================================================
-- ⚠️  ATENÇÃO:
-- 1. Todos os clientes existentes precisam ter vendedor_id definido
-- 2. Configure as equipes com permitir_prazo e permitir_parcelamento
-- 3. Cadastre os CrossDockings conforme necessário
-- ====================================================================
