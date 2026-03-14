-- Migration: Criar tabelas de CTE Complementar e Custo Entrega (CarVia)
-- Executar no Render Shell (SQL idempotente)
-- Dependencias: carvia_operacoes, carvia_faturas_cliente

-- 1. CTe Complementares (referenciada por custos_entrega)
CREATE TABLE IF NOT EXISTS carvia_cte_complementares (
    id SERIAL PRIMARY KEY,
    numero_comp VARCHAR(20) NOT NULL,
    operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
    fatura_cliente_id INTEGER REFERENCES carvia_faturas_cliente(id),
    cte_numero VARCHAR(20),
    cte_chave_acesso VARCHAR(44) UNIQUE,
    cte_valor NUMERIC(15,2) NOT NULL,
    cte_xml_path VARCHAR(500),
    cte_xml_nome_arquivo VARCHAR(255),
    cte_data_emissao DATE,
    cnpj_cliente VARCHAR(20),
    nome_cliente VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
    observacoes TEXT,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- 2. Custos de Entrega
CREATE TABLE IF NOT EXISTS carvia_custos_entrega (
    id SERIAL PRIMARY KEY,
    numero_custo VARCHAR(20) NOT NULL,
    operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
    cte_complementar_id INTEGER REFERENCES carvia_cte_complementares(id),
    tipo_custo VARCHAR(50) NOT NULL,
    descricao VARCHAR(500),
    valor NUMERIC(15,2) NOT NULL,
    data_custo DATE NOT NULL,
    data_vencimento DATE,
    fornecedor_nome VARCHAR(255),
    fornecedor_cnpj VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    pago_por VARCHAR(100),
    pago_em TIMESTAMP,
    total_conciliado NUMERIC(15,2) NOT NULL DEFAULT 0,
    conciliado BOOLEAN NOT NULL DEFAULT FALSE,
    observacoes TEXT,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- 3. Anexos dos Custos de Entrega
CREATE TABLE IF NOT EXISTS carvia_custo_entrega_anexos (
    id SERIAL PRIMARY KEY,
    custo_entrega_id INTEGER NOT NULL REFERENCES carvia_custos_entrega(id) ON DELETE CASCADE,
    nome_original VARCHAR(255) NOT NULL,
    nome_arquivo VARCHAR(255) NOT NULL,
    caminho_s3 VARCHAR(500) NOT NULL,
    tamanho_bytes INTEGER,
    content_type VARCHAR(100),
    descricao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Indices: carvia_cte_complementares
CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_numero_comp ON carvia_cte_complementares(numero_comp);
CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_operacao_id ON carvia_cte_complementares(operacao_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_fatura_cliente_id ON carvia_cte_complementares(fatura_cliente_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_cte_numero ON carvia_cte_complementares(cte_numero);
CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_cnpj_cliente ON carvia_cte_complementares(cnpj_cliente);
CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_status ON carvia_cte_complementares(status);

-- Indices: carvia_custos_entrega
CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_numero_custo ON carvia_custos_entrega(numero_custo);
CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_operacao_id ON carvia_custos_entrega(operacao_id);
CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_cte_comp_id ON carvia_custos_entrega(cte_complementar_id);
CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_tipo_custo ON carvia_custos_entrega(tipo_custo);
CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_status ON carvia_custos_entrega(status);

-- Indices: carvia_custo_entrega_anexos
CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_anexo_custo_id ON carvia_custo_entrega_anexos(custo_entrega_id);
CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_anexo_ativo ON carvia_custo_entrega_anexos(ativo);
