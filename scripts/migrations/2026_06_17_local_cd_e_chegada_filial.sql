-- Migration: flag local_cd (CD de expedicao) + chegada_filial (monitoramento CarVia)
-- Data: 2026-06-17
-- Descricao:
--   Stream FUNDACAO do redesign CarVia (.claire/rascunho.md topicos 4 e 6).
--   Adiciona a coluna `local_cd` (Victorio Marchezine / Tenente Marques) nas 5 tabelas
--   que precisam exibir/operar a flag:
--     separacao, embarque_itens, controle_portaria, carvia_nfs, entregas_monitoradas.
--   Adiciona tambem em entregas_monitoradas os campos chegada_filial (bool + datahora)
--   p/ a etapa "Recebido Filial Entrega" do portal (so faz sentido p/ CarVia, mas a
--   coluna e generica e fica FALSE/NULL p/ Nacom).
--
--   BACKFILL automatico: ADD COLUMN ... NOT NULL DEFAULT 'VICTORIO_MARCHEZINE' preenche
--   TODOS os registros historicos com o default Nacom (topico 4D). Em PostgreSQL 11+
--   isso e metadata-only (rapido, sem reescrever a tabela).
--
--   NAO recria a VIEW pedidos — isso fica na migration v10 (alterar_view_pedidos_v10_local_cd).
-- Idempotente (ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).

-- ============================================================
-- 1. Colunas local_cd (NOT NULL default VM = backfill historico)
-- ============================================================
ALTER TABLE separacao
    ADD COLUMN IF NOT EXISTS local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE';

ALTER TABLE embarque_itens
    ADD COLUMN IF NOT EXISTS local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE';

ALTER TABLE controle_portaria
    ADD COLUMN IF NOT EXISTS local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE';

ALTER TABLE carvia_nfs
    ADD COLUMN IF NOT EXISTS local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE';

ALTER TABLE entregas_monitoradas
    ADD COLUMN IF NOT EXISTS local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE';

-- ============================================================
-- 2. chegada_filial (monitoramento) — "Recebido Filial Entrega"
-- ============================================================
ALTER TABLE entregas_monitoradas
    ADD COLUMN IF NOT EXISTS chegada_filial BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE entregas_monitoradas
    ADD COLUMN IF NOT EXISTS chegada_filial_em TIMESTAMP WITHOUT TIME ZONE;

-- ============================================================
-- 3. Indices (parciais: TM e minoria; VM e default dominante)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_sep_local_cd
    ON separacao (local_cd) WHERE local_cd <> 'VICTORIO_MARCHEZINE';
CREATE INDEX IF NOT EXISTS idx_ei_local_cd
    ON embarque_itens (local_cd);
CREATE INDEX IF NOT EXISTS idx_cp_local_cd
    ON controle_portaria (local_cd);
CREATE INDEX IF NOT EXISTS idx_carvia_nfs_local_cd
    ON carvia_nfs (local_cd) WHERE local_cd <> 'VICTORIO_MARCHEZINE';
CREATE INDEX IF NOT EXISTS idx_em_local_cd
    ON entregas_monitoradas (local_cd) WHERE local_cd <> 'VICTORIO_MARCHEZINE';
CREATE INDEX IF NOT EXISTS idx_em_chegada_filial
    ON entregas_monitoradas (chegada_filial) WHERE chegada_filial = true;
