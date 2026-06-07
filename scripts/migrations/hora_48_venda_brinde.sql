-- Migration HORA 48: Brindes de venda (roadmap #36).
-- Peca dada de brinde numa venda: custo = preco_venda_padrao (snapshot),
-- NAO cobrado (fora do valor_total), NAO abate estoque. Idempotente.

CREATE TABLE IF NOT EXISTS hora_venda_brinde (
    id              SERIAL PRIMARY KEY,
    venda_id        INTEGER NOT NULL REFERENCES hora_venda (id),
    peca_id         INTEGER NOT NULL REFERENCES hora_peca (id),
    qtd             NUMERIC(15, 3) NOT NULL DEFAULT 1,
    custo_unitario  NUMERIC(15, 2) NOT NULL DEFAULT 0,
    custo_total     NUMERIC(15, 2) NOT NULL DEFAULT 0,
    criado_em       TIMESTAMP NOT NULL,
    criado_por      VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_hora_venda_brinde_venda_id ON hora_venda_brinde (venda_id);
CREATE INDEX IF NOT EXISTS idx_hora_venda_brinde_peca_id ON hora_venda_brinde (peca_id);
