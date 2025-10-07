-- ================================================================================
-- MIGRATION: Refatoração Financeira MotoCHEFE
-- Para: Render (PostgreSQL)
-- Data: 2025-01-10
--
-- ATENÇÃO: Execute este script no shell do Render via copy/paste
-- ================================================================================

BEGIN;

-- ================================================================================
-- 1. ALTERAR TABELA: empresa_venda_moto
-- ================================================================================

-- Alterar cnpj_empresa para nullable (para MargemSogima)
ALTER TABLE empresa_venda_moto ALTER COLUMN cnpj_empresa DROP NOT NULL;

-- Adicionar novos campos
ALTER TABLE empresa_venda_moto ADD COLUMN IF NOT EXISTS baixa_compra_auto BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE empresa_venda_moto ADD COLUMN IF NOT EXISTS saldo NUMERIC(15, 2) DEFAULT 0 NOT NULL;
ALTER TABLE empresa_venda_moto ADD COLUMN IF NOT EXISTS tipo_conta VARCHAR(20);

-- Adicionar comentários
COMMENT ON COLUMN empresa_venda_moto.baixa_compra_auto IS 'TRUE: Ao receber, paga motos automaticamente (FIFO)';
COMMENT ON COLUMN empresa_venda_moto.saldo IS 'Saldo atual da conta';
COMMENT ON COLUMN empresa_venda_moto.tipo_conta IS 'Valores: FABRICANTE, OPERACIONAL, MARGEM_SOGIMA';

-- ================================================================================
-- 2. ALTERAR TABELA: titulo_financeiro
-- ================================================================================

-- Adicionar novos campos
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS numero_chassi VARCHAR(30);
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS tipo_titulo VARCHAR(20);
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS ordem_pagamento INTEGER;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS empresa_recebedora_id INTEGER;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS valor_original NUMERIC(15, 2);
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS valor_saldo NUMERIC(15, 2);
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS valor_pago_total NUMERIC(15, 2) DEFAULT 0;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS data_emissao DATE DEFAULT CURRENT_DATE;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS data_ultimo_pagamento DATE;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS titulo_pai_id INTEGER;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS eh_titulo_dividido BOOLEAN DEFAULT FALSE;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS historico_divisao TEXT;
ALTER TABLE titulo_financeiro ADD COLUMN IF NOT EXISTS criado_por VARCHAR(100);

-- Migrar dados antigos para novos campos (títulos existentes)
UPDATE titulo_financeiro SET
    tipo_titulo = 'VENDA',  -- Padrão para títulos antigos
    ordem_pagamento = 4,
    valor_original = valor_parcela,
    valor_saldo = valor_parcela - COALESCE(valor_recebido, 0),
    valor_pago_total = COALESCE(valor_recebido, 0),
    data_emissao = criado_em::date
WHERE tipo_titulo IS NULL;

-- Tornar NOT NULL após migração (somente se tiver dados)
DO $$
BEGIN
    -- Só altera para NOT NULL se todos os registros tiverem valor
    IF NOT EXISTS (SELECT 1 FROM titulo_financeiro WHERE tipo_titulo IS NULL) THEN
        ALTER TABLE titulo_financeiro ALTER COLUMN tipo_titulo SET NOT NULL;
        ALTER TABLE titulo_financeiro ALTER COLUMN ordem_pagamento SET NOT NULL;
        ALTER TABLE titulo_financeiro ALTER COLUMN valor_original SET NOT NULL;
        ALTER TABLE titulo_financeiro ALTER COLUMN valor_saldo SET NOT NULL;
        ALTER TABLE titulo_financeiro ALTER COLUMN data_emissao SET NOT NULL;
    END IF;
END $$;

-- Adicionar FKs (com proteção para não duplicar)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_titulo_numero_chassi') THEN
        ALTER TABLE titulo_financeiro ADD CONSTRAINT fk_titulo_numero_chassi
            FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_titulo_empresa_recebedora') THEN
        ALTER TABLE titulo_financeiro ADD CONSTRAINT fk_titulo_empresa_recebedora
            FOREIGN KEY (empresa_recebedora_id) REFERENCES empresa_venda_moto(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_titulo_pai') THEN
        ALTER TABLE titulo_financeiro ADD CONSTRAINT fk_titulo_pai
            FOREIGN KEY (titulo_pai_id) REFERENCES titulo_financeiro(id);
    END IF;
END $$;

-- Adicionar índices
CREATE INDEX IF NOT EXISTS idx_titulo_chassi ON titulo_financeiro(numero_chassi);
CREATE INDEX IF NOT EXISTS idx_titulo_tipo ON titulo_financeiro(tipo_titulo);
CREATE INDEX IF NOT EXISTS idx_titulo_empresa_rec ON titulo_financeiro(empresa_recebedora_id);

-- ================================================================================
-- 3. ALTERAR TABELA: comissao_vendedor
-- ================================================================================

ALTER TABLE comissao_vendedor ADD COLUMN IF NOT EXISTS numero_chassi VARCHAR(30);

-- Adicionar FK com proteção
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_comissao_chassi') THEN
        ALTER TABLE comissao_vendedor ADD CONSTRAINT fk_comissao_chassi
            FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_comissao_chassi ON comissao_vendedor(numero_chassi);

-- ================================================================================
-- 4. CRIAR TABELA: movimentacao_financeira
-- ================================================================================

CREATE TABLE IF NOT EXISTS movimentacao_financeira (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    valor NUMERIC(15, 2) NOT NULL,
    data_movimentacao DATE NOT NULL,

    -- Origem
    empresa_origem_id INTEGER,
    origem_tipo VARCHAR(50),
    origem_identificacao VARCHAR(255),

    -- Destino
    empresa_destino_id INTEGER,
    destino_tipo VARCHAR(50),
    destino_identificacao VARCHAR(255),

    -- Relacionamentos
    pedido_id INTEGER,
    numero_chassi VARCHAR(30),
    titulo_financeiro_id INTEGER,
    comissao_vendedor_id INTEGER,
    embarque_moto_id INTEGER,
    despesa_mensal_id INTEGER,

    -- Complementares
    descricao TEXT,
    numero_nf VARCHAR(20),
    numero_documento VARCHAR(50),
    observacoes TEXT,

    -- Controle
    eh_baixa_automatica BOOLEAN DEFAULT FALSE,
    movimentacao_origem_id INTEGER,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100),

    -- Constraints
    FOREIGN KEY (empresa_origem_id) REFERENCES empresa_venda_moto(id),
    FOREIGN KEY (empresa_destino_id) REFERENCES empresa_venda_moto(id),
    FOREIGN KEY (pedido_id) REFERENCES pedido_venda_moto(id),
    FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi),
    FOREIGN KEY (titulo_financeiro_id) REFERENCES titulo_financeiro(id),
    FOREIGN KEY (comissao_vendedor_id) REFERENCES comissao_vendedor(id),
    FOREIGN KEY (embarque_moto_id) REFERENCES embarque_moto(id),
    FOREIGN KEY (despesa_mensal_id) REFERENCES despesa_mensal(id),
    FOREIGN KEY (movimentacao_origem_id) REFERENCES movimentacao_financeira(id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_movfin_tipo ON movimentacao_financeira(tipo);
CREATE INDEX IF NOT EXISTS idx_movfin_categoria ON movimentacao_financeira(categoria);
CREATE INDEX IF NOT EXISTS idx_movfin_data ON movimentacao_financeira(data_movimentacao);
CREATE INDEX IF NOT EXISTS idx_movfin_emp_origem ON movimentacao_financeira(empresa_origem_id);
CREATE INDEX IF NOT EXISTS idx_movfin_emp_destino ON movimentacao_financeira(empresa_destino_id);
CREATE INDEX IF NOT EXISTS idx_movfin_pedido ON movimentacao_financeira(pedido_id);
CREATE INDEX IF NOT EXISTS idx_movfin_chassi ON movimentacao_financeira(numero_chassi);
CREATE INDEX IF NOT EXISTS idx_movfin_titulo ON movimentacao_financeira(titulo_financeiro_id);

-- ================================================================================
-- 5. CRIAR TABELA: titulo_a_pagar
-- ================================================================================

CREATE TABLE IF NOT EXISTS titulo_a_pagar (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,

    -- Origem
    titulo_financeiro_id INTEGER NOT NULL,
    pedido_id INTEGER NOT NULL,
    numero_chassi VARCHAR(30) NOT NULL,

    -- Beneficiário
    empresa_destino_id INTEGER,
    fornecedor_montagem VARCHAR(100),

    -- Valores
    valor_original NUMERIC(15, 2) NOT NULL,
    valor_pago NUMERIC(15, 2) DEFAULT 0,
    valor_saldo NUMERIC(15, 2) NOT NULL,

    -- Datas
    data_criacao DATE NOT NULL DEFAULT CURRENT_DATE,
    data_liberacao DATE,
    data_vencimento DATE,
    data_pagamento DATE,

    -- Status
    status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,

    -- Controle
    observacoes TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) DEFAULT 'SISTEMA',
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),

    -- Constraints
    FOREIGN KEY (titulo_financeiro_id) REFERENCES titulo_financeiro(id),
    FOREIGN KEY (pedido_id) REFERENCES pedido_venda_moto(id),
    FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi),
    FOREIGN KEY (empresa_destino_id) REFERENCES empresa_venda_moto(id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_titpagar_tipo ON titulo_a_pagar(tipo);
CREATE INDEX IF NOT EXISTS idx_titpagar_status ON titulo_a_pagar(status);
CREATE INDEX IF NOT EXISTS idx_titpagar_titulo ON titulo_a_pagar(titulo_financeiro_id);
CREATE INDEX IF NOT EXISTS idx_titpagar_pedido ON titulo_a_pagar(pedido_id);
CREATE INDEX IF NOT EXISTS idx_titpagar_chassi ON titulo_a_pagar(numero_chassi);

-- ================================================================================
-- 6. POPULAR: MargemSogima
-- ================================================================================

INSERT INTO empresa_venda_moto (
    cnpj_empresa,
    empresa,
    chave_pix,
    banco,
    cod_banco,
    agencia,
    conta,
    baixa_compra_auto,
    saldo,
    tipo_conta,
    ativo,
    criado_em,
    criado_por,
    atualizado_em,
    atualizado_por
)
SELECT
    NULL,                    -- cnpj_empresa (nullable para MargemSogima)
    'MargemSogima',          -- empresa
    NULL,                    -- chave_pix
    NULL,                    -- banco
    NULL,                    -- cod_banco
    NULL,                    -- agencia
    NULL,                    -- conta
    FALSE,                   -- baixa_compra_auto
    0,                       -- saldo
    'MARGEM_SOGIMA',         -- tipo_conta
    TRUE,                    -- ativo
    CURRENT_TIMESTAMP,       -- criado_em
    'SISTEMA',               -- criado_por
    NULL,                    -- atualizado_em
    NULL                     -- atualizado_por
WHERE NOT EXISTS (
    SELECT 1 FROM empresa_venda_moto WHERE tipo_conta = 'MARGEM_SOGIMA'
);

-- ================================================================================
-- 7. CLEANUP (OPCIONAL - remover campos antigos após validação)
-- ================================================================================

-- NÃO execute estas linhas agora! Apenas após validar que tudo funciona:
-- ALTER TABLE titulo_financeiro DROP COLUMN IF EXISTS valor_parcela;
-- ALTER TABLE titulo_financeiro DROP COLUMN IF EXISTS total_parcelas;
-- ALTER TABLE titulo_financeiro DROP COLUMN IF EXISTS data_recebimento;
-- ALTER TABLE titulo_financeiro DROP COLUMN IF EXISTS valor_recebido;

COMMIT;

-- ================================================================================
-- FIM DA MIGRATION - Refatoração Financeira MotoCHEFE
-- ================================================================================
