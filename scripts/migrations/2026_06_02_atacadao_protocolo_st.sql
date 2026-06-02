-- Migration: split de NF por protocolo ST (Atacadão RJ)
-- Adiciona:
--   regiao_tabela_rede.separar_protocolo_st         (liga/desliga split por rede+uf)
--   portal_atacadao_produto_depara.protocolo_st     (marca produto sujeito a ST)
-- Motivo: quebrar 1 Pedido Atacadão RJ em 2 sale.orders (ST vs demais).
-- Idempotente: ADD COLUMN IF NOT EXISTS + DEFAULT FALSE (backfill implícito para linhas existentes).
-- Data: 2026-06-02

BEGIN;

ALTER TABLE regiao_tabela_rede
    ADD COLUMN IF NOT EXISTS separar_protocolo_st BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE portal_atacadao_produto_depara
    ADD COLUMN IF NOT EXISTS protocolo_st BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
