-- ============================================================================
-- Migration: Adicionar campos Pluggy em PessoalTransacao e PessoalConta
-- Data: 2026-04-21
-- Fase: 4 (preparacao para merge staging -> PessoalTransacao)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PessoalConta — vinculo com conta Pluggy
-- ----------------------------------------------------------------------------
ALTER TABLE pessoal_contas
    ADD COLUMN IF NOT EXISTS pluggy_account_id VARCHAR(50) UNIQUE,
    ADD COLUMN IF NOT EXISTS pluggy_item_pk INTEGER REFERENCES pessoal_pluggy_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_pessoal_contas_pluggy_item
    ON pessoal_contas(pluggy_item_pk);

COMMENT ON COLUMN pessoal_contas.pluggy_account_id IS
    'ID Pluggy da conta. UNIQUE para evitar vincular 2 contas locais ao mesmo pluggy_account.';

-- ----------------------------------------------------------------------------
-- PessoalTransacao — metadados Pluggy + origem
-- ----------------------------------------------------------------------------
ALTER TABLE pessoal_transacoes
    ADD COLUMN IF NOT EXISTS pluggy_transaction_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS origem_import VARCHAR(20) NOT NULL DEFAULT 'csv',
    ADD COLUMN IF NOT EXISTS operation_type VARCHAR(30),
    ADD COLUMN IF NOT EXISTS merchant_nome VARCHAR(200),
    ADD COLUMN IF NOT EXISTS merchant_cnpj VARCHAR(20),
    ADD COLUMN IF NOT EXISTS categoria_pluggy_id VARCHAR(20),
    ADD COLUMN IF NOT EXISTS categoria_pluggy_sugerida VARCHAR(100);

-- Index parcial UNIQUE — so uma transacao pode referenciar cada pluggy_transaction_id
CREATE UNIQUE INDEX IF NOT EXISTS uq_pessoal_transacoes_pluggy_tx
    ON pessoal_transacoes(pluggy_transaction_id)
    WHERE pluggy_transaction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_origem
    ON pessoal_transacoes(origem_import);

COMMENT ON COLUMN pessoal_transacoes.origem_import IS
    'Origem da transacao: csv | ofx | pluggy. Default csv para compat retroativa.';
COMMENT ON COLUMN pessoal_transacoes.pluggy_transaction_id IS
    'UUID Pluggy (se importada via Open Finance). UNIQUE parcial — dedup cross-source.';
COMMENT ON COLUMN pessoal_transacoes.categoria_pluggy_id IS
    'categoryId Pluggy (ex 05080000). Permite mapear para PessoalCategoria via pessoal_pluggy_categorias_map.';
