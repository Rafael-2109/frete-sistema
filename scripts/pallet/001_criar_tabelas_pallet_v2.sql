-- ============================================================
-- SCRIPT DE CRIAÇÃO DAS TABELAS DO MÓDULO DE PALLETS v2
-- ============================================================
-- Para execução no Render Shell (psql)
--
-- Uso:
--   psql $DATABASE_URL < scripts/pallet/001_criar_tabelas_pallet_v2.sql
--
-- Ou cole diretamente no Render Shell PostgreSQL
--
-- Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
-- IMPLEMENTATION_PLAN.md: Fase 1.2.2
-- ============================================================

-- Início da transação
BEGIN;

-- ============================================================
-- 1. TABELA: pallet_nf_remessa
-- NFs de remessa de pallet emitidas
-- ============================================================
CREATE TABLE IF NOT EXISTS pallet_nf_remessa (
    id SERIAL PRIMARY KEY,

    -- Identificação da NF
    numero_nf VARCHAR(20) NOT NULL,
    serie VARCHAR(5),
    chave_nfe VARCHAR(44) UNIQUE,
    data_emissao TIMESTAMP NOT NULL,

    -- Dados Odoo
    odoo_account_move_id INTEGER,
    odoo_picking_id INTEGER,

    -- Empresa emissora (CD, FB, SC)
    empresa VARCHAR(10) NOT NULL,

    -- Destinatário
    tipo_destinatario VARCHAR(20) NOT NULL,
    cnpj_destinatario VARCHAR(20) NOT NULL,
    nome_destinatario VARCHAR(255),

    -- Transportadora (quando destinatário é CLIENTE)
    cnpj_transportadora VARCHAR(20),
    nome_transportadora VARCHAR(255),

    -- Quantidade e valores
    quantidade INTEGER NOT NULL,
    valor_unitario NUMERIC(15, 2) DEFAULT 35.00,
    valor_total NUMERIC(15, 2),

    -- Vínculo com Embarque
    embarque_id INTEGER REFERENCES embarques(id) ON DELETE SET NULL,
    embarque_item_id INTEGER REFERENCES embarque_itens(id) ON DELETE SET NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'ATIVA' NOT NULL,
    qtd_resolvida INTEGER DEFAULT 0 NOT NULL,

    -- Cancelamento
    cancelada BOOLEAN DEFAULT FALSE NOT NULL,
    cancelada_em TIMESTAMP,
    cancelada_por VARCHAR(100),
    motivo_cancelamento VARCHAR(255),

    -- Referência migração
    movimentacao_estoque_id INTEGER,

    -- Observações
    observacao TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100),

    -- Soft delete
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Índices pallet_nf_remessa
CREATE INDEX IF NOT EXISTS idx_nf_remessa_numero_nf ON pallet_nf_remessa(numero_nf);
CREATE INDEX IF NOT EXISTS idx_nf_remessa_status ON pallet_nf_remessa(status);
CREATE INDEX IF NOT EXISTS idx_nf_remessa_cnpj_destinatario ON pallet_nf_remessa(cnpj_destinatario);
CREATE INDEX IF NOT EXISTS idx_nf_remessa_odoo_account_move_id ON pallet_nf_remessa(odoo_account_move_id);
CREATE INDEX IF NOT EXISTS idx_nf_remessa_empresa_status ON pallet_nf_remessa(empresa, status);
CREATE INDEX IF NOT EXISTS idx_nf_remessa_destinatario_tipo ON pallet_nf_remessa(cnpj_destinatario, tipo_destinatario);
CREATE INDEX IF NOT EXISTS idx_nf_remessa_data_status ON pallet_nf_remessa(data_emissao, status);

-- ============================================================
-- 2. TABELA: pallet_creditos
-- Créditos de pallet a receber
-- ============================================================
CREATE TABLE IF NOT EXISTS pallet_creditos (
    id SERIAL PRIMARY KEY,

    -- Vínculo com NF de remessa
    nf_remessa_id INTEGER NOT NULL REFERENCES pallet_nf_remessa(id) ON DELETE RESTRICT,

    -- Quantidade
    qtd_original INTEGER NOT NULL,
    qtd_saldo INTEGER NOT NULL,

    -- Responsável
    tipo_responsavel VARCHAR(20) NOT NULL,
    cnpj_responsavel VARCHAR(20) NOT NULL,
    nome_responsavel VARCHAR(255),
    uf_responsavel VARCHAR(2),
    cidade_responsavel VARCHAR(100),

    -- Prazo
    prazo_dias INTEGER,
    data_vencimento DATE,

    -- Status
    status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,

    -- Referência migração
    movimentacao_estoque_id INTEGER,

    -- Observações
    observacao TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100),

    -- Soft delete
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Índices pallet_creditos
CREATE INDEX IF NOT EXISTS idx_credito_nf_remessa_id ON pallet_creditos(nf_remessa_id);
CREATE INDEX IF NOT EXISTS idx_credito_status ON pallet_creditos(status);
CREATE INDEX IF NOT EXISTS idx_credito_cnpj_responsavel ON pallet_creditos(cnpj_responsavel);
CREATE INDEX IF NOT EXISTS idx_credito_responsavel_status ON pallet_creditos(cnpj_responsavel, status);
CREATE INDEX IF NOT EXISTS idx_credito_tipo_status ON pallet_creditos(tipo_responsavel, status);
CREATE INDEX IF NOT EXISTS idx_credito_vencimento ON pallet_creditos(data_vencimento, status);

-- ============================================================
-- 3. TABELA: pallet_documentos
-- Documentos de enriquecimento (canhotos, vales)
-- ============================================================
CREATE TABLE IF NOT EXISTS pallet_documentos (
    id SERIAL PRIMARY KEY,

    -- Vínculo com crédito
    credito_id INTEGER NOT NULL REFERENCES pallet_creditos(id) ON DELETE RESTRICT,

    -- Tipo do documento (CANHOTO, VALE_PALLET)
    tipo VARCHAR(20) NOT NULL,

    -- Dados do documento
    numero_documento VARCHAR(50),
    data_emissao DATE,
    data_validade DATE,
    quantidade INTEGER NOT NULL,

    -- Arquivo anexo
    arquivo_path VARCHAR(500),
    arquivo_nome VARCHAR(255),
    arquivo_tipo VARCHAR(50),

    -- Emissor
    cnpj_emissor VARCHAR(20),
    nome_emissor VARCHAR(255),

    -- Recebimento
    recebido BOOLEAN DEFAULT FALSE NOT NULL,
    recebido_em TIMESTAMP,
    recebido_por VARCHAR(100),

    -- Arquivamento físico
    pasta_arquivo VARCHAR(100),
    aba_arquivo VARCHAR(50),

    -- Referência migração
    vale_pallet_id INTEGER,

    -- Observações
    observacao TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100),

    -- Soft delete
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Índices pallet_documentos
CREATE INDEX IF NOT EXISTS idx_documento_credito_id ON pallet_documentos(credito_id);
CREATE INDEX IF NOT EXISTS idx_documento_tipo_recebido ON pallet_documentos(tipo, recebido);
CREATE INDEX IF NOT EXISTS idx_documento_validade ON pallet_documentos(data_validade);
CREATE INDEX IF NOT EXISTS idx_documento_emissor ON pallet_documentos(cnpj_emissor, tipo);

-- ============================================================
-- 4. TABELA: pallet_solucoes
-- Soluções de créditos (baixa, venda, recebimento, substituição)
-- ============================================================
CREATE TABLE IF NOT EXISTS pallet_solucoes (
    id SERIAL PRIMARY KEY,

    -- Vínculo com crédito de origem
    credito_id INTEGER NOT NULL REFERENCES pallet_creditos(id) ON DELETE RESTRICT,

    -- Tipo (BAIXA, VENDA, RECEBIMENTO, SUBSTITUICAO)
    tipo VARCHAR(20) NOT NULL,

    -- Quantidade resolvida
    quantidade INTEGER NOT NULL,

    -- Campos para BAIXA
    motivo_baixa VARCHAR(100),
    confirmado_cliente BOOLEAN,
    data_confirmacao DATE,

    -- Campos para VENDA
    nf_venda VARCHAR(20),
    chave_nfe_venda VARCHAR(44),
    data_venda DATE,
    valor_unitario NUMERIC(15, 2),
    valor_total NUMERIC(15, 2),
    cnpj_comprador VARCHAR(20),
    nome_comprador VARCHAR(255),

    -- Campos para RECEBIMENTO
    data_recebimento DATE,
    local_recebimento VARCHAR(100),
    recebido_de VARCHAR(255),
    cnpj_entregador VARCHAR(20),

    -- Campos para SUBSTITUICAO
    credito_destino_id INTEGER REFERENCES pallet_creditos(id) ON DELETE SET NULL,
    nf_destino VARCHAR(20),
    motivo_substituicao VARCHAR(255),

    -- Responsável genérico
    cnpj_responsavel VARCHAR(20),
    nome_responsavel VARCHAR(255),

    -- Referência migração
    vale_pallet_id INTEGER,

    -- Observações
    observacao TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100),

    -- Soft delete
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Índices pallet_solucoes
CREATE INDEX IF NOT EXISTS idx_solucao_credito_id ON pallet_solucoes(credito_id);
CREATE INDEX IF NOT EXISTS idx_solucao_tipo ON pallet_solucoes(tipo);
CREATE INDEX IF NOT EXISTS idx_solucao_credito_destino_id ON pallet_solucoes(credito_destino_id);
CREATE INDEX IF NOT EXISTS idx_solucao_tipo_data ON pallet_solucoes(tipo, criado_em);
CREATE INDEX IF NOT EXISTS idx_solucao_nf_venda ON pallet_solucoes(nf_venda);
CREATE INDEX IF NOT EXISTS idx_solucao_credito_tipo ON pallet_solucoes(credito_id, tipo);

-- ============================================================
-- 5. TABELA: pallet_nf_solucoes
-- Soluções documentais de NF (devolução, retorno, cancelamento)
-- ============================================================
CREATE TABLE IF NOT EXISTS pallet_nf_solucoes (
    id SERIAL PRIMARY KEY,

    -- Vínculo com NF de remessa
    nf_remessa_id INTEGER NOT NULL REFERENCES pallet_nf_remessa(id) ON DELETE RESTRICT,

    -- Tipo (DEVOLUCAO, RETORNO, CANCELAMENTO)
    tipo VARCHAR(20) NOT NULL,

    -- Quantidade resolvida
    quantidade INTEGER NOT NULL,

    -- Dados da NF de solução
    numero_nf_solucao VARCHAR(20),
    serie_nf_solucao VARCHAR(5),
    chave_nfe_solucao VARCHAR(44) UNIQUE,
    data_nf_solucao TIMESTAMP,

    -- Odoo
    odoo_account_move_id INTEGER,
    odoo_dfe_id INTEGER,

    -- Emitente
    cnpj_emitente VARCHAR(20),
    nome_emitente VARCHAR(255),

    -- Vinculação
    vinculacao VARCHAR(20) DEFAULT 'MANUAL' NOT NULL,

    -- Confirmação
    confirmado BOOLEAN DEFAULT TRUE NOT NULL,
    confirmado_em TIMESTAMP,
    confirmado_por VARCHAR(100),

    -- Rejeição
    rejeitado BOOLEAN DEFAULT FALSE NOT NULL,
    rejeitado_em TIMESTAMP,
    rejeitado_por VARCHAR(100),
    motivo_rejeicao VARCHAR(255),

    -- Info complementar (para match automático)
    info_complementar TEXT,

    -- Observações
    observacao TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100),

    -- Soft delete
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Índices pallet_nf_solucoes
CREATE INDEX IF NOT EXISTS idx_nf_solucao_nf_remessa_id ON pallet_nf_solucoes(nf_remessa_id);
CREATE INDEX IF NOT EXISTS idx_nf_solucao_tipo ON pallet_nf_solucoes(tipo);
CREATE INDEX IF NOT EXISTS idx_nf_solucao_numero_nf ON pallet_nf_solucoes(numero_nf_solucao);
CREATE INDEX IF NOT EXISTS idx_nf_solucao_tipo_vinculacao ON pallet_nf_solucoes(tipo, vinculacao);
CREATE INDEX IF NOT EXISTS idx_nf_solucao_confirmado ON pallet_nf_solucoes(confirmado, vinculacao);
CREATE INDEX IF NOT EXISTS idx_nf_solucao_emitente ON pallet_nf_solucoes(cnpj_emitente, tipo);

-- Commit da transação
COMMIT;

-- ============================================================
-- VERIFICAÇÃO
-- ============================================================
-- Lista todas as tabelas criadas
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'pallet_%'
ORDER BY table_name;

-- ============================================================
-- PRÓXIMO PASSO
-- ============================================================
-- Execute o script de migração de dados:
-- python scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py
-- ============================================================
