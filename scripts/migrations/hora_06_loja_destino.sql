-- Migration HORA 06: loja_destino_id em pedido + nf_entrada
-- Data: 2026-04-19
-- Descricao:
--   Todos os pedidos/NFs HORA sao emitidos para o CNPJ da matriz (Tatuape),
--   mas a loja de destino REAL e indicada no cabecalho do Excel (ex: "HORA BRAGANCA").
--   Portanto, a resolucao por CNPJ nao funciona — a loja destino precisa ser
--   selecionada MANUALMENTE (ou auto-sugerida via match de apelido no header).
--   Adiciona loja_destino_id FK nullable (retrocompat com pedidos/NFs existentes).
-- Idempotente: ADD COLUMN IF NOT EXISTS.
-- RISCO: baixo.

ALTER TABLE hora_pedido
    ADD COLUMN IF NOT EXISTS loja_destino_id INTEGER REFERENCES hora_loja(id);

ALTER TABLE hora_pedido
    ADD COLUMN IF NOT EXISTS apelido_detectado VARCHAR(100);

CREATE INDEX IF NOT EXISTS ix_hora_pedido_loja_destino_id
    ON hora_pedido (loja_destino_id);

ALTER TABLE hora_nf_entrada
    ADD COLUMN IF NOT EXISTS loja_destino_id INTEGER REFERENCES hora_loja(id);

CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_loja_destino_id
    ON hora_nf_entrada (loja_destino_id);
