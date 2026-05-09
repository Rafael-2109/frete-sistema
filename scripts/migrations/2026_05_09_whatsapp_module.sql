-- Migration: modulo WhatsApp (canal alternativo via OpenClaw + Baileys).
--
-- 1. Adiciona usuarios.whatsapp_autorizado (opt-in explicito por seguranca).
-- 2. Cria index parcial em usuarios(telefone) WHERE whatsapp_autorizado = TRUE.
-- 3. Cria tabela whatsapp_tasks (lifecycle async, espelha teams_tasks).
--
-- Idempotente: usa IF NOT EXISTS em todas as operacoes DDL.

BEGIN;

-- 1. Coluna whatsapp_autorizado em usuarios
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS whatsapp_autorizado BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN usuarios.whatsapp_autorizado IS
    'Opt-in explicito do usuario para receber/enviar mensagens via WhatsApp Bot. '
    'Default FALSE: usuarios antigos com telefone cadastrado para contato '
    'generico nao recebem bot por engano.';

-- 2. Index parcial para resolver telefone -> usuario com filtro de autorizacao
CREATE INDEX IF NOT EXISTS ix_usuarios_telefone_whatsapp
    ON usuarios (telefone)
    WHERE whatsapp_autorizado = TRUE
      AND telefone IS NOT NULL
      AND telefone <> '';

-- 3. Tabela whatsapp_tasks (espelha teams_tasks com adaptacoes WhatsApp)
CREATE TABLE IF NOT EXISTS whatsapp_tasks (
    id VARCHAR(36) PRIMARY KEY,

    -- Identidade da conversa
    peer_jid VARCHAR(120) NOT NULL,           -- numero E.164 ou JID Baileys
    conversation_jid VARCHAR(120) NOT NULL,   -- = peer_jid (DM) ou JID grupo (@g.us)
    is_group BOOLEAN NOT NULL DEFAULT FALSE,
    sender_name VARCHAR(200),                 -- nome de exibicao quando disponivel

    -- Vinculo com Usuario Nacom (resolvido via Usuario.find_by_whatsapp_jid)
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,

    -- Estado e payload
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending, processing, completed, error, awaiting_user_input, timeout
    mensagem TEXT NOT NULL,
    resposta TEXT,

    -- AskUserQuestion (mesma mecanica do Teams)
    pending_questions JSON,
    pending_question_session_id VARCHAR(255),

    -- Correlacao OpenClaw
    openclaw_message_id VARCHAR(120),
    openclaw_session_key VARCHAR(255),

    -- Lifecycle
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_whatsapp_tasks_peer_jid
    ON whatsapp_tasks (peer_jid);

CREATE INDEX IF NOT EXISTS ix_whatsapp_tasks_status
    ON whatsapp_tasks (status);

CREATE INDEX IF NOT EXISTS ix_whatsapp_tasks_conversation_jid
    ON whatsapp_tasks (conversation_jid);

COMMIT;
