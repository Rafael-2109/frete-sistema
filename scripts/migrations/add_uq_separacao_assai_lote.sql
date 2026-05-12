-- Migration: UNIQUE partial index em separacao para lotes ASSAI-SEP-*
-- Data: 2026-05-11
-- Descricao: garantia atomica de idempotencia do mirror_assai_to_separacao.
--
-- O service `mirror_assai_to_separacao` cria N linhas (uma por chassi) em
-- `separacao` para cada AssaiSeparacao. Para ser idempotente, ele faz um
-- COUNT antes do INSERT. Sem constraint de banco, dois requests concorrentes
-- podem passar o COUNT e criar 2*N linhas (race condition).
--
-- Este index UNIQUE em `(separacao_lote_id, cod_produto)` PARCIAL (apenas
-- onde lote comeca com 'ASSAI-SEP-') previne duplicacao no nivel do banco.
-- Cada chassi (cod_produto) tem 1 linha por separacao espelhada.
--
-- Lotes Nacom (LOTE_*) e CarVia (CARVIA-*) nao tem essa unicidade — comportamento
-- preservado pelo `postgresql_where`. Nacom Separacao pode ter N linhas por
-- mesmo lote+produto (split de pedidos, etc).
-- Idempotente: usa IF NOT EXISTS.

CREATE UNIQUE INDEX IF NOT EXISTS uq_separacao_assai_lote_produto
    ON separacao (separacao_lote_id, cod_produto)
    WHERE separacao_lote_id LIKE 'ASSAI-SEP-%';
