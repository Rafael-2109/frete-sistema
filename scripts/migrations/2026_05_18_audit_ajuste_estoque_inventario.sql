-- Migration: audit log append-only de ajuste_estoque_inventario
-- Captura todo INSERT/UPDATE/DELETE em ajuste_estoque_inventario via trigger
-- independente de origem (ORM, SQL direto, MCP, psql, scripts).
--
-- Decisao: 2026-05-18 — Rafael solicitou audit log apenas (sem bloqueio)
-- para o ciclo inventario 2026-05. Foco: forense de cancelamentos/reset
-- de ajustes EXECUTADO->PROPOSTO sem rastreio (caso NF 626032).
--
-- Idempotente: pode rodar varias vezes sem efeito colateral.

BEGIN;

-- =========================================================================
-- 1) TABELA APPEND-ONLY
-- =========================================================================
CREATE TABLE IF NOT EXISTS ajuste_estoque_inventario_audit (
    id              BIGSERIAL PRIMARY KEY,
    -- ajuste_id SEM FK proposital: preserva audit apos DELETE do ajuste original
    ajuste_id       INTEGER NOT NULL,
    tipo_evento     VARCHAR(10) NOT NULL
                    CHECK (tipo_evento IN ('INSERT','UPDATE','DELETE')),
    dados_antes     JSONB,
    dados_depois    JSONB,
    campos_alterados TEXT[],
    registrado_em   TIMESTAMP NOT NULL
                    DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    registrado_por  TEXT NOT NULL DEFAULT session_user,
    aplicacao       TEXT,
    client_addr     INET,
    transaction_id  BIGINT NOT NULL DEFAULT txid_current()
);

COMMENT ON TABLE ajuste_estoque_inventario_audit IS
    'Audit log append-only de ajuste_estoque_inventario. Populado por trigger. '
    'NUNCA fazer UPDATE/DELETE manual nesta tabela — e a fonte de verdade forense.';

COMMENT ON COLUMN ajuste_estoque_inventario_audit.ajuste_id IS
    'ID do ajuste original. Sem FK proposital — preserva audit apos DELETE.';
COMMENT ON COLUMN ajuste_estoque_inventario_audit.aplicacao IS
    'application_name da conexao (gunicorn/worker/psql/Claude Code). '
    'Setado via SET application_name = ''...'' ou parametro de conexao.';
COMMENT ON COLUMN ajuste_estoque_inventario_audit.transaction_id IS
    'txid_current() — correlaciona multiplas mudancas dentro da mesma transacao.';

-- =========================================================================
-- 2) INDICES
-- =========================================================================
CREATE INDEX IF NOT EXISTS idx_aei_audit_ajuste_time
    ON ajuste_estoque_inventario_audit (ajuste_id, registrado_em DESC);

CREATE INDEX IF NOT EXISTS idx_aei_audit_time
    ON ajuste_estoque_inventario_audit (registrado_em DESC);

CREATE INDEX IF NOT EXISTS idx_aei_audit_tx
    ON ajuste_estoque_inventario_audit (transaction_id);

-- Indice parcial: queries focadas em DELETEs (raros, criticos)
CREATE INDEX IF NOT EXISTS idx_aei_audit_deletes
    ON ajuste_estoque_inventario_audit (registrado_em DESC)
    WHERE tipo_evento = 'DELETE';

-- =========================================================================
-- 3) FUNCAO DE TRIGGER
-- =========================================================================
CREATE OR REPLACE FUNCTION audit_ajuste_estoque_inventario_fn()
RETURNS TRIGGER AS $$
DECLARE
    v_antes      JSONB;
    v_depois     JSONB;
    v_campos     TEXT[];
    v_aplicacao  TEXT;
BEGIN
    -- application_name pode nao estar setado em todas conexoes
    v_aplicacao := current_setting('application_name', true);
    IF v_aplicacao = '' THEN
        v_aplicacao := NULL;
    END IF;

    IF (TG_OP = 'INSERT') THEN
        INSERT INTO ajuste_estoque_inventario_audit
            (ajuste_id, tipo_evento, dados_antes, dados_depois,
             aplicacao, client_addr)
        VALUES
            (NEW.id, 'INSERT', NULL, to_jsonb(NEW),
             v_aplicacao, inet_client_addr());
        RETURN NEW;

    ELSIF (TG_OP = 'UPDATE') THEN
        v_antes  := to_jsonb(OLD);
        v_depois := to_jsonb(NEW);

        -- Diff: chaves cujo valor mudou (compara como JSON)
        SELECT array_agg(k ORDER BY k) INTO v_campos
        FROM (
            SELECT jsonb_object_keys(v_antes)  AS k
            UNION
            SELECT jsonb_object_keys(v_depois) AS k
        ) keys
        WHERE v_antes->k IS DISTINCT FROM v_depois->k;

        -- Skip UPDATEs no-op (sem mudanca real) — economiza espaco/ruido
        IF v_campos IS NULL OR array_length(v_campos, 1) = 0 THEN
            RETURN NEW;
        END IF;

        INSERT INTO ajuste_estoque_inventario_audit
            (ajuste_id, tipo_evento, dados_antes, dados_depois,
             campos_alterados, aplicacao, client_addr)
        VALUES
            (NEW.id, 'UPDATE', v_antes, v_depois,
             v_campos, v_aplicacao, inet_client_addr());
        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO ajuste_estoque_inventario_audit
            (ajuste_id, tipo_evento, dados_antes, dados_depois,
             aplicacao, client_addr)
        VALUES
            (OLD.id, 'DELETE', to_jsonb(OLD), NULL,
             v_aplicacao, inet_client_addr());
        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION audit_ajuste_estoque_inventario_fn() IS
    'Trigger function: insere linha em ajuste_estoque_inventario_audit '
    'para todo INSERT/UPDATE/DELETE. UPDATEs no-op (sem campos alterados) '
    'sao silenciosamente ignorados.';

-- =========================================================================
-- 4) TRIGGER (drop+create para idempotencia)
-- =========================================================================
DROP TRIGGER IF EXISTS audit_ajuste_estoque_inventario_trg
    ON ajuste_estoque_inventario;

CREATE TRIGGER audit_ajuste_estoque_inventario_trg
AFTER INSERT OR UPDATE OR DELETE ON ajuste_estoque_inventario
FOR EACH ROW EXECUTE FUNCTION audit_ajuste_estoque_inventario_fn();

COMMIT;
