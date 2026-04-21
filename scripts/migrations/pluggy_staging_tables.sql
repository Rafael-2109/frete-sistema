-- ============================================================================
-- Migration: Pluggy Staging Tables (Fase 1)
-- Data: 2026-04-21
-- Objetivo: Criar tabelas staging para Pluggy Open Finance sem tocar em
--           pessoal_transacoes/pessoal_contas. Permite validar dados do
--           Pluggy antes de migrar para o modelo final.
--
-- Execucao: idempotente via IF NOT EXISTS. Seguro para Render Shell.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. pessoal_pluggy_items — conexoes criadas via widget Pluggy Connect
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pessoal_pluggy_items (
    id SERIAL PRIMARY KEY,
    pluggy_item_id VARCHAR(50) NOT NULL UNIQUE,
    client_user_id VARCHAR(20) NOT NULL,
    connector_id INTEGER NOT NULL,
    connector_name VARCHAR(100),
    status VARCHAR(30) NOT NULL,
    execution_status VARCHAR(50),
    consent_expires_at TIMESTAMP,
    ultimo_sync TIMESTAMP,
    ultimo_webhook_em TIMESTAMP,
    erro_mensagem TEXT,
    payload_raw JSONB,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pessoal_pluggy_items_user
    ON pessoal_pluggy_items(client_user_id);
CREATE INDEX IF NOT EXISTS idx_pessoal_pluggy_items_status
    ON pessoal_pluggy_items(status);

COMMENT ON TABLE pessoal_pluggy_items IS
    'Conexoes Pluggy Open Finance. 1 item = 1 banco conectado via OAuth/consent.';
COMMENT ON COLUMN pessoal_pluggy_items.client_user_id IS
    'str(User.id) — vinculo ao usuario autorizado via USUARIOS_PESSOAL, nao e FK.';
COMMENT ON COLUMN pessoal_pluggy_items.status IS
    'UPDATING | UPDATED | LOGIN_ERROR | OUTDATED | WAITING_USER_INPUT';

-- ----------------------------------------------------------------------------
-- 2. pessoal_pluggy_accounts — contas retornadas pelo item
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pessoal_pluggy_accounts (
    id SERIAL PRIMARY KEY,
    pluggy_item_pk INTEGER NOT NULL REFERENCES pessoal_pluggy_items(id) ON DELETE CASCADE,
    pluggy_account_id VARCHAR(50) NOT NULL UNIQUE,
    type VARCHAR(10) NOT NULL,
    subtype VARCHAR(30),
    number VARCHAR(50),
    name VARCHAR(200),
    marketing_name VARCHAR(200),
    owner_name VARCHAR(200),
    tax_number VARCHAR(30),
    balance NUMERIC(15,2),
    currency_code VARCHAR(3) DEFAULT 'BRL',
    bank_data JSONB,
    credit_data JSONB,
    payload_raw JSONB,
    -- Vinculo pos-aprovacao (Fase 4)
    conta_pessoal_id INTEGER REFERENCES pessoal_contas(id) ON DELETE SET NULL,
    conta_vinculada_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pessoal_pluggy_accounts_item
    ON pessoal_pluggy_accounts(pluggy_item_pk);
CREATE INDEX IF NOT EXISTS idx_pessoal_pluggy_accounts_conta
    ON pessoal_pluggy_accounts(conta_pessoal_id);
CREATE INDEX IF NOT EXISTS idx_pessoal_pluggy_accounts_type
    ON pessoal_pluggy_accounts(type);

COMMENT ON TABLE pessoal_pluggy_accounts IS
    'Contas Pluggy (BANK conta corrente/poupanca ou CREDIT cartao de credito).';
COMMENT ON COLUMN pessoal_pluggy_accounts.number IS
    'BANK: "AGENCIA/CONTA-DIG" (ex 0001/12345-0). CREDIT: 4 ultimos digitos.';
COMMENT ON COLUMN pessoal_pluggy_accounts.balance IS
    'BANK: saldo conta. CREDIT: saldo devedor (nao mapear para Transacao.saldo).';

-- ----------------------------------------------------------------------------
-- 3. pessoal_pluggy_transacoes_stg — transacoes fieis ao payload
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pessoal_pluggy_transacoes_stg (
    id SERIAL PRIMARY KEY,
    pluggy_account_pk INTEGER NOT NULL REFERENCES pessoal_pluggy_accounts(id) ON DELETE CASCADE,
    pluggy_transaction_id VARCHAR(64) NOT NULL UNIQUE,
    -- Core (fiel ao payload)
    date TIMESTAMP NOT NULL,
    description VARCHAR(500),
    description_raw VARCHAR(500),
    amount NUMERIC(15,2) NOT NULL,
    amount_in_account_currency NUMERIC(15,2),
    currency_code VARCHAR(3),
    balance NUMERIC(15,2),
    category VARCHAR(100),
    category_id VARCHAR(20),
    category_translated VARCHAR(100),
    provider_code VARCHAR(100),
    provider_id VARCHAR(100),
    type VARCHAR(10),
    status VARCHAR(20),
    operation_type VARCHAR(30),
    -- Nested (flexivel)
    payment_data JSONB,
    credit_card_metadata JSONB,
    merchant JSONB,
    payload_raw JSONB NOT NULL,
    -- Controle do staging
    visto_em_sync_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_processamento VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    -- Vinculo pos-migracao (Fase 4)
    transacao_pessoal_id INTEGER REFERENCES pessoal_transacoes(id) ON DELETE SET NULL,
    migrado_em TIMESTAMP,
    observacao_migracao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_pluggy_stg_status_proc CHECK (
        status_processamento IN ('PENDENTE', 'DRY_RUN', 'APROVADO', 'MIGRADO', 'REPROVADO', 'IGNORAR')
    )
);

CREATE INDEX IF NOT EXISTS idx_pluggy_stg_account
    ON pessoal_pluggy_transacoes_stg(pluggy_account_pk);
CREATE INDEX IF NOT EXISTS idx_pluggy_stg_date
    ON pessoal_pluggy_transacoes_stg(date);
CREATE INDEX IF NOT EXISTS idx_pluggy_stg_status
    ON pessoal_pluggy_transacoes_stg(status);
CREATE INDEX IF NOT EXISTS idx_pluggy_stg_status_proc
    ON pessoal_pluggy_transacoes_stg(status_processamento);
CREATE INDEX IF NOT EXISTS idx_pluggy_stg_transacao
    ON pessoal_pluggy_transacoes_stg(transacao_pessoal_id)
    WHERE transacao_pessoal_id IS NOT NULL;

COMMENT ON TABLE pessoal_pluggy_transacoes_stg IS
    'Staging de transacoes Pluggy. Recebe dados fieis ao payload, sem mapear para PessoalTransacao.';
COMMENT ON COLUMN pessoal_pluggy_transacoes_stg.amount IS
    'Signed. BANK: +entrada/-saida. CREDIT_CARD: +compra/-estorno (INVERSO). Adapter resolve em Fase 4.';
COMMENT ON COLUMN pessoal_pluggy_transacoes_stg.status_processamento IS
    'PENDENTE (recem-sync) -> DRY_RUN (simulado) -> APROVADO|REPROVADO|IGNORAR -> MIGRADO';

-- ----------------------------------------------------------------------------
-- 4. pessoal_pluggy_categorias_map — mapeamento Pluggy categoryId -> PessoalCategoria
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pessoal_pluggy_categorias_map (
    id SERIAL PRIMARY KEY,
    pluggy_category_id VARCHAR(20) NOT NULL UNIQUE,
    pluggy_category_description VARCHAR(100),
    pluggy_category_translated VARCHAR(100),
    pluggy_parent_id VARCHAR(20),
    pessoal_categoria_id INTEGER REFERENCES pessoal_categorias(id) ON DELETE SET NULL,
    confianca NUMERIC(5,2) DEFAULT 100,
    origem VARCHAR(20) DEFAULT 'manual',
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_pluggy_cat_map_origem CHECK (
        origem IN ('manual', 'sugerida', 'aprovada', 'semente')
    )
);

CREATE INDEX IF NOT EXISTS idx_pluggy_cat_map_pessoal
    ON pessoal_pluggy_categorias_map(pessoal_categoria_id);
CREATE INDEX IF NOT EXISTS idx_pluggy_cat_map_parent
    ON pessoal_pluggy_categorias_map(pluggy_parent_id);

COMMENT ON TABLE pessoal_pluggy_categorias_map IS
    'Mapeia categoryId hierarquico Pluggy (ex 05080000=Transfer-TED) para PessoalCategoria local.';
