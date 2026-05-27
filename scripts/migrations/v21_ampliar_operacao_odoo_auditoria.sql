-- Migration v21+ G-AUDIT-2 (2026-05-27) — ampliar colunas VARCHAR pequenas
-- de operacao_odoo_auditoria que estouravam com nomes longos da Skill 5 v15a.
--
-- Incidente: pipeline real v21+ crashou em F5a por
--   StringDataRightTruncation: value too long for type character varying(20)
-- quando Skill 5 v15a tentou INSERT acao='criar_picking_inter_company' (27 chars).
--
-- Outros nomes longos:
--   - validar_picking_inter_company           (28 chars)
--   - criar_picking_entrada_destino_manual    (37 chars)
--   - aplicar_peso_volumes_fallback           (29 chars)
--
-- Idempotente: ALTER COLUMN TYPE só roda se necessário (sem CHECK explícito
-- pois PostgreSQL aceita re-ampliar para mesmo tamanho).

ALTER TABLE operacao_odoo_auditoria ALTER COLUMN acao TYPE VARCHAR(60);
ALTER TABLE operacao_odoo_auditoria ALTER COLUMN status TYPE VARCHAR(30);
ALTER TABLE operacao_odoo_auditoria ALTER COLUMN pipeline_etapa TYPE VARCHAR(40);
