-- Migration: Criar tabela carvia_fretes + FK frete_id em custos_entrega e cte_complementares
-- Data: 2026-03-21
-- Descricao:
--   1. Tabela carvia_fretes — frete CarVia por (embarque_id, cnpj_emitente, cnpj_destino)
--   2. Campo frete_id em carvia_custos_entrega (equivalente a DespesaExtra.frete_id Nacom)
--   3. Campo frete_id em carvia_cte_complementares
-- Uso: Executar no Render Shell (SQL idempotente)

-- 1. Tabela carvia_fretes
CREATE TABLE IF NOT EXISTS carvia_fretes (
    id SERIAL PRIMARY KEY,

    -- Chaves
    embarque_id INTEGER NOT NULL REFERENCES embarques(id),
    transportadora_id INTEGER NOT NULL REFERENCES transportadoras(id),

    -- Agregacao CNPJ emitente + destino
    cnpj_emitente VARCHAR(20) NOT NULL,
    nome_emitente VARCHAR(255),
    cnpj_destino VARCHAR(20) NOT NULL,
    nome_destino VARCHAR(255),

    -- Rota
    uf_destino VARCHAR(2) NOT NULL,
    cidade_destino VARCHAR(100) NOT NULL,
    tipo_carga VARCHAR(20) NOT NULL,

    -- Totais NFs do grupo
    peso_total FLOAT NOT NULL DEFAULT 0,
    valor_total_nfs FLOAT NOT NULL DEFAULT 0,
    quantidade_nfs INTEGER NOT NULL DEFAULT 0,
    numeros_nfs TEXT,

    -- Snapshot tabela frete (custo — tabela Nacom)
    tabela_nome_tabela VARCHAR(100),
    tabela_valor_kg FLOAT,
    tabela_percentual_valor FLOAT,
    tabela_frete_minimo_valor FLOAT,
    tabela_frete_minimo_peso FLOAT,
    tabela_icms FLOAT,
    tabela_percentual_gris FLOAT,
    tabela_pedagio_por_100kg FLOAT,
    tabela_valor_tas FLOAT,
    tabela_percentual_adv FLOAT,
    tabela_percentual_rca FLOAT,
    tabela_valor_despacho FLOAT,
    tabela_valor_cte FLOAT,
    tabela_icms_incluso BOOLEAN DEFAULT FALSE,
    tabela_icms_destino FLOAT,
    tabela_gris_minimo FLOAT DEFAULT 0,
    tabela_adv_minimo FLOAT DEFAULT 0,
    tabela_icms_proprio FLOAT,

    -- 4 valores CUSTO
    valor_cotado FLOAT NOT NULL DEFAULT 0,
    valor_cte FLOAT,
    valor_considerado FLOAT,
    valor_pago FLOAT,

    -- Valor VENDA
    valor_venda FLOAT,

    -- Vinculacao CUSTO
    subcontrato_id INTEGER REFERENCES carvia_subcontratos(id),
    fatura_transportadora_id INTEGER REFERENCES carvia_faturas_transportadora(id),

    -- Vinculacao VENDA
    operacao_id INTEGER REFERENCES carvia_operacoes(id),
    fatura_cliente_id INTEGER REFERENCES carvia_faturas_cliente(id),

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',

    -- Auditoria
    criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    criado_por VARCHAR(100) NOT NULL,
    observacoes TEXT,

    -- Unique: 1 frete por (embarque, cnpj_emitente, cnpj_destino)
    CONSTRAINT uq_carvia_frete_embarque_cnpj UNIQUE (embarque_id, cnpj_emitente, cnpj_destino)
);

-- Indices
CREATE INDEX IF NOT EXISTS ix_carvia_fretes_embarque ON carvia_fretes (embarque_id);
CREATE INDEX IF NOT EXISTS ix_carvia_fretes_cnpj_emitente ON carvia_fretes (cnpj_emitente);
CREATE INDEX IF NOT EXISTS ix_carvia_fretes_cnpj_destino ON carvia_fretes (cnpj_destino);
CREATE INDEX IF NOT EXISTS ix_carvia_fretes_status ON carvia_fretes (status);
CREATE INDEX IF NOT EXISTS ix_carvia_fretes_subcontrato ON carvia_fretes (subcontrato_id) WHERE subcontrato_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_carvia_fretes_operacao ON carvia_fretes (operacao_id) WHERE operacao_id IS NOT NULL;

-- 2. FK frete_id em carvia_custos_entrega
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_custos_entrega' AND column_name = 'frete_id'
    ) THEN
        ALTER TABLE carvia_custos_entrega ADD COLUMN frete_id INTEGER REFERENCES carvia_fretes(id);
        CREATE INDEX ix_carvia_custos_entrega_frete ON carvia_custos_entrega (frete_id) WHERE frete_id IS NOT NULL;
    END IF;
END $$;

-- 3. FK frete_id em carvia_cte_complementares
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cte_complementares' AND column_name = 'frete_id'
    ) THEN
        ALTER TABLE carvia_cte_complementares ADD COLUMN frete_id INTEGER REFERENCES carvia_fretes(id);
        CREATE INDEX ix_carvia_cte_comp_frete ON carvia_cte_complementares (frete_id) WHERE frete_id IS NOT NULL;
    END IF;
END $$;
