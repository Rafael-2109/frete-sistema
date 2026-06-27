-- Migration HORA 57: Recebimento por filial sem NF (NF provisória).
-- Adiciona hora_nf_entrada.tipo {PROVISORIA,REAL} (default REAL p/ NFs existentes)
-- e a tabela de snapshot congelado hora_recebimento_esperado.
-- Idempotente — pode rodar 2x (IF NOT EXISTS).
-- Nota: planejado como hora_54 no spec, renumerado para 57 porque
--       hora_54_aprovacoes_perm já existia no branch main.

ALTER TABLE hora_nf_entrada
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'REAL';

CREATE TABLE IF NOT EXISTS hora_recebimento_esperado (
    id                            SERIAL PRIMARY KEY,
    recebimento_id                INTEGER NOT NULL REFERENCES hora_recebimento (id),
    pedido_id                     INTEGER REFERENCES hora_pedido (id),
    pedido_item_id                INTEGER REFERENCES hora_pedido_item (id),
    modelo_id                     INTEGER REFERENCES hora_modelo (id),
    cor                           VARCHAR(50),
    chassi_esperado               VARCHAR(30),
    preco_esperado                NUMERIC(15, 2),
    consumido_por_conferencia_id  INTEGER REFERENCES hora_recebimento_conferencia (id),
    criado_em                     TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec ON hora_recebimento_esperado (recebimento_id);
CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_modelo ON hora_recebimento_esperado (recebimento_id, modelo_id);
CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_chassi ON hora_recebimento_esperado (recebimento_id, chassi_esperado);
