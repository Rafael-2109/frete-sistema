-- Migration HORA 12: redesign do recebimento com conferência cega + auditoria
--
-- 1. hora_recebimento: amplia status VARCHAR(20) -> VARCHAR(30) e adiciona
--                      qtd_declarada, finalizado_em.
-- 2. hora_recebimento_conferencia: adiciona ordem, modelo_id_conferido,
--                                  cor_conferida, avaria_fisica, confirmado_em,
--                                  substituida, substituida_por_id.
-- 3. Troca UNIQUE(recebimento_id, numero_chassi) por UNIQUE PARCIAL
--    WHERE substituida = false; cria UNIQUE PARCIAL (recebimento_id, ordem).
-- 4. Cria hora_conferencia_divergencia (1-N por conferência).
-- 5. Cria hora_conferencia_auditoria (append-only).
--
-- Idempotente.

-- ---------------------------------------------------------------------
-- 1) hora_recebimento
-- ---------------------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'hora_recebimento'
          AND column_name = 'status'
          AND character_maximum_length < 30
    ) THEN
        ALTER TABLE hora_recebimento ALTER COLUMN status TYPE VARCHAR(30);
    END IF;
END $$;

ALTER TABLE hora_recebimento
    ADD COLUMN IF NOT EXISTS qtd_declarada INTEGER NULL,
    ADD COLUMN IF NOT EXISTS finalizado_em TIMESTAMP NULL;

-- ---------------------------------------------------------------------
-- 2) hora_recebimento_conferencia
-- ---------------------------------------------------------------------

ALTER TABLE hora_recebimento_conferencia
    ADD COLUMN IF NOT EXISTS ordem INTEGER NULL,
    ADD COLUMN IF NOT EXISTS confirmado_em TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS modelo_id_conferido INTEGER NULL REFERENCES hora_modelo(id),
    ADD COLUMN IF NOT EXISTS cor_conferida VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS avaria_fisica BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS substituida BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS substituida_por_id INTEGER NULL
        REFERENCES hora_recebimento_conferencia(id);

-- Backfill ordem para linhas legado: numerar 1..N por (recebimento_id, id).
DO $$
DECLARE
    r RECORD;
    n INTEGER;
BEGIN
    FOR r IN
        SELECT DISTINCT recebimento_id
        FROM hora_recebimento_conferencia
        WHERE ordem IS NULL
    LOOP
        n := 0;
        UPDATE hora_recebimento_conferencia x
        SET ordem = sub.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
            FROM hora_recebimento_conferencia
            WHERE recebimento_id = r.recebimento_id
              AND ordem IS NULL
        ) sub
        WHERE x.id = sub.id;
    END LOOP;
END $$;

-- Agora ordem pode virar NOT NULL
ALTER TABLE hora_recebimento_conferencia
    ALTER COLUMN ordem SET NOT NULL;

-- Remove UNIQUE antigo se existir, para dar lugar aos UNIQUE parciais.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_hora_recebimento_conferencia_chassi'
    ) THEN
        ALTER TABLE hora_recebimento_conferencia
            DROP CONSTRAINT uq_hora_recebimento_conferencia_chassi;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ix_hora_conferencia_ativa
    ON hora_recebimento_conferencia (recebimento_id, numero_chassi)
    WHERE substituida = FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS ix_hora_conferencia_ordem_ativa
    ON hora_recebimento_conferencia (recebimento_id, ordem)
    WHERE substituida = FALSE;

-- ---------------------------------------------------------------------
-- 3) hora_conferencia_divergencia (1-N)
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS hora_conferencia_divergencia (
    id SERIAL PRIMARY KEY,
    conferencia_id INTEGER NOT NULL
        REFERENCES hora_recebimento_conferencia(id) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL,
    detalhe TEXT NULL,
    valor_esperado VARCHAR(200) NULL,
    valor_conferido VARCHAR(200) NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_hora_conferencia_divergencia_tipo
        UNIQUE (conferencia_id, tipo)
);

CREATE INDEX IF NOT EXISTS ix_hora_conferencia_divergencia_conferencia_id
    ON hora_conferencia_divergencia (conferencia_id);

CREATE INDEX IF NOT EXISTS ix_hora_conferencia_divergencia_tipo
    ON hora_conferencia_divergencia (tipo);

-- ---------------------------------------------------------------------
-- 4) hora_conferencia_auditoria (append-only)
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS hora_conferencia_auditoria (
    id SERIAL PRIMARY KEY,
    recebimento_id INTEGER NOT NULL
        REFERENCES hora_recebimento(id) ON DELETE CASCADE,
    conferencia_id INTEGER NULL
        REFERENCES hora_recebimento_conferencia(id) ON DELETE SET NULL,
    usuario VARCHAR(100) NULL,
    acao VARCHAR(40) NOT NULL,
    campo_alterado VARCHAR(60) NULL,
    valor_antes TEXT NULL,
    valor_depois TEXT NULL,
    detalhe TEXT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_hora_conferencia_auditoria_recebimento_id
    ON hora_conferencia_auditoria (recebimento_id);

CREATE INDEX IF NOT EXISTS ix_hora_conferencia_auditoria_conferencia_id
    ON hora_conferencia_auditoria (conferencia_id);

CREATE INDEX IF NOT EXISTS ix_hora_conferencia_auditoria_acao
    ON hora_conferencia_auditoria (acao);

CREATE INDEX IF NOT EXISTS ix_hora_conferencia_auditoria_criado_em
    ON hora_conferencia_auditoria (criado_em);

CREATE INDEX IF NOT EXISTS ix_hora_conf_aud_rec_ts
    ON hora_conferencia_auditoria (recebimento_id, criado_em);
