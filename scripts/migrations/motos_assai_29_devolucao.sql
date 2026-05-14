-- Migration 29: Devolucao por NF de venda Q.P.A. (3 tabelas).
--
-- Cenario: cliente (Sendas/Assai) emite NF de devolucao (NFd) para 1+ chassis
-- de uma NF Q.P.A. de venda ja FATURADA. Cada chassi devolvido:
--   1. Recebe novo evento PENDENTE (volta ao estoque para conserto)
--   2. Observacao do evento: "Moto devolvida - {motivo}"
--   3. NF original NAO e cancelada (devolucao parcial e legitima).
--
-- Identidade da devolucao: (nf_qpa_origem_id, numero_nfd) UNIQUE — evita duplicar
-- a mesma NFd contra a mesma NF de origem.
--
-- Anexos: PDF, XML, PNG, JPG armazenados em S3 sob folder
-- `motos_assai/devolucoes/<devolucao_id>/`.

BEGIN;

-- ============================================================================
-- 1. Cabecalho da devolucao (1 NFd = 1 linha)
-- ============================================================================
CREATE TABLE IF NOT EXISTS assai_devolucao_nfd (
    id SERIAL PRIMARY KEY,
    nf_qpa_origem_id INTEGER NOT NULL REFERENCES assai_nf_qpa(id) ON DELETE RESTRICT,
    numero_nfd VARCHAR(40) NOT NULL,
    data_devolucao DATE NOT NULL,
    motivo TEXT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,

    CONSTRAINT uq_assai_devolucao_nf_numero UNIQUE (nf_qpa_origem_id, numero_nfd),
    CONSTRAINT ck_assai_devolucao_motivo_min CHECK (char_length(trim(motivo)) >= 3),
    CONSTRAINT ck_assai_devolucao_nfd_min CHECK (char_length(trim(numero_nfd)) >= 1)
);

CREATE INDEX IF NOT EXISTS ix_assai_devolucao_nf_origem
    ON assai_devolucao_nfd(nf_qpa_origem_id);
CREATE INDEX IF NOT EXISTS ix_assai_devolucao_data
    ON assai_devolucao_nfd(data_devolucao DESC);
CREATE INDEX IF NOT EXISTS ix_assai_devolucao_criado_em
    ON assai_devolucao_nfd(criado_em DESC);

-- ============================================================================
-- 2. Itens (1 chassi devolvido = 1 linha)
-- ============================================================================
CREATE TABLE IF NOT EXISTS assai_devolucao_item (
    id SERIAL PRIMARY KEY,
    devolucao_id INTEGER NOT NULL REFERENCES assai_devolucao_nfd(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    nf_qpa_item_id INTEGER REFERENCES assai_nf_qpa_item(id) ON DELETE SET NULL,
    evento_pendencia_id INTEGER REFERENCES assai_moto_evento(id) ON DELETE SET NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_assai_devolucao_item_chassi UNIQUE (devolucao_id, chassi)
);

CREATE INDEX IF NOT EXISTS ix_assai_devolucao_item_devolucao
    ON assai_devolucao_item(devolucao_id);
CREATE INDEX IF NOT EXISTS ix_assai_devolucao_item_chassi
    ON assai_devolucao_item(chassi);

-- ============================================================================
-- 3. Anexos (1 arquivo = 1 linha; padrao igual assai_pos_venda_ocorrencia_anexo)
-- ============================================================================
CREATE TABLE IF NOT EXISTS assai_devolucao_anexo (
    id SERIAL PRIMARY KEY,
    devolucao_id INTEGER NOT NULL REFERENCES assai_devolucao_nfd(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL,
    nome_original VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    content_type VARCHAR(120),
    tamanho_bytes BIGINT,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_assai_devolucao_anexo_devolucao
    ON assai_devolucao_anexo(devolucao_id);

-- ============================================================================
-- 4. Flag de devolucao em AssaiNfQpaItem
--
-- Regra de negocio: ao devolver o chassi, o pedido de vendas vinculado deve
-- recuperar o saldo da unidade (definido pelo MODELO). Marca-se a LINHA da
-- NF como devolvida — `recalcular_status_pedido()` exclui da contagem todo
-- `assai_separacao_item.id` referenciado por algum `assai_nf_qpa_item.devolvido = TRUE`.
-- ============================================================================
ALTER TABLE assai_nf_qpa_item
    ADD COLUMN IF NOT EXISTS devolvido BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS devolvido_em TIMESTAMP,
    ADD COLUMN IF NOT EXISTS devolucao_item_id INTEGER
        REFERENCES assai_devolucao_item(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_devolvido
    ON assai_nf_qpa_item(devolvido) WHERE devolvido = TRUE;
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_devolucao
    ON assai_nf_qpa_item(devolucao_item_id) WHERE devolucao_item_id IS NOT NULL;

COMMIT;
