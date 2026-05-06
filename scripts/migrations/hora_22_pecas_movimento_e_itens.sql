-- ============================================================
-- HORA 22: Movimento de pecas + itens em NF entrada / venda
-- + ALTER hora_pedido_item para suportar peca (XOR moto/peca).
-- Idempotente.
-- ============================================================

CREATE TABLE IF NOT EXISTS hora_peca_movimento (
    id            SERIAL PRIMARY KEY,
    peca_id       INTEGER NOT NULL REFERENCES hora_peca(id),
    loja_id       INTEGER NOT NULL REFERENCES hora_loja(id),
    tipo          VARCHAR(25) NOT NULL,
    qtd           NUMERIC(15, 3) NOT NULL,
    ref_tabela    VARCHAR(50),
    ref_id        INTEGER,
    motivo        VARCHAR(500),
    operador      VARCHAR(100),
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_hora_peca_mov_saldo
    ON hora_peca_movimento(peca_id, loja_id, criado_em);
CREATE INDEX IF NOT EXISTS ix_hora_peca_mov_ref
    ON hora_peca_movimento(ref_tabela, ref_id);

CREATE TABLE IF NOT EXISTS hora_nf_entrada_item_peca (
    id                       SERIAL PRIMARY KEY,
    nf_id                    INTEGER NOT NULL REFERENCES hora_nf_entrada(id),
    peca_id                  INTEGER NOT NULL REFERENCES hora_peca(id),
    qtd_nf                   NUMERIC(15, 3) NOT NULL,
    preco_real               NUMERIC(15, 2) NOT NULL,
    modelo_texto_original    VARCHAR(255),
    qtd_conferida            NUMERIC(15, 3),
    divergencia_qtd          VARCHAR(20),
    foto_conferencia_s3_key  VARCHAR(500),
    conferida_em             TIMESTAMP,
    conferida_por            VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS ix_hora_nf_ent_item_peca_nf
    ON hora_nf_entrada_item_peca(nf_id);
CREATE INDEX IF NOT EXISTS ix_hora_nf_ent_item_peca_peca
    ON hora_nf_entrada_item_peca(peca_id);

CREATE TABLE IF NOT EXISTS hora_venda_item_peca (
    id                          SERIAL PRIMARY KEY,
    venda_id                    INTEGER NOT NULL REFERENCES hora_venda(id),
    peca_id                     INTEGER NOT NULL REFERENCES hora_peca(id),
    qtd                         NUMERIC(15, 3) NOT NULL,
    preco_unitario_referencia   NUMERIC(15, 2) NOT NULL,
    desconto_aplicado           NUMERIC(15, 2) NOT NULL DEFAULT 0,
    preco_final                 NUMERIC(15, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_venda_item_peca_venda
    ON hora_venda_item_peca(venda_id);
CREATE INDEX IF NOT EXISTS ix_hora_venda_item_peca_peca
    ON hora_venda_item_peca(peca_id);

-- ALTER hora_pedido_item: adicionar peca_id, qtd_pedida com CHECK XOR.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='hora_pedido_item' AND column_name='peca_id'
    ) THEN
        ALTER TABLE hora_pedido_item ADD COLUMN peca_id INTEGER REFERENCES hora_peca(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='hora_pedido_item' AND column_name='qtd_pedida'
    ) THEN
        ALTER TABLE hora_pedido_item ADD COLUMN qtd_pedida NUMERIC(15, 3);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='hora_pedido_item' AND constraint_name='chk_hora_pedido_item_xor'
    ) THEN
        ALTER TABLE hora_pedido_item
            ADD CONSTRAINT chk_hora_pedido_item_xor CHECK (
                (peca_id IS NULL AND qtd_pedida IS NULL) OR
                (peca_id IS NOT NULL AND modelo_id IS NULL AND numero_chassi IS NULL
                 AND qtd_pedida IS NOT NULL)
            );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_hora_pedido_item_peca
    ON hora_pedido_item(peca_id);
