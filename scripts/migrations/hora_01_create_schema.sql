-- Migration HORA 01: Cria schema inicial do modulo Lojas Motochefe (13 tabelas hora_*)
-- Data: 2026-04-18
-- Descricao:
--   Schema inicial do modulo HORA conforme plano de primeiros principios.
--   Ver docs/hora/INVARIANTES.md para contrato de design.
--   Ver app/hora/CLAUDE.md para convencoes do modulo.
-- Idempotente: todas as tabelas criadas com IF NOT EXISTS.
-- RISCO: baixo. Somente CREATE TABLE + indices. Nao altera dados existentes.
-- Ordem respeita dependencias de FK.

-- ============================================================================
-- 1. hora_loja (cadastro, sem FK)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_loja (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(20) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    endereco VARCHAR(255),
    cidade VARCHAR(100),
    uf VARCHAR(2),
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    atualizado_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_loja_cnpj ON hora_loja (cnpj);

-- ============================================================================
-- 2. hora_modelo (cadastro, sem FK)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_modelo (
    id SERIAL PRIMARY KEY,
    nome_modelo VARCHAR(100) NOT NULL UNIQUE,
    potencia_motor VARCHAR(50),
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    atualizado_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_modelo_nome ON hora_modelo (nome_modelo);

-- ============================================================================
-- 3. hora_tabela_preco (FK hora_modelo)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_tabela_preco (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL REFERENCES hora_modelo(id),
    preco_tabela NUMERIC(15, 2) NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS ix_hora_tabela_preco_modelo_id ON hora_tabela_preco (modelo_id);
CREATE INDEX IF NOT EXISTS ix_hora_tabela_preco_vigencia ON hora_tabela_preco (modelo_id, vigencia_inicio);

-- ============================================================================
-- 4. hora_moto (IDENTIDADE IMUTAVEL - insert-once)
--    INVARIANTE 3: nenhuma coluna mutavel aqui (sem status, sem loja, sem preco).
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_moto (
    numero_chassi VARCHAR(30) PRIMARY KEY,
    modelo_id INTEGER NOT NULL REFERENCES hora_modelo(id),
    cor VARCHAR(50) NOT NULL,
    numero_motor VARCHAR(50) UNIQUE,
    ano_modelo INTEGER,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    criado_por VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_hora_moto_modelo_id ON hora_moto (modelo_id);

-- ============================================================================
-- 5. hora_pedido (sem FK, header)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_pedido (
    id SERIAL PRIMARY KEY,
    numero_pedido VARCHAR(50) NOT NULL UNIQUE,
    cnpj_destino VARCHAR(20) NOT NULL,
    data_pedido DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTO',
    arquivo_origem_s3_key VARCHAR(500),
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_pedido_numero ON hora_pedido (numero_pedido);
CREATE INDEX IF NOT EXISTS ix_hora_pedido_cnpj_destino ON hora_pedido (cnpj_destino);
CREATE INDEX IF NOT EXISTS ix_hora_pedido_status ON hora_pedido (status);

-- ============================================================================
-- 6. hora_pedido_item (FK hora_pedido, hora_moto, hora_modelo)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_pedido_item (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES hora_pedido(id),
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    modelo_id INTEGER REFERENCES hora_modelo(id),
    cor VARCHAR(50),
    preco_compra_esperado NUMERIC(15, 2) NOT NULL,
    CONSTRAINT uq_hora_pedido_item_chassi UNIQUE (pedido_id, numero_chassi)
);
CREATE INDEX IF NOT EXISTS ix_hora_pedido_item_pedido_id ON hora_pedido_item (pedido_id);
CREATE INDEX IF NOT EXISTS ix_hora_pedido_item_chassi ON hora_pedido_item (numero_chassi);

-- ============================================================================
-- 7. hora_nf_entrada (FK hora_pedido NULLABLE)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_nf_entrada (
    id SERIAL PRIMARY KEY,
    chave_44 VARCHAR(44) NOT NULL UNIQUE,
    numero_nf VARCHAR(20) NOT NULL,
    serie_nf VARCHAR(10),
    cnpj_emitente VARCHAR(20) NOT NULL,
    nome_emitente VARCHAR(200),
    cnpj_destinatario VARCHAR(20) NOT NULL,
    data_emissao DATE NOT NULL,
    valor_total NUMERIC(15, 2) NOT NULL,
    arquivo_pdf_s3_key VARCHAR(500),
    arquivo_xml_s3_key VARCHAR(500),
    pedido_id INTEGER REFERENCES hora_pedido(id),
    parseada_em TIMESTAMP,
    parser_usado VARCHAR(50),
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_chave_44 ON hora_nf_entrada (chave_44);
CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_cnpj_emitente ON hora_nf_entrada (cnpj_emitente);
CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_cnpj_destinatario ON hora_nf_entrada (cnpj_destinatario);
CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_pedido_id ON hora_nf_entrada (pedido_id);

-- ============================================================================
-- 8. hora_nf_entrada_item (FK hora_nf_entrada, hora_moto)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_nf_entrada_item (
    id SERIAL PRIMARY KEY,
    nf_id INTEGER NOT NULL REFERENCES hora_nf_entrada(id),
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    preco_real NUMERIC(15, 2) NOT NULL,
    modelo_texto_original VARCHAR(255),
    cor_texto_original VARCHAR(100),
    numero_motor_texto_original VARCHAR(100),
    CONSTRAINT uq_hora_nf_entrada_item_chassi UNIQUE (nf_id, numero_chassi)
);
CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_item_nf_id ON hora_nf_entrada_item (nf_id);
CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_item_chassi ON hora_nf_entrada_item (numero_chassi);

-- ============================================================================
-- 9. hora_recebimento (FK hora_nf_entrada, hora_loja)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_recebimento (
    id SERIAL PRIMARY KEY,
    nf_id INTEGER NOT NULL REFERENCES hora_nf_entrada(id),
    loja_id INTEGER NOT NULL REFERENCES hora_loja(id),
    data_recebimento DATE NOT NULL,
    operador VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'EM_CONFERENCIA',
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    atualizado_em TIMESTAMP,
    CONSTRAINT uq_hora_recebimento_nf_loja UNIQUE (nf_id, loja_id)
);
CREATE INDEX IF NOT EXISTS ix_hora_recebimento_nf_id ON hora_recebimento (nf_id);
CREATE INDEX IF NOT EXISTS ix_hora_recebimento_loja_id ON hora_recebimento (loja_id);
CREATE INDEX IF NOT EXISTS ix_hora_recebimento_status ON hora_recebimento (status);

-- ============================================================================
-- 10. hora_recebimento_conferencia (FK hora_recebimento, hora_moto)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_recebimento_conferencia (
    id SERIAL PRIMARY KEY,
    recebimento_id INTEGER NOT NULL REFERENCES hora_recebimento(id),
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    conferido_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    qr_code_lido BOOLEAN NOT NULL DEFAULT FALSE,
    foto_s3_key VARCHAR(500),
    tipo_divergencia VARCHAR(30),
    detalhe_divergencia TEXT,
    operador VARCHAR(100),
    CONSTRAINT uq_hora_recebimento_conferencia_chassi UNIQUE (recebimento_id, numero_chassi)
);
CREATE INDEX IF NOT EXISTS ix_hora_recebimento_conferencia_recebimento_id
    ON hora_recebimento_conferencia (recebimento_id);
CREATE INDEX IF NOT EXISTS ix_hora_recebimento_conferencia_chassi
    ON hora_recebimento_conferencia (numero_chassi);
CREATE INDEX IF NOT EXISTS ix_hora_recebimento_conferencia_divergencia
    ON hora_recebimento_conferencia (tipo_divergencia);

-- ============================================================================
-- 11. hora_venda (FK hora_loja)
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_venda (
    id SERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES hora_loja(id),
    cpf_cliente VARCHAR(14) NOT NULL,
    nome_cliente VARCHAR(200) NOT NULL,
    telefone_cliente VARCHAR(20),
    email_cliente VARCHAR(120),
    data_venda DATE NOT NULL,
    forma_pagamento VARCHAR(20) NOT NULL,
    valor_total NUMERIC(15, 2) NOT NULL,
    nf_saida_numero VARCHAR(20),
    nf_saida_chave_44 VARCHAR(44) UNIQUE,
    nf_saida_emitida_em TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'CONCLUIDA',
    vendedor VARCHAR(100),
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    atualizado_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_venda_loja_id ON hora_venda (loja_id);
CREATE INDEX IF NOT EXISTS ix_hora_venda_cpf_cliente ON hora_venda (cpf_cliente);
CREATE INDEX IF NOT EXISTS ix_hora_venda_data_venda ON hora_venda (data_venda);
CREATE INDEX IF NOT EXISTS ix_hora_venda_nf_saida_numero ON hora_venda (nf_saida_numero);
CREATE INDEX IF NOT EXISTS ix_hora_venda_status ON hora_venda (status);

-- ============================================================================
-- 12. hora_venda_item (FK hora_venda, hora_moto, hora_tabela_preco)
--     UNIQUE em numero_chassi: impede venda dupla estruturalmente.
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_venda_item (
    id SERIAL PRIMARY KEY,
    venda_id INTEGER NOT NULL REFERENCES hora_venda(id),
    numero_chassi VARCHAR(30) NOT NULL UNIQUE REFERENCES hora_moto(numero_chassi),
    tabela_preco_id INTEGER REFERENCES hora_tabela_preco(id),
    preco_tabela_referencia NUMERIC(15, 2) NOT NULL,
    desconto_aplicado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    preco_final NUMERIC(15, 2) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_hora_venda_item_venda_id ON hora_venda_item (venda_id);
CREATE INDEX IF NOT EXISTS ix_hora_venda_item_chassi ON hora_venda_item (numero_chassi);

-- ============================================================================
-- 13. hora_moto_evento (FK hora_moto, hora_loja) — log append-only
-- ============================================================================
CREATE TABLE IF NOT EXISTS hora_moto_evento (
    id SERIAL PRIMARY KEY,
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    tipo VARCHAR(20) NOT NULL,
    origem_tabela VARCHAR(50),
    origem_id INTEGER,
    loja_id INTEGER REFERENCES hora_loja(id),
    operador VARCHAR(100),
    detalhe TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS ix_hora_moto_evento_chassi ON hora_moto_evento (numero_chassi);
CREATE INDEX IF NOT EXISTS ix_hora_moto_evento_tipo ON hora_moto_evento (tipo);
CREATE INDEX IF NOT EXISTS ix_hora_moto_evento_loja_id ON hora_moto_evento (loja_id);
CREATE INDEX IF NOT EXISTS ix_hora_moto_evento_timestamp ON hora_moto_evento (timestamp);
CREATE INDEX IF NOT EXISTS ix_hora_moto_evento_chassi_timestamp
    ON hora_moto_evento (numero_chassi, timestamp);
