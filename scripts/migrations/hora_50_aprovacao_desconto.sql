-- Migration HORA 50: fila de aprovacao de desconto (roadmap #28, Fatia 2).
-- Desconto acima do teto do modelo bloqueia a confirmacao da venda ate
-- aprovacao (perm comissao/aprovar). Idempotente.

CREATE TABLE IF NOT EXISTS hora_aprovacao_desconto (
    id              SERIAL PRIMARY KEY,
    venda_id        INTEGER NOT NULL REFERENCES hora_venda (id),
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    detalhe         TEXT,
    solicitado_em   TIMESTAMP NOT NULL,
    solicitado_por  VARCHAR(100),
    decidido_em     TIMESTAMP,
    decidido_por    VARCHAR(100),
    motivo_decisao  VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_hora_aprov_desc_venda ON hora_aprovacao_desconto (venda_id);
CREATE INDEX IF NOT EXISTS idx_hora_aprov_desc_status ON hora_aprovacao_desconto (status);
