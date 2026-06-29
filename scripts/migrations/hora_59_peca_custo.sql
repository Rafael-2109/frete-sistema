-- Migration HORA 59: Custo de peca (cadastro) + snapshot do custo no item de venda.
-- Objetivo: margem do preview da NF passa a usar o CUSTO real da peca
-- (nao mais o preco de venda como proxy). Idempotente. Rodar no Render Shell.

-- 1) Custo de aquisicao padrao da peca (usado como base de margem e snapshot).
ALTER TABLE hora_peca
    ADD COLUMN IF NOT EXISTS custo NUMERIC(15, 2) NOT NULL DEFAULT 0;

-- 2) Snapshot do custo unitario no momento da venda da peca (auditavel,
--    mesmo padrao do brinde). Default 0 cobre as linhas legadas.
ALTER TABLE hora_venda_item_peca
    ADD COLUMN IF NOT EXISTS custo_unitario NUMERIC(15, 2) NOT NULL DEFAULT 0;
