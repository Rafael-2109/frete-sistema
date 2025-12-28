-- ==============================================
-- SCRIPT SQL PARA CRIAR TABELAS DE CUSTEIO
-- Executar no Shell do Render
-- ==============================================

-- Tabela: custo_mensal
-- Historico de custos mensais por produto
CREATE TABLE IF NOT EXISTS custo_mensal (
    id SERIAL PRIMARY KEY,

    -- Periodo de referencia
    mes INTEGER NOT NULL,
    ano INTEGER NOT NULL,

    -- Produto
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    tipo_produto VARCHAR(20) NOT NULL,

    -- Custos calculados
    custo_liquido_medio NUMERIC(15, 6),
    custo_medio_estoque NUMERIC(15, 6),
    ultimo_custo NUMERIC(15, 6),
    custo_bom NUMERIC(15, 6),

    -- Estoque inicial
    qtd_estoque_inicial NUMERIC(15, 3) DEFAULT 0,
    custo_estoque_inicial NUMERIC(15, 2) DEFAULT 0,

    -- Compras do mes
    qtd_comprada NUMERIC(15, 3) DEFAULT 0,
    valor_compras_bruto NUMERIC(15, 2) DEFAULT 0,
    valor_icms NUMERIC(15, 2) DEFAULT 0,
    valor_pis NUMERIC(15, 2) DEFAULT 0,
    valor_cofins NUMERIC(15, 2) DEFAULT 0,
    valor_compras_liquido NUMERIC(15, 2) DEFAULT 0,

    -- Producao
    qtd_produzida NUMERIC(15, 3) DEFAULT 0,
    custo_producao NUMERIC(15, 2) DEFAULT 0,

    -- Consumo/Vendas
    qtd_consumida NUMERIC(15, 3) DEFAULT 0,
    qtd_vendida NUMERIC(15, 3) DEFAULT 0,

    -- Estoque final
    qtd_estoque_final NUMERIC(15, 3) DEFAULT 0,
    custo_estoque_final NUMERIC(15, 2) DEFAULT 0,

    -- Controle
    status VARCHAR(20) DEFAULT 'ABERTO' NOT NULL,
    fechado_em TIMESTAMP,
    fechado_por VARCHAR(100),

    -- Auditoria
    criado_em TIMESTAMP DEFAULT NOW() NOT NULL,
    atualizado_em TIMESTAMP DEFAULT NOW(),

    -- Constraint unica
    CONSTRAINT uq_custo_mensal_periodo_produto UNIQUE (mes, ano, cod_produto)
);

-- Indices para custo_mensal
CREATE INDEX IF NOT EXISTS idx_custo_mensal_periodo ON custo_mensal(ano, mes);
CREATE INDEX IF NOT EXISTS idx_custo_mensal_tipo ON custo_mensal(tipo_produto);
CREATE INDEX IF NOT EXISTS idx_custo_mensal_produto ON custo_mensal(cod_produto);
CREATE INDEX IF NOT EXISTS idx_custo_mensal_status ON custo_mensal(status);

-- Tabela: custo_considerado
-- Custo vigente para cada produto
CREATE TABLE IF NOT EXISTS custo_considerado (
    id SERIAL PRIMARY KEY,

    -- Produto (unico)
    cod_produto VARCHAR(50) NOT NULL UNIQUE,
    nome_produto VARCHAR(255),
    tipo_produto VARCHAR(20) NOT NULL,

    -- Tipos de custo disponiveis
    custo_medio_mes NUMERIC(15, 6),
    ultimo_custo NUMERIC(15, 6),
    custo_medio_estoque NUMERIC(15, 6),
    custo_bom NUMERIC(15, 6),

    -- Custo considerado (selecionado)
    tipo_custo_selecionado VARCHAR(20) DEFAULT 'MEDIO_MES' NOT NULL,
    custo_considerado NUMERIC(15, 6),

    -- Posicao de estoque
    qtd_estoque_inicial NUMERIC(15, 3) DEFAULT 0,
    custo_estoque_inicial NUMERIC(15, 2) DEFAULT 0,
    qtd_comprada_periodo NUMERIC(15, 3) DEFAULT 0,
    custo_compras_periodo NUMERIC(15, 2) DEFAULT 0,
    qtd_estoque_final NUMERIC(15, 3) DEFAULT 0,
    custo_estoque_final NUMERIC(15, 2) DEFAULT 0,

    -- Referencia ao ultimo fechamento
    ultimo_mes_fechado INTEGER,
    ultimo_ano_fechado INTEGER,

    -- Auditoria
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

-- Indices para custo_considerado
CREATE INDEX IF NOT EXISTS idx_custo_considerado_tipo ON custo_considerado(tipo_produto);
CREATE INDEX IF NOT EXISTS idx_custo_considerado_produto ON custo_considerado(cod_produto);

-- Verificar criacao
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('custo_mensal', 'custo_considerado')
ORDER BY table_name;
