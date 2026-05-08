-- Migration HORA 39: Devolucao de Venda (cliente -> HORA).
--
-- ATENCAO: NAO confundir com hora_devolucao_fornecedor (HORA -> Motochefe).
-- Esta tabela cobre o caso "cliente final devolveu a moto que comprou":
--   1. Operador pesquisa a NF de venda (HoraVenda).
--   2. Seleciona quais chassis da NF estao voltando.
--   3. Sistema emite evento DEVOLVIDA por chassi (sai do estoque).
--   4. Devolucao fica PENDENTE ate que cada chassi seja resolvido individualmente:
--      - DISPONIVEL    -> volta ao estoque (evento CONFERIDA)
--      - AVARIA        -> cria HoraAvaria + evento AVARIADA (volta ao estoque com badge)
--      - PECA_FALTANDO -> cria HoraPecaFaltando + evento FALTANDO_PECA (volta ao estoque com badge)
--
-- Fluxo:
--   header.status: PENDENTE -> RESOLVIDA (todos itens resolvidos) | CANCELADA (revertida)
--   item.status_item: PENDENTE -> RESOLVIDA
--
-- Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS hora_devolucao_venda (
    id                  SERIAL PRIMARY KEY,
    venda_id            INTEGER NOT NULL REFERENCES hora_venda(id),
    loja_id             INTEGER NOT NULL REFERENCES hora_loja(id),
    motivo              TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    data_devolucao      DATE NOT NULL,
    data_resolucao      DATE,
    cancelamento_motivo VARCHAR(500),
    criado_por          VARCHAR(100),
    resolvida_por       VARCHAR(100),
    cancelada_por       VARCHAR(100),
    criado_em           TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    atualizado_em       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_venda_id  ON hora_devolucao_venda(venda_id);
CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_loja_id   ON hora_devolucao_venda(loja_id);
CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_status    ON hora_devolucao_venda(status);
CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_data      ON hora_devolucao_venda(data_devolucao);


CREATE TABLE IF NOT EXISTS hora_devolucao_venda_item (
    id                    SERIAL PRIMARY KEY,
    devolucao_id          INTEGER NOT NULL REFERENCES hora_devolucao_venda(id) ON DELETE CASCADE,
    numero_chassi         VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    venda_item_id         INTEGER REFERENCES hora_venda_item(id),
    motivo_especifico     TEXT,

    -- Resolucao por chassi (1 acao por item).
    status_item           VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    resolucao_acao        VARCHAR(30),
    resolucao_observacoes TEXT,
    resolvida_em          TIMESTAMP,
    resolvida_por         VARCHAR(100),

    -- Refs ao registro criado pela resolucao (auditoria; NULL para acao DISPONIVEL).
    avaria_id             INTEGER REFERENCES hora_avaria(id),
    peca_faltando_id      INTEGER REFERENCES hora_peca_faltando(id),

    criado_em             TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),

    CONSTRAINT uq_hora_dev_venda_item_chassi UNIQUE (devolucao_id, numero_chassi)
);

CREATE INDEX IF NOT EXISTS ix_hora_dev_venda_item_devolucao ON hora_devolucao_venda_item(devolucao_id);
CREATE INDEX IF NOT EXISTS ix_hora_dev_venda_item_chassi    ON hora_devolucao_venda_item(numero_chassi);
CREATE INDEX IF NOT EXISTS ix_hora_dev_venda_item_status    ON hora_devolucao_venda_item(status_item);
