-- Migration HORA 34: multiplas formas de pagamento por pedido + AUT/ID.
-- Idempotente.

-- 1. CREATE TABLE hora_venda_pagamento.
CREATE TABLE IF NOT EXISTS hora_venda_pagamento (
    id SERIAL PRIMARY KEY,
    venda_id INTEGER NOT NULL REFERENCES hora_venda(id) ON DELETE CASCADE,
    forma_pagamento_hora VARCHAR(20) NOT NULL,
    valor NUMERIC(15, 2) NOT NULL,
    numero_parcelas INTEGER NOT NULL DEFAULT 1,
    aut_id VARCHAR(50),
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_hora_venda_pag_valor_pos CHECK (valor > 0),
    CONSTRAINT ck_hora_venda_pag_parcelas_pos CHECK (numero_parcelas >= 1 AND numero_parcelas <= 60)
);

CREATE INDEX IF NOT EXISTS ix_hora_venda_pag_venda
    ON hora_venda_pagamento (venda_id);

-- 2. ALTER hora_tagplus_forma_pagamento_map: exige_aut_id.
ALTER TABLE hora_tagplus_forma_pagamento_map
    ADD COLUMN IF NOT EXISTS exige_aut_id BOOLEAN NOT NULL DEFAULT FALSE;

-- 3. Backfill: 1 pagamento por HoraVenda existente (skipa NAO_INFORMADO/NULL).
-- criado_em: preserva historico (criado_em > data_venda > NOW fallback).
INSERT INTO hora_venda_pagamento
    (venda_id, forma_pagamento_hora, valor, numero_parcelas, criado_em)
SELECT
    v.id,
    v.forma_pagamento,
    v.valor_total,
    COALESCE(v.numero_parcelas, 1),
    COALESCE(
        v.criado_em,
        v.data_venda::timestamp,
        NOW()
    )
FROM hora_venda v
WHERE v.forma_pagamento IS NOT NULL
  AND v.forma_pagamento <> ''
  AND v.forma_pagamento <> 'NAO_INFORMADO'
  AND v.valor_total IS NOT NULL
  AND v.valor_total > 0
  AND NOT EXISTS (
      SELECT 1 FROM hora_venda_pagamento p
      WHERE p.venda_id = v.id
  );

-- Verificacoes:
SELECT 'hora_venda_pagamento total' AS metrica, COUNT(*) FROM hora_venda_pagamento
UNION ALL
SELECT 'vendas com pagamento', COUNT(DISTINCT venda_id) FROM hora_venda_pagamento;
