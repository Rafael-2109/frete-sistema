-- scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.sql
-- Idempotente — pode rodar 2x. Cria a tabela de notificações WhatsApp TagPlus.
CREATE TABLE IF NOT EXISTS tagplus_notificacao_whatsapp (
    id               SERIAL PRIMARY KEY,
    tipo             VARCHAR(10)  NOT NULL,
    event_type       VARCHAR(30)  NOT NULL,
    tagplus_id       VARCHAR(30)  NOT NULL,
    numero           VARCHAR(30),
    cliente_nome     VARCHAR(255),
    valor            NUMERIC(15,2),
    vendedor_nome    VARCHAR(120),
    vendedor_user_id INTEGER,
    enviado_grupo    BOOLEAN      NOT NULL DEFAULT FALSE,
    enviado_vendedor BOOLEAN,
    status           VARCHAR(15)  NOT NULL DEFAULT 'PENDENTE',
    erro             TEXT,
    tentativas       INTEGER      NOT NULL DEFAULT 0,
    anexou_pdf       BOOLEAN      NOT NULL DEFAULT FALSE,
    enviado_em       TIMESTAMP,
    criado_em        TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tagplus_notif_tipo_id_event
    ON tagplus_notificacao_whatsapp (tipo, tagplus_id, event_type);

CREATE INDEX IF NOT EXISTS idx_tagplus_notif_status
    ON tagplus_notificacao_whatsapp (status);
