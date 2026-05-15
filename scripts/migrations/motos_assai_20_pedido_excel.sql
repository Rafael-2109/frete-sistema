-- Migration 20: Cria assai_pedido_excel (historico versionado de Excel).
-- UNIQUE (separacao_id, versao) — S13=a — proteger race em versao.
-- UNIQUE parcial (separacao_id) WHERE ativo=TRUE — apenas 1 ativo por sep.

BEGIN;

CREATE TABLE IF NOT EXISTS assai_pedido_excel (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    separacao_id INTEGER NOT NULL REFERENCES assai_separacao(id),
    s3_key VARCHAR(500) NOT NULL,
    versao INTEGER NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    gerado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    gerado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_regeneracao TEXT
);

CREATE INDEX IF NOT EXISTS ix_assai_pedido_excel_pedido
    ON assai_pedido_excel(pedido_id);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_excel_sep
    ON assai_pedido_excel(separacao_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_pedido_excel_sep_ativo
    ON assai_pedido_excel(separacao_id) WHERE ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_pedido_excel_sep_versao
    ON assai_pedido_excel(separacao_id, versao);

-- Garantir DEFAULT em gerado_em (caso tabela tenha sido criada sem DEFAULT em ambiente legado).
-- IDEMPOTENTE: ALTER COLUMN SET DEFAULT pode rodar varias vezes sem erro.
ALTER TABLE assai_pedido_excel
    ALTER COLUMN gerado_em SET DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo');

-- Backfill: copiar valor existente de assai_separacao.solicitacao_excel_s3_key
-- para novas linhas com versao=1, ativo=TRUE.
-- gerado_em incluido explicitamente como defesa-em-profundidade (caso o DEFAULT
-- nao tenha sido aplicado por algum motivo em prod legado).
INSERT INTO assai_pedido_excel (pedido_id, separacao_id, s3_key, versao, ativo, gerado_em, motivo_regeneracao)
SELECT
    s.pedido_id,
    s.id,
    s.solicitacao_excel_s3_key,
    1,
    TRUE,
    (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    'Backfill Migration 20 (legado solicitacao_excel_s3_key)'
FROM assai_separacao s
WHERE s.solicitacao_excel_s3_key IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM assai_pedido_excel pe WHERE pe.separacao_id = s.id
  );

COMMIT;
