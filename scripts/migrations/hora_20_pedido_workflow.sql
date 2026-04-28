-- Migration HORA 20: Workflow completo de pedido de venda.
-- 1) ALTER hora_venda: novos campos de transicao (confirmado_em/por,
--    cancelado_em/por, cancelamento_motivo).
-- 2) ALTER hora_venda.status DEFAULT='COTACAO'.
-- 3) Migracao de dados legados:
--    - 'CONCLUIDA' com nf_saida_chave_44 NOT NULL  -> 'FATURADO'
--    - 'CONCLUIDA' sem nf_saida_chave_44           -> 'CONFIRMADO' (legado validado)
--    - 'DEVOLVIDA'                                 -> 'CANCELADO'
-- 4) CREATE TABLE hora_venda_auditoria (append-only).
-- Idempotente.

-- ============================================================
-- 1. Novos campos em hora_venda
-- ============================================================
ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS confirmado_em TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS confirmado_por VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS cancelado_em TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS cancelado_por VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS cancelamento_motivo VARCHAR(500) NULL,
    ADD COLUMN IF NOT EXISTS faturado_em TIMESTAMP NULL;

-- ============================================================
-- 2. Default novo do status
-- ============================================================
ALTER TABLE hora_venda
    ALTER COLUMN status SET DEFAULT 'COTACAO';

-- ============================================================
-- 3. Migracao de dados legados
-- ============================================================
-- 3a. CONCLUIDA com NF emitida -> FATURADO (preserva faturado_em a partir de
--     nf_saida_emitida_em quando disponivel, senao criado_em).
UPDATE hora_venda
SET status = 'FATURADO',
    faturado_em = COALESCE(nf_saida_emitida_em, criado_em)
WHERE status = 'CONCLUIDA'
  AND nf_saida_chave_44 IS NOT NULL;

-- 3b. CONCLUIDA sem NF -> CONFIRMADO (decisao do usuario: pedidos legados
--     ja passaram por validacao manual).
UPDATE hora_venda
SET status = 'CONFIRMADO',
    confirmado_em = COALESCE(criado_em, CURRENT_TIMESTAMP),
    confirmado_por = COALESCE(vendedor, 'migracao_hora_20')
WHERE status = 'CONCLUIDA'
  AND nf_saida_chave_44 IS NULL;

-- 3c. DEVOLVIDA -> CANCELADO (raro/inexistente, mas preserva).
UPDATE hora_venda
SET status = 'CANCELADO',
    cancelado_em = COALESCE(criado_em, CURRENT_TIMESTAMP),
    cancelado_por = 'migracao_hora_20',
    cancelamento_motivo = 'Migracao: status legado DEVOLVIDA convertido para CANCELADO'
WHERE status = 'DEVOLVIDA';

-- ============================================================
-- 3.5. hora_venda_item: remover UNIQUE em numero_chassi
-- ============================================================
-- Motivo: pedido cancelado devolve chassi ao estoque, permitindo nova venda.
-- A UNIQUE original bloqueava re-venda. Defesa contra double-sell agora e via
-- lock pessimista (SELECT FOR UPDATE em hora_moto) + check do ultimo evento.
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT con.conname INTO constraint_name
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'hora_venda_item'
      AND con.contype = 'u'
      AND con.conkey = ARRAY[(
          SELECT attnum FROM pg_attribute
          WHERE attrelid = rel.oid AND attname = 'numero_chassi'
      )::smallint];
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE hora_venda_item DROP CONSTRAINT %I', constraint_name);
    END IF;
END$$;

-- Indice nao-unico para preservar performance da busca por chassi.
CREATE INDEX IF NOT EXISTS ix_hora_venda_item_chassi
    ON hora_venda_item(numero_chassi);

-- ============================================================
-- 4. Tabela de auditoria
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_venda_auditoria (
    id BIGSERIAL PRIMARY KEY,
    venda_id INTEGER NOT NULL REFERENCES hora_venda(id) ON DELETE CASCADE,
    item_id INTEGER NULL REFERENCES hora_venda_item(id) ON DELETE SET NULL,
    usuario VARCHAR(100) NOT NULL,
    acao VARCHAR(40) NOT NULL,
    campo_alterado VARCHAR(60) NULL,
    valor_antes TEXT NULL,
    valor_depois TEXT NULL,
    detalhe TEXT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Corrige FK item_id em instalacoes que criaram a tabela sem ON DELETE SET NULL.
DO $$
DECLARE
    fk_name TEXT;
BEGIN
    SELECT con.conname INTO fk_name
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'hora_venda_auditoria'
      AND con.contype = 'f'
      AND con.confdeltype = 'a'  -- 'a' = NO ACTION
      AND con.conkey = ARRAY[(
          SELECT attnum FROM pg_attribute
          WHERE attrelid = rel.oid AND attname = 'item_id'
      )::smallint];
    IF fk_name IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE hora_venda_auditoria DROP CONSTRAINT %I', fk_name
        );
        EXECUTE 'ALTER TABLE hora_venda_auditoria
                 ADD CONSTRAINT hora_venda_auditoria_item_id_fkey
                 FOREIGN KEY (item_id) REFERENCES hora_venda_item(id) ON DELETE SET NULL';
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS ix_hora_venda_auditoria_venda
    ON hora_venda_auditoria(venda_id);
CREATE INDEX IF NOT EXISTS ix_hora_venda_auditoria_item
    ON hora_venda_auditoria(item_id);
CREATE INDEX IF NOT EXISTS ix_hora_venda_auditoria_acao
    ON hora_venda_auditoria(acao);
CREATE INDEX IF NOT EXISTS ix_hora_venda_auditoria_timeline
    ON hora_venda_auditoria(venda_id, criado_em DESC);
