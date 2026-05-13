-- Migration 18: Cria assai_carregamento + assai_carregamento_item.
-- Decisao: SEM UNIQUE em (pedido, loja, EM_CARREGAMENTO) — A2.
-- Enforcement: lock pessimista em assai_moto via service (S3=c).

BEGIN;

CREATE TABLE IF NOT EXISTS assai_carregamento (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    separacao_id INTEGER REFERENCES assai_separacao(id),
    status VARCHAR(20) NOT NULL DEFAULT 'EM_CARREGAMENTO',
    iniciado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    iniciado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    finalizado_em TIMESTAMP,
    finalizado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    cancelado_em TIMESTAMP,
    cancelado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_cancelamento TEXT,
    CONSTRAINT ck_assai_carregamento_status
        CHECK (status IN ('EM_CARREGAMENTO', 'FINALIZADO', 'CANCELADO'))
);

CREATE INDEX IF NOT EXISTS ix_assai_carregamento_pedido_loja
    ON assai_carregamento(pedido_id, loja_id);
CREATE INDEX IF NOT EXISTS ix_assai_carregamento_status
    ON assai_carregamento(status);
CREATE INDEX IF NOT EXISTS ix_assai_carregamento_separacao
    ON assai_carregamento(separacao_id) WHERE separacao_id IS NOT NULL;

-- Q2: 1 carregamento FINALIZADO ↔ 1 sep
CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_carregamento_sep
    ON assai_carregamento(separacao_id)
    WHERE separacao_id IS NOT NULL AND status = 'FINALIZADO';

CREATE TABLE IF NOT EXISTS assai_carregamento_item (
    id SERIAL PRIMARY KEY,
    carregamento_id INTEGER NOT NULL REFERENCES assai_carregamento(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    escaneado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    escaneado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_assai_carregamento_item_carregamento
    ON assai_carregamento_item(carregamento_id);
CREATE INDEX IF NOT EXISTS ix_assai_carregamento_item_chassi
    ON assai_carregamento_item(chassi);

-- A2: SEM UNIQUE chassi-em-carregamento-ativo. Enforcement via service
-- (lock pessimista em assai_moto). Subquery em indice parcial nao e suportada em PG.

COMMIT;
