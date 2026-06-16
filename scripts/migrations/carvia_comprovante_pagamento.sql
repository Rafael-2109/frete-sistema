-- CarVia — Comprovantes de Pagamento + flag "Cotacao Paga"
-- Data: 2026-06-16. Idempotente. Safe para re-execucao.
-- Spec: docs/superpowers/specs/2026-06-16-carvia-comprovantes-pagamento-design.md
--
-- (1) Tabela carvia_comprovantes_pagamento (arquivo S3 + metadados de conciliacao)
-- (2) Tabela carvia_comprovante_vinculos (N:N polimorfico comprovante <-> documento)
-- (3) Colunas pago/pago_em/pago_por em carvia_cotacoes (pagamento antecipado)
--
-- Nota: db.create_all() no boot tambem cria (1) e (2); este DDL e a fonte
-- canonica/rastreavel e cobre (3), que create_all NAO faz (tabela ja existente).

-- (1) Comprovantes
CREATE TABLE IF NOT EXISTS carvia_comprovantes_pagamento (
    id              SERIAL PRIMARY KEY,
    nome_original   VARCHAR(255) NOT NULL,
    nome_arquivo    VARCHAR(255) NOT NULL,
    caminho_s3      VARCHAR(500) NOT NULL,
    tamanho_bytes   INTEGER,
    content_type    VARCHAR(100),
    valor           NUMERIC(15,2),
    data_pagamento  DATE,
    cnpj_pagador    VARCHAR(20),
    descricao       TEXT,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    criado_por      VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_carvia_comprovantes_pagamento_cnpj_pagador
    ON carvia_comprovantes_pagamento (cnpj_pagador);
CREATE INDEX IF NOT EXISTS ix_carvia_comprovantes_pagamento_ativo
    ON carvia_comprovantes_pagamento (ativo);

-- (2) Vinculos N:N polimorficos (comprovante <-> cotacao/nf/operacao/fatura_cliente)
CREATE TABLE IF NOT EXISTS carvia_comprovante_vinculos (
    id              SERIAL PRIMARY KEY,
    comprovante_id  INTEGER NOT NULL REFERENCES carvia_comprovantes_pagamento(id) ON DELETE CASCADE,
    entidade_tipo   VARCHAR(30) NOT NULL,
    entidade_id     INTEGER NOT NULL,
    origem          VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
    criado_em       TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    criado_por      VARCHAR(100) NOT NULL,
    CONSTRAINT uq_carvia_comprovante_vinculo UNIQUE (comprovante_id, entidade_tipo, entidade_id)
);
CREATE INDEX IF NOT EXISTS ix_carvia_comprovante_vinculos_comprovante_id
    ON carvia_comprovante_vinculos (comprovante_id);
CREATE INDEX IF NOT EXISTS ix_carvia_comprovante_vinculo_entidade
    ON carvia_comprovante_vinculos (entidade_tipo, entidade_id);

-- (3) Flag "Cotacao Paga" (pagamento antecipado) em carvia_cotacoes
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS pago     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS pago_em  TIMESTAMP;
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS pago_por VARCHAR(100);
