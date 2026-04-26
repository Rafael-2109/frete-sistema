-- Migration HORA 18: integracao TagPlus para emissao de NFe de venda.
--
-- 5 tabelas novas (prefixo hora_tagplus_):
--   hora_tagplus_conta              singleton: 1 linha ativa por vez
--   hora_tagplus_token              tokens OAuth2 persistidos (encriptados)
--   hora_tagplus_produto_map        de-para HoraModelo -> tagplus_produto_id
--   hora_tagplus_forma_pagamento_map de-para forma_pagamento HORA -> tagplus_forma_id
--   hora_tagplus_nfe_emissao        fila + historico de emissoes (fonte de verdade)
--
-- Idempotente (CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS hora_tagplus_conta (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(64) NOT NULL,
    client_secret_encrypted TEXT NOT NULL,
    webhook_secret VARCHAR(64) NOT NULL,
    oauth_state_last VARCHAR(64),
    scope_contratado VARCHAR(255) NOT NULL DEFAULT 'write:nfes read:clientes write:clientes read:produtos',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ambiente VARCHAR(15) NOT NULL DEFAULT 'producao',
    redirect_uri VARCHAR(500),
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em TIMESTAMP
);

-- Singleton: so 1 conta pode estar ativa simultaneamente.
CREATE UNIQUE INDEX IF NOT EXISTS uq_hora_tagplus_conta_ativa
    ON hora_tagplus_conta(ativo) WHERE ativo = TRUE;


CREATE TABLE IF NOT EXISTS hora_tagplus_token (
    id SERIAL PRIMARY KEY,
    conta_id INTEGER NOT NULL UNIQUE REFERENCES hora_tagplus_conta(id) ON DELETE CASCADE,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,
    token_type VARCHAR(20) NOT NULL DEFAULT 'bearer',
    expires_at TIMESTAMP NOT NULL,
    obtido_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    refreshed_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_token_expires_at ON hora_tagplus_token(expires_at);


CREATE TABLE IF NOT EXISTS hora_tagplus_produto_map (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL UNIQUE REFERENCES hora_modelo(id),
    tagplus_produto_id INTEGER NOT NULL,
    tagplus_codigo VARCHAR(50),
    cfop_default VARCHAR(5) NOT NULL DEFAULT '5.102',
    -- VARCHAR(5) cabe "5.102" / "6.102" (mascara 9.999 doc_tagplus.md:178).
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em TIMESTAMP
);


CREATE TABLE IF NOT EXISTS hora_tagplus_forma_pagamento_map (
    id SERIAL PRIMARY KEY,
    forma_pagamento_hora VARCHAR(20) NOT NULL UNIQUE,
    -- enum HoraVenda.forma_pagamento: PIX / CARTAO_CREDITO / DINHEIRO.
    tagplus_forma_id INTEGER NOT NULL,
    -- ID inteiro no TagPlus (resolver via GET /formas_pagamento).
    descricao VARCHAR(80),
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em TIMESTAMP
);


CREATE TABLE IF NOT EXISTS hora_tagplus_nfe_emissao (
    id SERIAL PRIMARY KEY,
    venda_id INTEGER NOT NULL UNIQUE REFERENCES hora_venda(id),
    conta_id INTEGER NOT NULL REFERENCES hora_tagplus_conta(id),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDENTE',
    -- PENDENTE, EM_ENVIO, ENVIADA_SEFAZ, APROVADA,
    -- REJEITADA_LOCAL, REJEITADA_SEFAZ, ERRO_INFRA,
    -- CANCELAMENTO_SOLICITADO, CANCELADA
    tagplus_nfe_id INTEGER,
    numero_nfe VARCHAR(20),
    serie_nfe VARCHAR(5),
    chave_44 VARCHAR(44) UNIQUE,
    protocolo_aprovacao VARCHAR(30),
    payload_enviado JSONB,
    response_inicial JSONB,
    response_webhook JSONB,
    error_code VARCHAR(60),
    error_message TEXT,
    tentativas INTEGER NOT NULL DEFAULT 0,
    enviado_em TIMESTAMP,
    aprovado_em TIMESTAMP,
    cancelamento_justificativa TEXT,
    cancelamento_solicitado_por VARCHAR(100),
    cancelamento_solicitado_em TIMESTAMP,
    cancelado_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_nfe_status ON hora_tagplus_nfe_emissao(status);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_nfe_tagplus_id ON hora_tagplus_nfe_emissao(tagplus_nfe_id);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_nfe_conta ON hora_tagplus_nfe_emissao(conta_id);
