-- Motos Assaí — Schema completo (16 tabelas)
-- Idempotente; safe para re-execução.

-- ===== Cadastros =====

CREATE TABLE IF NOT EXISTS assai_cd (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(80) NOT NULL UNIQUE,
    cnpj VARCHAR(14),
    endereco VARCHAR(255),
    bairro VARCHAR(80),
    cep VARCHAR(10),
    cidade VARCHAR(80),
    uf CHAR(2),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_loja (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(120) NOT NULL,
    razao_social VARCHAR(200) NOT NULL,
    cnpj VARCHAR(18) NOT NULL,
    ie VARCHAR(20),
    endereco VARCHAR(255),
    bairro VARCHAR(80),
    cep VARCHAR(10),
    cidade VARCHAR(80),
    uf CHAR(2),
    regional VARCHAR(80),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);
CREATE INDEX IF NOT EXISTS ix_assai_loja_cnpj ON assai_loja(cnpj);

CREATE TABLE IF NOT EXISTS assai_modelo (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nome VARCHAR(80) NOT NULL,
    descricao_qpa VARCHAR(200),
    codigo_qpa VARCHAR(20),
    regex_chassi VARCHAR(120),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);
CREATE INDEX IF NOT EXISTS ix_assai_modelo_codigo_qpa ON assai_modelo(codigo_qpa);

CREATE TABLE IF NOT EXISTS assai_modelo_alias (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id) ON DELETE CASCADE,
    alias VARCHAR(120) NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (tipo, alias)
);
CREATE INDEX IF NOT EXISTS ix_assai_modelo_alias_modelo ON assai_modelo_alias(modelo_id);

-- ===== Identidade da moto =====

CREATE TABLE IF NOT EXISTS assai_moto (
    id SERIAL PRIMARY KEY,
    chassi VARCHAR(50) NOT NULL UNIQUE,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    cor VARCHAR(40),
    motor VARCHAR(50),
    ano INTEGER,
    criada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_moto_evento (
    id SERIAL PRIMARY KEY,
    chassi VARCHAR(50) NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    ocorrido_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    operador_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    dados_extras JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_assai_moto_evento_chassi ON assai_moto_evento(chassi);
CREATE INDEX IF NOT EXISTS ix_assai_moto_evento_chassi_ocorrido ON assai_moto_evento(chassi, ocorrido_em DESC);

-- ===== Pipeline pedido → compra → recibo =====

CREATE TABLE IF NOT EXISTS assai_pedido_venda (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(40) NOT NULL UNIQUE,
    data_emissao DATE,
    previsao_entrega DATE,
    fornecedor_cnpj VARCHAR(18),
    pdf_s3_key VARCHAR(500),
    parser_usado VARCHAR(30),
    parsing_confianca NUMERIC(3,2),
    status VARCHAR(30) NOT NULL DEFAULT 'ABERTO',
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_pedido_venda_item (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id) ON DELETE CASCADE,
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    qtd_pedida INTEGER NOT NULL,
    valor_unitario NUMERIC(12,2) NOT NULL,
    valor_total NUMERIC(14,2) NOT NULL,
    UNIQUE (pedido_id, loja_id, modelo_id)
);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_item_loja ON assai_pedido_venda_item(loja_id);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_item_modelo ON assai_pedido_venda_item(modelo_id);

CREATE TABLE IF NOT EXISTS assai_compra_motochefe (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(30) NOT NULL UNIQUE,
    data_emissao DATE,
    motochefe_cnpj VARCHAR(18),
    status VARCHAR(30) NOT NULL DEFAULT 'ABERTA',
    criada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_compra_motochefe_pedido (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES assai_compra_motochefe(id) ON DELETE CASCADE,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id) ON DELETE CASCADE,
    UNIQUE (compra_id, pedido_id)
);

CREATE TABLE IF NOT EXISTS assai_recibo_motochefe (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES assai_compra_motochefe(id) ON DELETE CASCADE,
    numero_recibo VARCHAR(40),
    data_recibo DATE,
    equipe VARCHAR(80),
    conferente_motochefe VARCHAR(80),
    total_motos_declarado INTEGER,
    doc_s3_key VARCHAR(500),
    tipo_documento VARCHAR(10),
    parser_usado VARCHAR(30),
    parsing_confianca NUMERIC(3,2),
    status VARCHAR(40) NOT NULL DEFAULT 'RECEBIDO_AGUARDANDO_CONFERENCIA',
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);
CREATE INDEX IF NOT EXISTS ix_assai_recibo_compra ON assai_recibo_motochefe(compra_id);

CREATE TABLE IF NOT EXISTS assai_recibo_item (
    id SERIAL PRIMARY KEY,
    recibo_id INTEGER NOT NULL REFERENCES assai_recibo_motochefe(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_texto_recibo VARCHAR(120),
    modelo_id INTEGER REFERENCES assai_modelo(id),
    cor_texto VARCHAR(40),
    motor VARCHAR(50),
    conferido BOOLEAN NOT NULL DEFAULT FALSE,
    tipo_divergencia VARCHAR(30),
    qr_code_lido BOOLEAN NOT NULL DEFAULT FALSE,
    foto_s3_key VARCHAR(500)
);
CREATE INDEX IF NOT EXISTS ix_assai_recibo_item_recibo ON assai_recibo_item(recibo_id);
CREATE INDEX IF NOT EXISTS ix_assai_recibo_item_chassi ON assai_recibo_item(chassi);
CREATE UNIQUE INDEX IF NOT EXISTS ux_assai_recibo_item_recibo_chassi ON assai_recibo_item(recibo_id, chassi);

-- ===== Separação e faturamento =====

CREATE TABLE IF NOT EXISTS assai_separacao (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    status VARCHAR(20) NOT NULL DEFAULT 'EM_SEPARACAO',
    iniciada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    fechada_em TIMESTAMP,
    fechada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    solicitacao_excel_s3_key VARCHAR(500),
    motivo_cancelamento TEXT
);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_pedido ON assai_separacao(pedido_id);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_loja ON assai_separacao(loja_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_assai_separacao_pedido_loja_ativa
    ON assai_separacao(pedido_id, loja_id)
    WHERE status <> 'CANCELADA';

CREATE TABLE IF NOT EXISTS assai_separacao_item (
    id SERIAL PRIMARY KEY,
    separacao_id INTEGER NOT NULL REFERENCES assai_separacao(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    valor_unitario_qpa NUMERIC(12,2) NOT NULL,
    registrada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    registrada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_item_separacao ON assai_separacao_item(separacao_id);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_item_chassi ON assai_separacao_item(chassi);

CREATE TABLE IF NOT EXISTS assai_nf_qpa (
    id SERIAL PRIMARY KEY,
    separacao_id INTEGER REFERENCES assai_separacao(id) ON DELETE SET NULL,
    chave_44 VARCHAR(44) NOT NULL UNIQUE,
    numero VARCHAR(20),
    serie VARCHAR(10),
    emitente_cnpj VARCHAR(18),
    destinatario_cnpj VARCHAR(18),
    destinatario_nome VARCHAR(200),
    loja_id INTEGER REFERENCES assai_loja(id),
    valor_total NUMERIC(14,2),
    data_emissao DATE,
    pdf_s3_key VARCHAR(500),
    status_match VARCHAR(20) NOT NULL DEFAULT 'NAO_RECONCILIADO',
    importada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    importada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_loja ON assai_nf_qpa(loja_id);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_separacao ON assai_nf_qpa(separacao_id);

CREATE TABLE IF NOT EXISTS assai_nf_qpa_item (
    id SERIAL PRIMARY KEY,
    nf_id INTEGER NOT NULL REFERENCES assai_nf_qpa(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_extraido VARCHAR(120),
    valor_extraido NUMERIC(12,2),
    separacao_item_id INTEGER REFERENCES assai_separacao_item(id) ON DELETE SET NULL,
    tipo_divergencia VARCHAR(30)
);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_nf ON assai_nf_qpa_item(nf_id);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_chassi ON assai_nf_qpa_item(chassi);
