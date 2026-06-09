-- Migration 2026-06-08 — Formato canonico de memorias: coluna meta JSONB
--
-- Objetivo: dar ao pool de memorias do agente uma FONTE DE VERDADE estruturada e
-- QUERYAVEL para os campos discriminantes (kind/dominio/nivel/criterios/titulo/
-- when/do/...), em vez de mante-los presos no texto livre da coluna `content`
-- (hoje com 5+ formatos fisicos distintos: bracket, <heuristica>, <conhecimento>,
-- XML em code-fence, pseudo-XML).
--
-- ADDITIVE e REVERSIVEL: a coluna `content` NAO e alterada por esta DDL. O backfill
-- (script Python separado) popula `meta` parseando o content legado e re-renderiza
-- o content para o formato sentinela canonico. Memorias nao-parseaveis ficam intactas.
--
-- Serializacao/parse: app/agente/services/memory_format.py
-- Indice GIN jsonb_path_ops: acelera APENAS o operador @> (containment), ex:
--   meta @> '{"dominio":"recebimento"}'  /  meta @> '{"kind":"armadilha"}'
-- ATENCAO: `meta->>'campo' = 'valor'` NAO usa este indice (seq scan) — para isso
-- seria preciso jsonb_ops (GIN padrao) OU expression index na chave. Os filtros
-- atuais (list_memories) sao em Python apos ORM load, nao no DB.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.

ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS meta JSONB;

CREATE INDEX IF NOT EXISTS ix_agent_memories_meta_gin
  ON agent_memories USING GIN (meta jsonb_path_ops);

COMMENT ON COLUMN agent_memories.meta IS 'Formato canonico 2026-06-08. Campos discriminantes estruturados (v, kind, dominio, nivel, criterios, titulo, when, do, evidencia, origem, parse). Fonte de verdade queryavel. content e derivado via render_content(meta). NULL = legada nao migrada ou nao-estruturada. Serializacao em app/agente/services/memory_format.py';
