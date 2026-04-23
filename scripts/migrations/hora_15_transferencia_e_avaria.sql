-- Migration HORA 15: transferencia entre filiais + avaria em estoque.
-- Adiciona:
--   hora_transferencia (header: EM_TRANSITO|CONFIRMADA|CANCELADA)
--   hora_transferencia_item (N chassis por transferencia)
--   hora_transferencia_auditoria (append-only)
--   hora_avaria (header: ABERTA|RESOLVIDA|IGNORADA)
--   hora_avaria_foto (N fotos por avaria)
-- Idempotente: usa IF NOT EXISTS.

-- ============================================================
-- 1. hora_transferencia
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_transferencia (
    id BIGSERIAL PRIMARY KEY,
    loja_origem_id INTEGER NOT NULL REFERENCES hora_loja(id),
    loja_destino_id INTEGER NOT NULL REFERENCES hora_loja(id),
    status VARCHAR(30) NOT NULL,
    emitida_em TIMESTAMP NOT NULL,
    emitida_por VARCHAR(100) NOT NULL,
    confirmada_em TIMESTAMP NULL,
    confirmada_por VARCHAR(100) NULL,
    cancelada_em TIMESTAMP NULL,
    cancelada_por VARCHAR(100) NULL,
    motivo_cancelamento VARCHAR(255) NULL,
    observacoes TEXT NULL,
    criado_em TIMESTAMP NOT NULL,
    atualizado_em TIMESTAMP NOT NULL,
    CONSTRAINT ck_hora_transferencia_lojas_distintas
        CHECK (loja_origem_id <> loja_destino_id),
    CONSTRAINT ck_hora_transferencia_motivo_quando_cancelada
        CHECK (
            (cancelada_em IS NULL AND motivo_cancelamento IS NULL)
            OR (cancelada_em IS NOT NULL
                AND motivo_cancelamento IS NOT NULL
                AND length(trim(motivo_cancelamento)) >= 3)
        ),
    CONSTRAINT ck_hora_transferencia_confirmada_apos_emitida
        CHECK (confirmada_em IS NULL OR confirmada_em >= emitida_em),
    CONSTRAINT ck_hora_transferencia_cancelada_apos_emitida
        CHECK (cancelada_em IS NULL OR cancelada_em >= emitida_em),
    CONSTRAINT ck_hora_transferencia_exclusivo_final
        CHECK (NOT (confirmada_em IS NOT NULL AND cancelada_em IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS ix_hora_transferencia_status
    ON hora_transferencia(status);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_loja_origem
    ON hora_transferencia(loja_origem_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_loja_destino
    ON hora_transferencia(loja_destino_id);

-- ============================================================
-- 2. hora_transferencia_item
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_transferencia_item (
    id BIGSERIAL PRIMARY KEY,
    transferencia_id INTEGER NOT NULL REFERENCES hora_transferencia(id) ON DELETE CASCADE,
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    conferido_destino_em TIMESTAMP NULL,
    conferido_destino_por VARCHAR(100) NULL,
    qr_code_lido BOOLEAN NOT NULL DEFAULT FALSE,
    foto_s3_key VARCHAR(500) NULL,
    observacao_item TEXT NULL,
    CONSTRAINT uq_hora_transferencia_item_chassi
        UNIQUE (transferencia_id, numero_chassi)
);

CREATE INDEX IF NOT EXISTS ix_hora_transferencia_item_transferencia
    ON hora_transferencia_item(transferencia_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_item_chassi
    ON hora_transferencia_item(numero_chassi);

-- ============================================================
-- 3. hora_transferencia_auditoria (append-only)
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_transferencia_auditoria (
    id BIGSERIAL PRIMARY KEY,
    transferencia_id INTEGER NOT NULL REFERENCES hora_transferencia(id) ON DELETE CASCADE,
    item_id INTEGER NULL REFERENCES hora_transferencia_item(id),
    usuario VARCHAR(100) NOT NULL,
    acao VARCHAR(40) NOT NULL,
    campo_alterado VARCHAR(60) NULL,
    valor_antes TEXT NULL,
    valor_depois TEXT NULL,
    detalhe TEXT NULL,
    criado_em TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_transf
    ON hora_transferencia_auditoria(transferencia_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_item
    ON hora_transferencia_auditoria(item_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_acao
    ON hora_transferencia_auditoria(acao);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_timeline
    ON hora_transferencia_auditoria(transferencia_id, criado_em DESC);

-- ============================================================
-- 4. hora_avaria
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_avaria (
    id BIGSERIAL PRIMARY KEY,
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    loja_id INTEGER NOT NULL REFERENCES hora_loja(id),
    descricao TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
    criado_em TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    resolvido_em TIMESTAMP NULL,
    resolvido_por VARCHAR(100) NULL,
    resolucao_observacao TEXT NULL,
    CONSTRAINT ck_hora_avaria_descricao_nao_vazia
        CHECK (length(trim(descricao)) >= 3),
    CONSTRAINT ck_hora_avaria_resolvida_tem_status
        CHECK (resolvido_em IS NULL OR status IN ('RESOLVIDA','IGNORADA'))
);

CREATE INDEX IF NOT EXISTS ix_hora_avaria_chassi
    ON hora_avaria(numero_chassi);
CREATE INDEX IF NOT EXISTS ix_hora_avaria_loja
    ON hora_avaria(loja_id);
CREATE INDEX IF NOT EXISTS ix_hora_avaria_status
    ON hora_avaria(status);
CREATE INDEX IF NOT EXISTS ix_hora_avaria_criado_em
    ON hora_avaria(criado_em);

-- ============================================================
-- 5. hora_avaria_foto
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_avaria_foto (
    id BIGSERIAL PRIMARY KEY,
    avaria_id INTEGER NOT NULL REFERENCES hora_avaria(id) ON DELETE CASCADE,
    foto_s3_key VARCHAR(500) NOT NULL,
    legenda VARCHAR(255) NULL,
    criado_em TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_avaria_foto_avaria
    ON hora_avaria_foto(avaria_id);
