-- Migration 34: Estoque de Pecas + Pendencia categorizada (Spec 1 — back-end).
--
-- 6 tabelas novas. Sem CHECK (validacao por set Python no service, molde
-- Divergencia/Compra). Ordem de criacao evita FK pendente: peca -> peca_modelo
-- -> peca_compra -> pendencia -> peca_compra_item -> estoque_movimento.
-- (pendencia NAO referencia estoque_movimento nem compra_item -> sem ciclo.)
--
-- Convencao de deploy (padrao 30/32/33): aplicar manualmente em prod+local;
-- NAO consta no build.sh; arquivo versionado so como registro do DDL.

BEGIN;

-- 4.1 catalogo de pecas
CREATE TABLE IF NOT EXISTS assai_peca (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(40),
    nome VARCHAR(120) NOT NULL,
    custo_referencia NUMERIC(15,4),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    dados_extras JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_assai_peca_codigo ON assai_peca(codigo);

-- 4.2 compatibilidade N:N peca x modelo
CREATE TABLE IF NOT EXISTS assai_peca_modelo (
    id SERIAL PRIMARY KEY,
    peca_id INTEGER NOT NULL REFERENCES assai_peca(id) ON DELETE CASCADE,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id) ON DELETE CASCADE,
    CONSTRAINT uq_assai_peca_modelo UNIQUE (peca_id, modelo_id)
);

-- 4.5 pedido de compra (cabecalho)
CREATE TABLE IF NOT EXISTS assai_peca_compra (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(20) NOT NULL UNIQUE,
    tipo VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ABERTA',
    fornecedor VARCHAR(120) NOT NULL DEFAULT 'MOTOCHEFE',
    criada_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    dados_extras JSONB DEFAULT '{}'::jsonb
);

-- 4.3 ficha de pendencia categorizada
CREATE TABLE IF NOT EXISTS assai_pendencia (
    id SERIAL PRIMARY KEY,
    chassi VARCHAR(50) NOT NULL,
    categoria VARCHAR(20) NOT NULL,
    origem VARCHAR(20) NOT NULL,
    tratativa VARCHAR(40),
    fase VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
    retorno_fisico BOOLEAN NOT NULL DEFAULT FALSE,
    descricao TEXT NOT NULL,
    pendencia_pai_id INTEGER REFERENCES assai_pendencia(id) ON DELETE SET NULL,
    evento_pendente_id INTEGER REFERENCES assai_moto_evento(id) ON DELETE SET NULL,
    peca_id INTEGER REFERENCES assai_peca(id) ON DELETE SET NULL,
    chassi_doador VARCHAR(50),
    devolucao_item_id INTEGER REFERENCES assai_devolucao_item(id) ON DELETE SET NULL,
    pos_venda_ocorrencia_id INTEGER REFERENCES assai_pos_venda_ocorrencia(id) ON DELETE SET NULL,
    divergencia_origem_id INTEGER REFERENCES assai_divergencia(id) ON DELETE SET NULL,
    detalhes JSONB DEFAULT '{}'::jsonb,
    aberta_em TIMESTAMP NOT NULL DEFAULT NOW(),
    aberta_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    resolvida_em TIMESTAMP,
    resolvida_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    resolucao_descricao TEXT,
    cancelada_em TIMESTAMP,
    cancelada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_assai_pendencia_chassi ON assai_pendencia(chassi);
CREATE INDEX IF NOT EXISTS ix_assai_pendencia_aberta
    ON assai_pendencia(chassi)
    WHERE resolvida_em IS NULL AND cancelada_em IS NULL;

-- 4.6 itens do pedido de compra
CREATE TABLE IF NOT EXISTS assai_peca_compra_item (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES assai_peca_compra(id) ON DELETE CASCADE,
    peca_id INTEGER NOT NULL REFERENCES assai_peca(id) ON DELETE RESTRICT,
    quantidade NUMERIC(15,3) NOT NULL,
    quantidade_recebida NUMERIC(15,3) NOT NULL DEFAULT 0,
    custo_estimado NUMERIC(15,4),
    pendencia_id INTEGER REFERENCES assai_pendencia(id) ON DELETE SET NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_assai_peca_compra_item_compra ON assai_peca_compra_item(compra_id);

-- 4.4 ledger append-only de estoque
CREATE TABLE IF NOT EXISTS assai_estoque_movimento (
    id BIGSERIAL PRIMARY KEY,
    peca_id INTEGER NOT NULL REFERENCES assai_peca(id) ON DELETE RESTRICT,
    tipo VARCHAR(40) NOT NULL,
    quantidade NUMERIC(15,3) NOT NULL,
    delta_almoxarifado NUMERIC(15,3) NOT NULL DEFAULT 0,
    chassi_origem VARCHAR(50),
    chassi_destino VARCHAR(50),
    pendencia_id INTEGER REFERENCES assai_pendencia(id) ON DELETE SET NULL,
    compra_item_id INTEGER REFERENCES assai_peca_compra_item(id) ON DELETE SET NULL,
    custo_unitario NUMERIC(15,4),
    custo_total NUMERIC(15,2),
    receita_unitaria NUMERIC(15,4),
    receita_total NUMERIC(15,2),
    operador_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    ocorrido_em TIMESTAMP NOT NULL DEFAULT NOW(),
    observacao TEXT,
    dados_extras JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_peca ON assai_estoque_movimento(peca_id);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_chassi_origem ON assai_estoque_movimento(chassi_origem);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_chassi_destino ON assai_estoque_movimento(chassi_destino);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_pendencia ON assai_estoque_movimento(pendencia_id);

COMMIT;
