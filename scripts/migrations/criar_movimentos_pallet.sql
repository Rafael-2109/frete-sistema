-- Migracao: Adicionar campos de pallet em MovimentacaoEstoque e embarques/embarque_itens
-- Data: 03/01/2026
-- Executar no Shell do Render

-- 1. Campos em embarques
ALTER TABLE embarques
ADD COLUMN IF NOT EXISTS nf_pallet_transportadora VARCHAR(20),
ADD COLUMN IF NOT EXISTS qtd_pallet_transportadora FLOAT DEFAULT 0;

-- 2. Campos em embarque_itens
ALTER TABLE embarque_itens
ADD COLUMN IF NOT EXISTS nf_pallet_cliente VARCHAR(20),
ADD COLUMN IF NOT EXISTS qtd_pallet_cliente FLOAT DEFAULT 0;

-- 3. Campos de pallet em terceiros na movimentacao_estoque
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS tipo_destinatario VARCHAR(20),
ADD COLUMN IF NOT EXISTS cnpj_destinatario VARCHAR(20),
ADD COLUMN IF NOT EXISTS nome_destinatario VARCHAR(255),
ADD COLUMN IF NOT EXISTS embarque_item_id INTEGER REFERENCES embarque_itens(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS baixado BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS baixado_em TIMESTAMP,
ADD COLUMN IF NOT EXISTS baixado_por VARCHAR(100),
ADD COLUMN IF NOT EXISTS movimento_baixado_id INTEGER REFERENCES movimentacao_estoque(id) ON DELETE SET NULL;

-- 4. Indices para pallet
CREATE INDEX IF NOT EXISTS ix_movimentacao_cnpj_destinatario ON movimentacao_estoque(cnpj_destinatario);
CREATE INDEX IF NOT EXISTS ix_movimentacao_tipo_destinatario ON movimentacao_estoque(tipo_destinatario);
CREATE INDEX IF NOT EXISTS ix_movimentacao_baixado ON movimentacao_estoque(baixado);
