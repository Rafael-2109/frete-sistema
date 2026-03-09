-- Migration: Adicionar campos de contato do cliente em carvia_sessoes_cotacao
-- Executar no Render Shell: psql $DATABASE_URL -f adicionar_contato_sessao_cotacao_carvia.sql

ALTER TABLE carvia_sessoes_cotacao
    ADD COLUMN IF NOT EXISTS cliente_nome VARCHAR(255),
    ADD COLUMN IF NOT EXISTS cliente_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS cliente_telefone VARCHAR(50),
    ADD COLUMN IF NOT EXISTS cliente_responsavel VARCHAR(255);
