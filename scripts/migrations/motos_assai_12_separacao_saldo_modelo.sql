-- Motos Assaí — Migration 12: saldo_modelo (qtd planejada) + ajuste UNIQUE para N separações
-- Idempotente.
--
-- 1. Cria `assai_separacao_saldo_modelo` (placeholder qtd planejada por modelo na separação).
-- 2. Ajusta UNIQUE de `assai_separacao` para permitir N separações FECHADAS por (pedido, loja),
--    bloqueando apenas EM_SEPARACAO simultânea.
--
-- Decidido em 2026-05-12: fluxo de carregamentos sucessivos permite múltiplas separações
-- parciais da mesma loja (cada uma representa um caminhão).

CREATE TABLE IF NOT EXISTS assai_separacao_saldo_modelo (
    id SERIAL PRIMARY KEY,
    separacao_id INTEGER NOT NULL REFERENCES assai_separacao(id) ON DELETE CASCADE,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    qtd_planejada INTEGER NOT NULL CHECK (qtd_planejada > 0),
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    UNIQUE (separacao_id, modelo_id)
);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_saldo_modelo_sep
    ON assai_separacao_saldo_modelo(separacao_id);

-- Ajustar UNIQUE para permitir N separacoes FECHADAS por (pedido, loja).
-- Antes: bloqueava qualquer status != 'CANCELADA' (impedia 2a separacao mesmo apos fechar a 1a)
-- Depois: bloqueia apenas 'EM_SEPARACAO' (1 ativa por vez; multiplas FECHADAS permitidas)
DROP INDEX IF EXISTS ux_assai_separacao_pedido_loja_ativa;
CREATE UNIQUE INDEX IF NOT EXISTS ux_assai_separacao_pedido_loja_em_separacao
    ON assai_separacao(pedido_id, loja_id)
    WHERE status = 'EM_SEPARACAO';
