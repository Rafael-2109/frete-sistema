-- ============================================================================
-- Script SQL para RENDER SHELL
-- Criar tabela: tagplus_oauth_token
--
-- 🎯 OBJETIVO: Armazenar tokens OAuth2 do TagPlus de forma PERSISTENTE
-- ⚠️ IMPORTANTE: Resolve problema de perda de tokens após deploy
--
-- Data: 2025-11-06
-- ============================================================================

-- Criar tabela
CREATE TABLE IF NOT EXISTS tagplus_oauth_token (
    id SERIAL PRIMARY KEY,

    -- Tipo de API (único por tipo)
    api_type VARCHAR(50) NOT NULL UNIQUE,
    -- Exemplos: 'clientes', 'notas', 'produtos'

    -- ✅ Tokens OAuth2
    access_token TEXT NOT NULL,        -- Expira em 24h
    refresh_token TEXT,                 -- Dura 30-90 dias

    -- ⏰ Controle de expiração
    expires_at TIMESTAMP,               -- Quando access_token expira

    -- 📝 Metadados OAuth
    token_type VARCHAR(20) DEFAULT 'Bearer',
    scope VARCHAR(255),

    -- 📊 Auditoria e estatísticas
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_refresh TIMESTAMP,           -- Última renovação
    total_refreshes INTEGER DEFAULT 0,  -- Contador de renovações
    ultima_requisicao TIMESTAMP,        -- Último uso

    -- ✅ Status
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_tagplus_oauth_api_type
    ON tagplus_oauth_token(api_type);

CREATE INDEX IF NOT EXISTS idx_tagplus_oauth_ativo
    ON tagplus_oauth_token(ativo);

-- Comentários para documentação
COMMENT ON TABLE tagplus_oauth_token IS
    'Armazena tokens OAuth2 do TagPlus de forma persistente (sobrevive deploys)';

COMMENT ON COLUMN tagplus_oauth_token.api_type IS
    'Tipo da API: clientes, notas, produtos';

COMMENT ON COLUMN tagplus_oauth_token.access_token IS
    'Token de acesso (expira em 24h)';

COMMENT ON COLUMN tagplus_oauth_token.refresh_token IS
    'Token de renovação (dura 30-90 dias)';

COMMENT ON COLUMN tagplus_oauth_token.expires_at IS
    'Timestamp de expiração do access_token';

COMMENT ON COLUMN tagplus_oauth_token.total_refreshes IS
    'Contador de quantas vezes o token foi renovado';

-- ============================================================================
-- ✅ SUCESSO! Tabela criada.
--
-- 📋 PRÓXIMOS PASSOS:
-- 1. Após criar a tabela, autorize o app no TagPlus normalmente
-- 2. Os tokens serão salvos automaticamente no banco
-- 3. Mesmo após deploy, os tokens persistirão
-- 4. Renovação automática funcionará por 30-90 dias sem precisar autorizar
-- ============================================================================
