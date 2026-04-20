-- Migration HORA 08: cria hora_devolucao_fornecedor + item
-- Data: 2026-04-20
-- Descricao:
--   Tabelas para registrar devolucao de motos ao fornecedor (Motochefe).
--   HoraMoto e insert-once; devolucao emite evento DEVOLVIDA em hora_moto_evento
--   apontando origem para hora_devolucao_fornecedor_item.
-- Idempotente: CREATE TABLE IF NOT EXISTS.
-- RISCO: baixo. Tabelas novas.

CREATE TABLE IF NOT EXISTS hora_devolucao_fornecedor (
    id SERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES hora_loja(id),
    nf_entrada_id INTEGER NULL REFERENCES hora_nf_entrada(id),
    motivo VARCHAR(50) NOT NULL,
    observacoes TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
    data_devolucao DATE NOT NULL DEFAULT CURRENT_DATE,
    data_envio DATE NULL,
    data_confirmacao DATE NULL,
    nf_saida_numero VARCHAR(20) NULL,
    nf_saida_chave_44 VARCHAR(44) NULL UNIQUE,
    criado_por VARCHAR(100) NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_devolucao_fornecedor_loja
    ON hora_devolucao_fornecedor (loja_id);
CREATE INDEX IF NOT EXISTS ix_hora_devolucao_fornecedor_nf_entrada
    ON hora_devolucao_fornecedor (nf_entrada_id);
CREATE INDEX IF NOT EXISTS ix_hora_devolucao_fornecedor_status
    ON hora_devolucao_fornecedor (status);


CREATE TABLE IF NOT EXISTS hora_devolucao_fornecedor_item (
    id SERIAL PRIMARY KEY,
    devolucao_id INTEGER NOT NULL REFERENCES hora_devolucao_fornecedor(id),
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    motivo_especifico VARCHAR(255) NULL,
    recebimento_conferencia_id INTEGER NULL REFERENCES hora_recebimento_conferencia(id),
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_hora_devolucao_fornecedor_item_chassi
        UNIQUE (devolucao_id, numero_chassi)
);

CREATE INDEX IF NOT EXISTS ix_hora_devolucao_fornecedor_item_devolucao
    ON hora_devolucao_fornecedor_item (devolucao_id);
CREATE INDEX IF NOT EXISTS ix_hora_devolucao_fornecedor_item_chassi
    ON hora_devolucao_fornecedor_item (numero_chassi);
