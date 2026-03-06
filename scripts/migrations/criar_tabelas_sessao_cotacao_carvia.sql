-- Migration: Criar tabelas carvia_sessoes_cotacao e carvia_sessao_demandas
-- Sessao de cotacao CarVia — ferramenta comercial para cotar frete subcontratado
-- Executar via Render Shell (SQL idempotente)

-- 1. Tabela pai: sessoes de cotacao
CREATE TABLE IF NOT EXISTS carvia_sessoes_cotacao (
    id SERIAL PRIMARY KEY,
    numero_sessao VARCHAR(20) NOT NULL,
    nome_sessao VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
    valor_contra_proposta NUMERIC(15, 2),
    resposta_cliente_obs TEXT,
    respondido_em TIMESTAMP,
    respondido_por VARCHAR(100),
    enviado_em TIMESTAMP,
    enviado_por VARCHAR(100),
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Check constraint (idempotente via DO block)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'ck_carvia_sessao_status'
    ) THEN
        ALTER TABLE carvia_sessoes_cotacao
            ADD CONSTRAINT ck_carvia_sessao_status
            CHECK (status IN ('RASCUNHO', 'ENVIADO', 'APROVADO', 'CONTRA_PROPOSTA', 'CANCELADO'));
    END IF;
END $$;

-- Indices
CREATE INDEX IF NOT EXISTS ix_carvia_sessao_numero ON carvia_sessoes_cotacao (numero_sessao);
CREATE INDEX IF NOT EXISTS ix_carvia_sessao_status ON carvia_sessoes_cotacao (status);
CREATE INDEX IF NOT EXISTS ix_carvia_sessao_criado_em ON carvia_sessoes_cotacao (criado_em);


-- 2. Tabela filha: demandas por sessao
CREATE TABLE IF NOT EXISTS carvia_sessao_demandas (
    id SERIAL PRIMARY KEY,
    sessao_id INTEGER NOT NULL REFERENCES carvia_sessoes_cotacao(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL DEFAULT 1,
    origem_empresa VARCHAR(255) NOT NULL,
    origem_uf VARCHAR(2) NOT NULL,
    origem_cidade VARCHAR(100) NOT NULL,
    destino_empresa VARCHAR(255) NOT NULL,
    destino_uf VARCHAR(2) NOT NULL,
    destino_cidade VARCHAR(100) NOT NULL,
    tipo_carga VARCHAR(100),
    peso NUMERIC(15, 3) NOT NULL,
    valor_mercadoria NUMERIC(15, 2) NOT NULL,
    volume INTEGER,
    data_coleta DATE,
    data_entrega_prevista DATE,
    data_agendamento DATE,
    transportadora_id INTEGER REFERENCES transportadoras(id),
    tabela_frete_id INTEGER REFERENCES tabelas_frete(id),
    valor_frete_calculado NUMERIC(15, 2),
    detalhes_calculo JSON,
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint (idempotente via DO block)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_carvia_sessao_demanda_ordem'
    ) THEN
        ALTER TABLE carvia_sessao_demandas
            ADD CONSTRAINT uq_carvia_sessao_demanda_ordem
            UNIQUE (sessao_id, ordem);
    END IF;
END $$;

-- Indices
CREATE INDEX IF NOT EXISTS ix_carvia_sessao_demanda_sessao ON carvia_sessao_demandas (sessao_id);
CREATE INDEX IF NOT EXISTS ix_carvia_sessao_demanda_destino_uf ON carvia_sessao_demandas (destino_uf);
