-- Script SQL para Render Shell
-- FASE 1: Sistema de Gestao de Devolucoes
-- Criado em: 30/12/2024

-- =====================================================================
-- 1. Adicionar campo teve_devolucao em entregas_monitoradas
-- =====================================================================
ALTER TABLE entregas_monitoradas
ADD COLUMN IF NOT EXISTS teve_devolucao BOOLEAN DEFAULT FALSE NOT NULL;

-- =====================================================================
-- 2. Criar tabela nf_devolucao
-- =====================================================================
CREATE TABLE IF NOT EXISTS nf_devolucao (
    id SERIAL PRIMARY KEY,
    entrega_monitorada_id INTEGER REFERENCES entregas_monitoradas(id),

    -- Dados do registro inicial
    numero_nfd VARCHAR(20) NOT NULL,
    data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motivo VARCHAR(50) NOT NULL,
    descricao_motivo TEXT,
    numero_nf_venda VARCHAR(20),

    -- Dados do DFe Odoo
    odoo_dfe_id INTEGER UNIQUE,
    odoo_ativo BOOLEAN,
    odoo_name VARCHAR(100),
    odoo_status_codigo VARCHAR(10),
    odoo_status_descricao VARCHAR(100),

    -- Chave de acesso e dados fiscais
    chave_nfd VARCHAR(44) UNIQUE,
    serie_nfd VARCHAR(10),
    data_emissao DATE,
    data_entrada DATE,

    -- Valores
    valor_total NUMERIC(15, 2),
    valor_produtos NUMERIC(15, 2),

    -- Cliente/Emitente
    cnpj_emitente VARCHAR(20),
    nome_emitente VARCHAR(255),
    ie_emitente VARCHAR(20),

    -- Destinatario
    cnpj_destinatario VARCHAR(20),
    nome_destinatario VARCHAR(255),

    -- Arquivos
    nfd_xml_path VARCHAR(500),
    nfd_xml_nome_arquivo VARCHAR(255),
    nfd_pdf_path VARCHAR(500),
    nfd_pdf_nome_arquivo VARCHAR(255),

    -- Controle
    sincronizado_odoo BOOLEAN DEFAULT FALSE NOT NULL,
    data_sincronizacao TIMESTAMP,
    status VARCHAR(30) DEFAULT 'REGISTRADA' NOT NULL,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nfd_numero ON nf_devolucao(numero_nfd);
CREATE INDEX IF NOT EXISTS idx_nfd_entrega ON nf_devolucao(entrega_monitorada_id);
CREATE INDEX IF NOT EXISTS idx_nfd_status ON nf_devolucao(status);
CREATE INDEX IF NOT EXISTS idx_nfd_cnpj_emitente ON nf_devolucao(cnpj_emitente);
CREATE INDEX IF NOT EXISTS idx_nfd_nf_venda ON nf_devolucao(numero_nf_venda);
CREATE INDEX IF NOT EXISTS idx_nfd_odoo_dfe ON nf_devolucao(odoo_dfe_id);
CREATE INDEX IF NOT EXISTS idx_nfd_chave ON nf_devolucao(chave_nfd);
CREATE INDEX IF NOT EXISTS idx_nfd_ativo ON nf_devolucao(ativo);

-- =====================================================================
-- 3. Criar tabela nf_devolucao_linha
-- =====================================================================
CREATE TABLE IF NOT EXISTS nf_devolucao_linha (
    id SERIAL PRIMARY KEY,
    nf_devolucao_id INTEGER NOT NULL REFERENCES nf_devolucao(id) ON DELETE CASCADE,

    -- Codigo do produto (do cliente)
    codigo_produto_cliente VARCHAR(50),
    descricao_produto_cliente VARCHAR(255),

    -- Codigo interno (resolvido)
    codigo_produto_interno VARCHAR(50),
    descricao_produto_interno VARCHAR(255),
    produto_resolvido BOOLEAN DEFAULT FALSE NOT NULL,
    metodo_resolucao VARCHAR(20),

    -- Quantidades
    quantidade NUMERIC(15, 3),
    unidade_medida VARCHAR(20),
    valor_unitario NUMERIC(15, 4),
    valor_total NUMERIC(15, 2),

    -- Peso
    peso_bruto NUMERIC(15, 3),
    peso_liquido NUMERIC(15, 3),

    -- Dados fiscais
    cfop VARCHAR(10),
    ncm VARCHAR(20),
    numero_item INTEGER,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nfd_linha_nfd ON nf_devolucao_linha(nf_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_nfd_linha_cod_cliente ON nf_devolucao_linha(codigo_produto_cliente);
CREATE INDEX IF NOT EXISTS idx_nfd_linha_cod_interno ON nf_devolucao_linha(codigo_produto_interno);
CREATE INDEX IF NOT EXISTS idx_nfd_linha_resolvido ON nf_devolucao_linha(produto_resolvido);

-- =====================================================================
-- 4. Criar tabela ocorrencia_devolucao
-- =====================================================================
CREATE TABLE IF NOT EXISTS ocorrencia_devolucao (
    id SERIAL PRIMARY KEY,
    nf_devolucao_id INTEGER NOT NULL UNIQUE REFERENCES nf_devolucao(id) ON DELETE CASCADE,
    numero_ocorrencia VARCHAR(20) NOT NULL UNIQUE,

    -- Secao Logistica
    destino VARCHAR(20) DEFAULT 'INDEFINIDO' NOT NULL,
    localizacao_atual VARCHAR(20) DEFAULT 'CLIENTE' NOT NULL,
    transportadora_retorno_id INTEGER REFERENCES transportadoras(id),
    transportadora_retorno_nome VARCHAR(255),
    data_previsao_retorno DATE,
    data_chegada_cd TIMESTAMP,
    recebido_por VARCHAR(100),
    observacoes_logistica TEXT,

    -- Secao Comercial
    categoria VARCHAR(30),
    subcategoria VARCHAR(50),
    descricao_comercial TEXT,
    responsavel VARCHAR(30) DEFAULT 'INDEFINIDO',
    status VARCHAR(30) DEFAULT 'ABERTA' NOT NULL,
    origem VARCHAR(30) DEFAULT 'INDEFINIDO',
    autorizado_por VARCHAR(100),
    resolvido_por VARCHAR(100),
    desfecho TEXT,

    -- Timestamps
    data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_acao_comercial TIMESTAMP,
    data_resolucao TIMESTAMP,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ocorrencia_nfd ON ocorrencia_devolucao(nf_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_ocorrencia_numero ON ocorrencia_devolucao(numero_ocorrencia);
CREATE INDEX IF NOT EXISTS idx_ocorrencia_status ON ocorrencia_devolucao(status);
CREATE INDEX IF NOT EXISTS idx_ocorrencia_destino ON ocorrencia_devolucao(destino);
CREATE INDEX IF NOT EXISTS idx_ocorrencia_categoria ON ocorrencia_devolucao(categoria);
CREATE INDEX IF NOT EXISTS idx_ocorrencia_ativo ON ocorrencia_devolucao(ativo);

-- =====================================================================
-- 5. Criar tabela frete_devolucao
-- =====================================================================
CREATE TABLE IF NOT EXISTS frete_devolucao (
    id SERIAL PRIMARY KEY,
    ocorrencia_devolucao_id INTEGER REFERENCES ocorrencia_devolucao(id),
    despesa_extra_id INTEGER REFERENCES despesas_extras(id),

    -- Transportadora
    transportadora_id INTEGER REFERENCES transportadoras(id),
    transportadora_nome VARCHAR(255) NOT NULL,
    cnpj_transportadora VARCHAR(20),

    -- Valores
    valor_cotado NUMERIC(15, 2) NOT NULL,
    valor_negociado NUMERIC(15, 2),
    peso_kg NUMERIC(15, 3),

    -- Datas
    data_cotacao DATE NOT NULL,
    data_coleta_prevista DATE,
    data_coleta_realizada DATE,
    data_entrega_prevista DATE,
    data_entrega_realizada DATE,

    -- Rota
    uf_origem VARCHAR(2),
    cidade_origem VARCHAR(100),
    uf_destino VARCHAR(2),
    cidade_destino VARCHAR(100),

    -- Status
    status VARCHAR(20) DEFAULT 'COTADO' NOT NULL,

    -- CTe retorno
    numero_cte VARCHAR(20),
    chave_cte VARCHAR(44),

    -- Observacoes
    observacoes TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_frete_dev_ocorrencia ON frete_devolucao(ocorrencia_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_frete_dev_despesa ON frete_devolucao(despesa_extra_id);
CREATE INDEX IF NOT EXISTS idx_frete_dev_status ON frete_devolucao(status);
CREATE INDEX IF NOT EXISTS idx_frete_dev_transportadora ON frete_devolucao(transportadora_id);
CREATE INDEX IF NOT EXISTS idx_frete_dev_chave_cte ON frete_devolucao(chave_cte);

-- =====================================================================
-- 6. Criar tabela contagem_devolucao
-- =====================================================================
CREATE TABLE IF NOT EXISTS contagem_devolucao (
    id SERIAL PRIMARY KEY,
    nf_devolucao_linha_id INTEGER NOT NULL UNIQUE REFERENCES nf_devolucao_linha(id) ON DELETE CASCADE,

    -- Quantidades conforme
    caixas_conforme INTEGER DEFAULT 0 NOT NULL,
    unidades_conforme INTEGER DEFAULT 0 NOT NULL,

    -- Quantidades nao conforme
    caixas_nao_conforme INTEGER DEFAULT 0 NOT NULL,
    unidades_nao_conforme INTEGER DEFAULT 0 NOT NULL,

    -- Calculados
    caixas_faltantes INTEGER DEFAULT 0 NOT NULL,
    unidades_faltantes INTEGER DEFAULT 0 NOT NULL,

    -- Comentarios
    comentario_contagem TEXT,
    comentario_qualidade TEXT,

    -- Qualidade
    status_qualidade VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,
    destino_produto VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,

    -- Controle
    data_contagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    conferente VARCHAR(100) NOT NULL,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_contagem_linha ON contagem_devolucao(nf_devolucao_linha_id);
CREATE INDEX IF NOT EXISTS idx_contagem_status ON contagem_devolucao(status_qualidade);
CREATE INDEX IF NOT EXISTS idx_contagem_destino ON contagem_devolucao(destino_produto);

-- =====================================================================
-- 7. Criar tabela anexo_ocorrencia
-- =====================================================================
CREATE TABLE IF NOT EXISTS anexo_ocorrencia (
    id SERIAL PRIMARY KEY,
    ocorrencia_devolucao_id INTEGER REFERENCES ocorrencia_devolucao(id) ON DELETE CASCADE,
    contagem_devolucao_id INTEGER REFERENCES contagem_devolucao(id) ON DELETE CASCADE,

    -- Tipo
    tipo VARCHAR(20) NOT NULL,

    -- Dados do arquivo
    nome_original VARCHAR(255) NOT NULL,
    nome_arquivo VARCHAR(255) NOT NULL,
    caminho_s3 VARCHAR(500) NOT NULL,
    tamanho_bytes INTEGER,
    content_type VARCHAR(100),

    -- Metadados email
    email_remetente VARCHAR(255),
    email_assunto VARCHAR(500),
    email_data_envio TIMESTAMP,
    email_preview TEXT,

    -- Descricao
    descricao TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,

    -- Constraint: deve ter pelo menos um vinculo
    CONSTRAINT ck_anexo_vinculo CHECK (
        ocorrencia_devolucao_id IS NOT NULL OR contagem_devolucao_id IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_anexo_ocorrencia ON anexo_ocorrencia(ocorrencia_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_anexo_contagem ON anexo_ocorrencia(contagem_devolucao_id);
CREATE INDEX IF NOT EXISTS idx_anexo_tipo ON anexo_ocorrencia(tipo);
CREATE INDEX IF NOT EXISTS idx_anexo_ativo ON anexo_ocorrencia(ativo);

-- =====================================================================
-- 8. Criar tabela depara_produto_cliente
-- =====================================================================
CREATE TABLE IF NOT EXISTS depara_produto_cliente (
    id SERIAL PRIMARY KEY,

    -- Prefixo CNPJ
    prefixo_cnpj VARCHAR(8) NOT NULL,
    nome_grupo VARCHAR(255),

    -- Mapeamento
    codigo_cliente VARCHAR(50) NOT NULL,
    descricao_cliente VARCHAR(255),
    nosso_codigo VARCHAR(50) NOT NULL,
    descricao_nosso VARCHAR(255),

    -- Conversao
    fator_conversao NUMERIC(10, 4) DEFAULT 1.0 NOT NULL,
    unidade_medida_cliente VARCHAR(20),
    unidade_medida_nosso VARCHAR(20),

    -- Observacoes
    observacoes TEXT,

    -- Controle
    ativo BOOLEAN DEFAULT TRUE NOT NULL,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),

    -- Constraint unica
    CONSTRAINT uq_depara_prefixo_codigo UNIQUE (prefixo_cnpj, codigo_cliente)
);

CREATE INDEX IF NOT EXISTS idx_depara_prefixo ON depara_produto_cliente(prefixo_cnpj);
CREATE INDEX IF NOT EXISTS idx_depara_cod_cliente ON depara_produto_cliente(codigo_cliente);
CREATE INDEX IF NOT EXISTS idx_depara_nosso_codigo ON depara_produto_cliente(nosso_codigo);
CREATE INDEX IF NOT EXISTS idx_depara_ativo ON depara_produto_cliente(ativo);
