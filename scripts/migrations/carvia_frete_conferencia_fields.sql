-- Migration: Add campos de conferencia em carvia_fretes (Escopo C refactor)
-- Data: 2026-04-14
-- Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md

-- 1. Adicionar 5 colunas idempotente
ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS status_conferencia VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS conferido_por VARCHAR(100);

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS conferido_em TIMESTAMP;

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS detalhes_conferencia JSON;

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS requer_aprovacao BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Index para status_conferencia
CREATE INDEX IF NOT EXISTS idx_carvia_fretes_status_conferencia
  ON carvia_fretes (status_conferencia);

-- 3. Backfill: consolidar status_conferencia dos subs para frete pai
-- Logica:
--   Se algum sub DIVERGENTE → frete DIVERGENTE
--   Se TODOS subs APROVADO → frete APROVADO
--   Senao → frete PENDENTE (default)
WITH consolidacao AS (
  SELECT
    s.frete_id,
    COUNT(*) AS total,
    SUM(CASE WHEN s.status_conferencia = 'APROVADO' THEN 1 ELSE 0 END) AS aprovados,
    SUM(CASE WHEN s.status_conferencia = 'DIVERGENTE' THEN 1 ELSE 0 END) AS divergentes,
    MAX(s.conferido_por) AS conferido_por_any,
    MAX(s.conferido_em) AS conferido_em_max,
    BOOL_OR(s.requer_aprovacao) AS algum_requer_aprovacao
  FROM carvia_subcontratos s
  WHERE s.frete_id IS NOT NULL
  GROUP BY s.frete_id
)
UPDATE carvia_fretes f
SET
  status_conferencia = CASE
    WHEN c.divergentes > 0 THEN 'DIVERGENTE'
    WHEN c.aprovados = c.total THEN 'APROVADO'
    ELSE 'PENDENTE'
  END,
  conferido_por = CASE WHEN c.aprovados = c.total THEN c.conferido_por_any ELSE NULL END,
  conferido_em  = CASE WHEN c.aprovados = c.total THEN c.conferido_em_max ELSE NULL END,
  requer_aprovacao = COALESCE(c.algum_requer_aprovacao, FALSE)
FROM consolidacao c
WHERE f.id = c.frete_id
  AND f.status_conferencia = 'PENDENTE';

-- 4. Backfill valor_considerado (agrega sum dos subs)
UPDATE carvia_fretes f
SET valor_considerado = COALESCE(f.valor_considerado, subtotal.soma)
FROM (
  SELECT frete_id, SUM(valor_considerado) AS soma
  FROM carvia_subcontratos
  WHERE frete_id IS NOT NULL AND valor_considerado IS NOT NULL
  GROUP BY frete_id
) subtotal
WHERE f.id = subtotal.frete_id
  AND f.valor_considerado IS NULL;

-- 5. Backfill valor_pago (agrega sum dos subs)
UPDATE carvia_fretes f
SET valor_pago = COALESCE(f.valor_pago, subtotal.soma)
FROM (
  SELECT frete_id, SUM(valor_pago) AS soma
  FROM carvia_subcontratos
  WHERE frete_id IS NOT NULL AND valor_pago IS NOT NULL
  GROUP BY frete_id
) subtotal
WHERE f.id = subtotal.frete_id
  AND f.valor_pago IS NULL;
