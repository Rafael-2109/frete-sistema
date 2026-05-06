-- Migration HORA 29: unificacao de modelos (N nomes -> 1 modelo canonico)
--
-- Problema resolvido:
--   - TagPlus, NFs e pedidos podem se referir ao mesmo modelo fisico com
--     descricoes divergentes (ex: BOB, BOB AM, SCOOTER ELETRICA BOB todas
--     sao MT-BOB / tagplus_id=10).
--   - O codigo antigo criava HoraModelo distintos para cada nome via
--     buscar_ou_criar_modelo. Resultado: 7 grupos de duplicacao no banco
--     (vide hora_31_sugestoes_merge.py).
--
-- Solucao:
--   1. hora_modelo_alias  -> N nomes (de qualquer origem) que apontam para
--      1 modelo canonico. Resolver de ingestao consulta esta tabela.
--   2. hora_modelo_pendente -> fila de nomes desconhecidos aguardando
--      decisao do operador (vincular a modelo existente OU criar novo).
--      Sistema NAO cria modelos silenciosamente.
--   3. hora_modelo (ALTER) -> 3 colunas de auditoria de merge fisico
--      (modelo absorvido por outro fica ativo=False + merged_em_id).
--
-- Idempotente — usa IF NOT EXISTS.

-- ------------------------------------------------------------------------
-- Tabela 1: hora_modelo_alias (N nomes -> 1 modelo canonico)
-- ------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hora_modelo_alias (
    id              SERIAL PRIMARY KEY,
    modelo_id       INTEGER NOT NULL REFERENCES hora_modelo(id) ON DELETE CASCADE,
    nome_alias      VARCHAR(200) NOT NULL,
    tipo            VARCHAR(30) NOT NULL,
    -- Valores: TAGPLUS_PRODUTO_ID, TAGPLUS_CODIGO, NOME_NF,
    --          NOME_PEDIDO, NOME_LIVRE.
    criado_em       TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100),
    observacao      TEXT,
    -- 1 alias mapeia para no maximo 1 canonico (evita conflito).
    CONSTRAINT uq_hora_modelo_alias_tipo_nome UNIQUE (tipo, nome_alias)
);

CREATE INDEX IF NOT EXISTS ix_hora_modelo_alias_modelo_id
    ON hora_modelo_alias (modelo_id);

CREATE INDEX IF NOT EXISTS ix_hora_modelo_alias_tipo
    ON hora_modelo_alias (tipo);

-- ------------------------------------------------------------------------
-- Tabela 2: hora_modelo_pendente (fila de nomes nao reconhecidos)
-- ------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hora_modelo_pendente (
    id                  SERIAL PRIMARY KEY,
    nome_observado      VARCHAR(200) NOT NULL,
    origem              VARCHAR(30) NOT NULL,
    -- Valores: TAGPLUS_BACKFILL, NF_ENTRADA, PEDIDO_MANUAL, DANFE_PDF,
    --          RECEBIMENTO.
    origem_id           INTEGER,
    -- ID da entidade que disparou (venda_id, nf_id, pedido_id, etc).
    -- Sem FK porque N tabelas distintas. Usado apenas para rastreio
    -- humano via UI; backend resolve retroatividade via JOIN textual.

    tagplus_codigo      VARCHAR(50),
    tagplus_produto_id  VARCHAR(50),
    -- Preenchidos apenas quando origem=TAGPLUS_BACKFILL.

    qtd_ocorrencias     INTEGER NOT NULL DEFAULT 1,
    -- Incrementado a cada nova ingestao com o mesmo nome+origem.

    primeiro_visto      TIMESTAMP NOT NULL DEFAULT NOW(),
    ultimo_visto        TIMESTAMP NOT NULL DEFAULT NOW(),

    status              VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    -- Valores: PENDENTE, VINCULADO, NOVO_MODELO, IGNORADO.

    resolvido_modelo_id INTEGER REFERENCES hora_modelo(id),
    -- Preenchido quando status in (VINCULADO, NOVO_MODELO).

    resolvido_em        TIMESTAMP,
    resolvido_por       VARCHAR(100),
    observacao          TEXT,

    -- Mesmo nome em mesma origem = 1 unica linha (incrementa qtd_ocorrencias).
    CONSTRAINT uq_hora_modelo_pendente_nome_origem UNIQUE (nome_observado, origem)
);

CREATE INDEX IF NOT EXISTS ix_hora_modelo_pendente_status
    ON hora_modelo_pendente (status);

CREATE INDEX IF NOT EXISTS ix_hora_modelo_pendente_origem
    ON hora_modelo_pendente (origem);

CREATE INDEX IF NOT EXISTS ix_hora_modelo_pendente_resolvido
    ON hora_modelo_pendente (resolvido_modelo_id);

-- ------------------------------------------------------------------------
-- ALTER hora_modelo: auditoria de merge fisico
-- ------------------------------------------------------------------------
ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS merged_em_id INTEGER;
ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS merged_em TIMESTAMP;
ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS merged_por VARCHAR(100);

-- FK self-reference (so aplicada se ainda nao existe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_hora_modelo_merged_em'
          AND table_name = 'hora_modelo'
    ) THEN
        ALTER TABLE hora_modelo
            ADD CONSTRAINT fk_hora_modelo_merged_em
            FOREIGN KEY (merged_em_id) REFERENCES hora_modelo(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_hora_modelo_merged_em_id
    ON hora_modelo (merged_em_id);
