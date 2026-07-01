-- Alertas de Faturamento por CNPJ (e-mail)
-- Spec: docs/superpowers/specs/2026-07-01-alertas-faturamento-cnpj-design.md

-- Teams foi removido: descarta a tabela de config (se existir de deploy anterior).
-- Segura (tabela sem FKs, vazia/desusada); no-op se nunca foi criada.
DROP TABLE IF EXISTS alerta_faturamento_config;

CREATE TABLE IF NOT EXISTS alerta_faturamento_cnpj (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(20) NOT NULL UNIQUE,
    nome_cliente VARCHAR(255),
    emails TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerta_faturamento_enviado (
    id SERIAL PRIMARY KEY,
    numero_nf VARCHAR(20) NOT NULL,
    cnpj VARCHAR(20),
    canal VARCHAR(10) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'ok',
    detalhe TEXT,
    enviado_em TIMESTAMP,
    CONSTRAINT uq_alerta_fat_enviado_nf_canal UNIQUE (numero_nf, canal)
);

CREATE INDEX IF NOT EXISTS ix_alerta_faturamento_enviado_numero_nf ON alerta_faturamento_enviado (numero_nf);
CREATE INDEX IF NOT EXISTS ix_alerta_faturamento_enviado_cnpj ON alerta_faturamento_enviado (cnpj);
