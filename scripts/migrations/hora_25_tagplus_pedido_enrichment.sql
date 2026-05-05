-- Migration HORA 25: enriquecimento de venda via GET /pedidos/{id} TagPlus.
--
-- Adiciona colunas para vincular NFe -> pedido_os_vinculada e persistir dados
-- coletados via /pedidos/{id} (vendedor, departamento/loja fisica, payload bruto).
-- Cria tabela de-para departamento -> loja para revisao humana pos-backfill.
-- Cria coluna scope_efetivo no token OAuth para detectar scope mismatch.
--
-- Idempotente — usa IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.

-- 1) Token OAuth: scope efetivo retornado pelo TagPlus (pode divergir de scope_contratado).
ALTER TABLE hora_tagplus_token
    ADD COLUMN IF NOT EXISTS scope_efetivo VARCHAR(255);

-- 2) NFe emissao: ID do pedido vinculado no TagPlus (auto-criado pelo TagPlus
--    quando NFe e confirmada). Chave para GET /pedidos/{id}.
ALTER TABLE hora_tagplus_nfe_emissao
    ADD COLUMN IF NOT EXISTS tagplus_pedido_id INTEGER;

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_nfe_emissao_tagplus_pedido_id
    ON hora_tagplus_nfe_emissao (tagplus_pedido_id);

-- 3) Venda: enriquecimento via pedido TagPlus.
--    - tagplus_pedido_id: redundancia controlada para queries diretas em hora_venda.
--    - tagplus_pedido_payload: JSON bruto do GET /pedidos/{id} (auditoria + reprocessamento).
--    - tagplus_departamento: descricao raw (ex.: "Praia Grande") — base para de-para.
ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS tagplus_pedido_id INTEGER;

ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS tagplus_pedido_payload JSONB;

ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS tagplus_departamento VARCHAR(100);

CREATE INDEX IF NOT EXISTS ix_hora_venda_tagplus_pedido_id
    ON hora_venda (tagplus_pedido_id);

CREATE INDEX IF NOT EXISTS ix_hora_venda_tagplus_departamento
    ON hora_venda (tagplus_departamento);

-- 4) De-para departamento TagPlus -> HoraLoja.
--    departamento_norm: chave UNIQUE normalizada (lowercase + sem acentos + strip).
--    departamento_raw: ultima forma vista em producao (pode variar entre vendas).
--    loja_id: NULL ate revisao humana. UPDATE em hora_venda.loja_id usa esse mapa.
CREATE TABLE IF NOT EXISTS hora_tagplus_departamento_map (
    id                       SERIAL PRIMARY KEY,
    departamento_norm        VARCHAR(200) NOT NULL UNIQUE,
    departamento_raw         VARCHAR(200) NOT NULL,
    loja_id                  INTEGER REFERENCES hora_loja(id),
    qtd_vendas_observadas    INTEGER NOT NULL DEFAULT 0,
    revisado_por             VARCHAR(100),
    revisado_em              TIMESTAMP,
    aplicado_em              TIMESTAMP,
    criado_em                TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em            TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_departamento_map_loja_id
    ON hora_tagplus_departamento_map (loja_id);

-- 5) Discriminador de tipo no job de backfill: NF (default, retrocompat) ou
--    PEDIDO_ENRIQUECIMENTO (novo backfill que enriquece via GET /pedidos/{id}).
ALTER TABLE hora_tagplus_backfill_job
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(30) NOT NULL DEFAULT 'NF';

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_backfill_job_tipo
    ON hora_tagplus_backfill_job (tipo);
