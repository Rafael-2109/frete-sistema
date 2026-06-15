-- Migration: tabela de fornecedores bloqueados para entradas de compra.
-- Quando um CNPJ esta cadastrado e ATIVO, o sync do Odoo NAO grava
-- PedidoCompras nem MovimentacaoEstoque (ENTRADA/COMPRA) desse fornecedor.
-- CNPJ armazenado NORMALIZADO (apenas digitos). Idempotente: roda 2x sem efeito.

CREATE TABLE IF NOT EXISTS fornecedor_bloqueado (
    id              SERIAL PRIMARY KEY,
    cnpj            VARCHAR(14)  NOT NULL,
    razao_social    VARCHAR(255),
    motivo          VARCHAR(500),
    ativo           BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    criado_por      VARCHAR(100),
    atualizado_em   TIMESTAMP,
    atualizado_por  VARCHAR(100),
    CONSTRAINT uq_fornecedor_bloqueado_cnpj UNIQUE (cnpj)
);

CREATE INDEX IF NOT EXISTS ix_fornecedor_bloqueado_cnpj  ON fornecedor_bloqueado (cnpj);
CREATE INDEX IF NOT EXISTS ix_fornecedor_bloqueado_ativo ON fornecedor_bloqueado (ativo);
