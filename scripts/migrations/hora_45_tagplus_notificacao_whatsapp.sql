-- Idempotente. Tabela de notificações WhatsApp do módulo HORA (NFe aprovada / pedido confirmado).
CREATE TABLE IF NOT EXISTS hora_tagplus_notificacao_whatsapp (
    id               SERIAL PRIMARY KEY,
    tipo             VARCHAR(10)  NOT NULL,
    ref_id           INTEGER      NOT NULL,
    numero           VARCHAR(30),
    cliente_nome     VARCHAR(255),
    vendedor_nome    VARCHAR(120),
    loja_nome        VARCHAR(120),
    valor            NUMERIC(15,2),
    enviado_grupo    BOOLEAN      NOT NULL DEFAULT FALSE,
    enviado_vendedor BOOLEAN,
    status           VARCHAR(15)  NOT NULL DEFAULT 'PENDENTE',
    erro             TEXT,
    tentativas       INTEGER      NOT NULL DEFAULT 0,
    anexou_pdf       BOOLEAN      NOT NULL DEFAULT FALSE,
    enviado_em       TIMESTAMP,
    criado_em        TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_hora_tagplus_notif_tipo_ref
    ON hora_tagplus_notificacao_whatsapp (tipo, ref_id);
CREATE INDEX IF NOT EXISTS idx_hora_tagplus_notif_status
    ON hora_tagplus_notificacao_whatsapp (status);
