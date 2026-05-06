-- Migration HORA 33: preço A vista/A prazo + tipo de pagamento + desconto %
--
-- Objetivo: permitir que o cadastro de modelo grave 2 preços (à vista / a prazo),
-- que cada forma de pagamento seja classificada como A_VISTA ou A_PRAZO, e que
-- cada item de venda registre o desconto também em percentual (alem de R$).
--
-- Mudanças:
--   1. hora_modelo  -> +preco_a_vista, +preco_a_prazo (NUMERIC(15,2), opcional)
--   2. hora_tagplus_forma_pagamento_map -> +tipo_pagamento VARCHAR(10)
--      (valores esperados: 'A_VISTA', 'A_PRAZO'; NULL = nao classificada)
--   3. hora_venda_item -> +desconto_percentual NUMERIC(5,2) NOT NULL DEFAULT 0
--
-- Idempotente — usa IF NOT EXISTS.

-- ------------------------------------------------------------------------
-- 1. hora_modelo: 2 colunas de preço (sem histórico/vigência)
-- ------------------------------------------------------------------------
ALTER TABLE hora_modelo
    ADD COLUMN IF NOT EXISTS preco_a_vista NUMERIC(15, 2);

ALTER TABLE hora_modelo
    ADD COLUMN IF NOT EXISTS preco_a_prazo NUMERIC(15, 2);

-- ------------------------------------------------------------------------
-- 2. hora_tagplus_forma_pagamento_map: classificação A vista / A prazo
-- ------------------------------------------------------------------------
ALTER TABLE hora_tagplus_forma_pagamento_map
    ADD COLUMN IF NOT EXISTS tipo_pagamento VARCHAR(10);

-- CHECK constraint (idempotente — só cria se ainda não existe).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'ck_hora_tagplus_forma_pgto_tipo'
          AND table_name = 'hora_tagplus_forma_pagamento_map'
    ) THEN
        ALTER TABLE hora_tagplus_forma_pagamento_map
            ADD CONSTRAINT ck_hora_tagplus_forma_pgto_tipo
            CHECK (tipo_pagamento IS NULL OR tipo_pagamento IN ('A_VISTA', 'A_PRAZO'));
    END IF;
END $$;

-- ------------------------------------------------------------------------
-- 3. hora_venda_item: desconto em percentual (alem do R$ ja existente)
-- ------------------------------------------------------------------------
ALTER TABLE hora_venda_item
    ADD COLUMN IF NOT EXISTS desconto_percentual NUMERIC(5, 2) NOT NULL DEFAULT 0;
