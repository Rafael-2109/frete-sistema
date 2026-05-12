-- Motos Assai - Migration 16: Pos-Venda (ocorrencias por chassi vendido)
-- Idempotente.
--
-- Cria 2 tabelas:
--   * assai_pos_venda_ocorrencia        — 1 ocorrencia (texto) por chassi
--   * assai_pos_venda_ocorrencia_anexo  — N anexos S3 por ocorrencia
--
-- Categoria: LOJA (problema reportado dentro da loja Assai/Sendas) ou CLIENTE
-- (problema reportado pelo cliente final).
--
-- Chassi e a chave de vinculo. NF Q.P.A. correspondente e resolvida via JOIN
-- (assai_nf_qpa_item.chassi -> assai_nf_qpa -> assai_loja).

CREATE TABLE IF NOT EXISTS assai_pos_venda_ocorrencia (
    id SERIAL PRIMARY KEY,
    chassi VARCHAR(50) NOT NULL,
    categoria VARCHAR(10) NOT NULL,
    descricao TEXT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    atualizado_em TIMESTAMP,
    atualizado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT ck_assai_pos_venda_ocorrencia_categoria
        CHECK (categoria IN ('LOJA','CLIENTE'))
);

CREATE INDEX IF NOT EXISTS ix_assai_pos_venda_ocorrencia_chassi
    ON assai_pos_venda_ocorrencia(chassi);
CREATE INDEX IF NOT EXISTS ix_assai_pos_venda_ocorrencia_categoria
    ON assai_pos_venda_ocorrencia(categoria);
CREATE INDEX IF NOT EXISTS ix_assai_pos_venda_ocorrencia_criado_em
    ON assai_pos_venda_ocorrencia(criado_em DESC);


CREATE TABLE IF NOT EXISTS assai_pos_venda_ocorrencia_anexo (
    id SERIAL PRIMARY KEY,
    ocorrencia_id INTEGER NOT NULL
        REFERENCES assai_pos_venda_ocorrencia(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL,
    nome_original VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    content_type VARCHAR(120),
    tamanho_bytes BIGINT,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT ck_assai_pos_venda_ocorrencia_anexo_tipo
        CHECK (tipo IN ('FOTO','VIDEO','AUDIO','OUTRO'))
);

CREATE INDEX IF NOT EXISTS ix_assai_pos_venda_ocorrencia_anexo_ocorrencia
    ON assai_pos_venda_ocorrencia_anexo(ocorrencia_id);
