-- Migration: Cria tabela vale_pallets
-- Data: 04/01/2026
-- Descrição: Armazena vale pallets emitidos por clientes

CREATE TABLE IF NOT EXISTS vale_pallets (
    id SERIAL PRIMARY KEY,

    -- Referência à NF de remessa/pallet
    nf_pallet VARCHAR(20) NOT NULL,

    -- Dados do vale
    data_emissao DATE NOT NULL,
    data_validade DATE NOT NULL,
    quantidade INTEGER NOT NULL,

    -- Cliente que emitiu o vale
    cnpj_cliente VARCHAR(20),
    nome_cliente VARCHAR(255),

    -- Posse e rastreamento
    posse_atual VARCHAR(50) DEFAULT 'TRANSPORTADORA',
    cnpj_posse VARCHAR(20),
    nome_posse VARCHAR(255),

    -- Transportadora responsável
    cnpj_transportadora VARCHAR(20),
    nome_transportadora VARCHAR(255),

    -- Arquivamento físico
    pasta_arquivo VARCHAR(100),
    aba_arquivo VARCHAR(50),

    -- Resolução
    tipo_resolucao VARCHAR(20) DEFAULT 'PENDENTE',
    responsavel_resolucao VARCHAR(255),
    cnpj_resolucao VARCHAR(20),
    valor_resolucao NUMERIC(15, 2),
    nf_resolucao VARCHAR(20),

    -- Status
    recebido BOOLEAN DEFAULT FALSE,
    recebido_em TIMESTAMP,
    recebido_por VARCHAR(100),

    enviado_coleta BOOLEAN DEFAULT FALSE,
    enviado_coleta_em TIMESTAMP,
    enviado_coleta_por VARCHAR(100),

    resolvido BOOLEAN DEFAULT FALSE,
    resolvido_em TIMESTAMP,
    resolvido_por VARCHAR(100),

    -- Observações
    observacao TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),

    -- Soft delete
    ativo BOOLEAN DEFAULT TRUE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_vale_pallets_nf_pallet ON vale_pallets(nf_pallet);
CREATE INDEX IF NOT EXISTS idx_vale_pallets_cnpj_cliente ON vale_pallets(cnpj_cliente);
CREATE INDEX IF NOT EXISTS idx_vale_pallets_cnpj_transportadora ON vale_pallets(cnpj_transportadora);
CREATE INDEX IF NOT EXISTS idx_vale_pallets_data_validade ON vale_pallets(data_validade);
CREATE INDEX IF NOT EXISTS idx_vale_pallets_resolvido ON vale_pallets(resolvido);
