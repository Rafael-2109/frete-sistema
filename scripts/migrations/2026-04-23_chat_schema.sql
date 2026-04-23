-- scripts/migrations/2026-04-23_chat_schema.sql
-- Cria 7 tabelas + indices + trigger FTS do modulo chat in-app.
-- Idempotente: pode rodar multiplas vezes sem erro.
-- Fonte de verdade: app/chat/models.py (ler antes de editar este SQL).

BEGIN;

-- ============================================================================
-- 1) chat_threads
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_threads (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,
    titulo VARCHAR(200),
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    sistemas_required JSONB NOT NULL DEFAULT '[]'::jsonb,
    criado_por_id INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    atualizado_em TIMESTAMP,
    arquivado_em TIMESTAMP,
    last_message_at TIMESTAMP,
    CONSTRAINT ck_chat_threads_tipo CHECK (tipo IN ('dm','group','entity','system_dm'))
);

-- Partial unique index: apenas 1 thread por entity_type+entity_id quando entity_type IS NOT NULL.
-- Nao usa UniqueConstraint pois postgresql_where nao e suportado ali (ver models.py).
CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_threads_entity
    ON chat_threads(entity_type, entity_id)
    WHERE entity_type IS NOT NULL;

-- Garante 1 caixa de entrada de sistema por usuario (race prevention para SystemNotifier).
CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_threads_system_dm
    ON chat_threads(criado_por_id)
    WHERE tipo = 'system_dm';

CREATE INDEX IF NOT EXISTS idx_chat_threads_last_msg
    ON chat_threads(last_message_at);


-- ============================================================================
-- 2) chat_messages (criada ANTES de chat_members por causa do FK last_read_message_id)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES chat_threads(id),
    sender_type VARCHAR(10) NOT NULL,
    sender_user_id INTEGER REFERENCES usuarios(id),
    sender_system_source VARCHAR(50),
    content TEXT NOT NULL,
    content_tsv TSVECTOR,
    reply_to_message_id BIGINT REFERENCES chat_messages(id),
    deep_link VARCHAR(500),
    nivel VARCHAR(20),
    dados JSONB,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    editado_em TIMESTAMP,
    deletado_em TIMESTAMP,
    deletado_por_id INTEGER REFERENCES usuarios(id),
    CONSTRAINT ck_chat_messages_sender_type CHECK (sender_type IN ('user','system')),
    CONSTRAINT ck_chat_messages_sender_consistency CHECK (
        (sender_type = 'user' AND sender_user_id IS NOT NULL) OR
        (sender_type = 'system' AND sender_system_source IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_time
    ON chat_messages(thread_id, criado_em);

CREATE INDEX IF NOT EXISTS idx_chat_messages_sender_time
    ON chat_messages(sender_user_id, criado_em)
    WHERE sender_type = 'user';

CREATE INDEX IF NOT EXISTS idx_chat_messages_content_tsv
    ON chat_messages USING gin(content_tsv);

-- Trigger: manter content_tsv atualizado em INSERT/UPDATE de content.
CREATE OR REPLACE FUNCTION chat_messages_tsv_update() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('portuguese', COALESCE(NEW.content, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chat_messages_tsv_trigger ON chat_messages;
CREATE TRIGGER chat_messages_tsv_trigger
    BEFORE INSERT OR UPDATE OF content ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION chat_messages_tsv_update();


-- ============================================================================
-- 3) chat_members (usa_alter FK para last_read_message_id -> chat_messages)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_members (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES usuarios(id),
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    adicionado_por_id INTEGER REFERENCES usuarios(id),
    adicionado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    last_read_message_id BIGINT REFERENCES chat_messages(id),
    silenciado BOOLEAN NOT NULL DEFAULT FALSE,
    removido_em TIMESTAMP,
    CONSTRAINT ck_chat_members_role CHECK (role IN ('owner','admin','member'))
);

CREATE INDEX IF NOT EXISTS idx_chat_members_user_thread
    ON chat_members(user_id, thread_id);


-- ============================================================================
-- 4) chat_attachments
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    s3_key VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);


-- ============================================================================
-- 5) chat_mentions
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_mentions (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    mentioned_user_id INTEGER NOT NULL REFERENCES usuarios(id)
);


-- ============================================================================
-- 6) chat_reactions
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_reactions (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES usuarios(id),
    emoji VARCHAR(16) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    CONSTRAINT uq_chat_reactions UNIQUE(message_id, user_id, emoji)
);


-- ============================================================================
-- 7) chat_forwards (sem CASCADE em FKs de mensagem: registro de auditoria deve
--    sobreviver deletes logicos; sem ON DELETE CASCADE intencional)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_forwards (
    id BIGSERIAL PRIMARY KEY,
    original_message_id BIGINT NOT NULL REFERENCES chat_messages(id),
    forwarded_message_id BIGINT NOT NULL REFERENCES chat_messages(id),
    forwarded_by_id INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);

COMMIT;
