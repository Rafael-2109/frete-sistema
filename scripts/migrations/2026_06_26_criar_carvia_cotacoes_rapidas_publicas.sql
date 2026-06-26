-- CarVia — Cotacao Rapida PUBLICA (tela sem login): snapshot persistido (lead).
CREATE TABLE IF NOT EXISTS carvia_cotacoes_rapidas_publicas (
    id                SERIAL PRIMARY KEY,
    solicitante_nome  VARCHAR(160) NOT NULL,
    cnpj_cliente      VARCHAR(20),
    uf_destino        VARCHAR(2) NOT NULL,
    cidade_destino    VARCHAR(120),
    codigo_ibge       VARCHAR(7),
    itens             JSONB NOT NULL,
    opcoes            JSONB NOT NULL,
    valor_total_min   NUMERIC(15, 2),
    qtd_total_motos   INTEGER,
    ip_solicitante    VARCHAR(45),
    user_agent        VARCHAR(255),
    criado_em         TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_carvia_cot_rap_pub_criado_em
    ON carvia_cotacoes_rapidas_publicas (criado_em DESC);
CREATE INDEX IF NOT EXISTS ix_carvia_cot_rap_pub_uf
    ON carvia_cotacoes_rapidas_publicas (uf_destino);
