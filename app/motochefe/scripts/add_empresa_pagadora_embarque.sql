-- Migration: Adicionar empresa_pagadora_id ao EmbarqueMoto
-- Data: 2025-01-08
-- Objetivo: Rastrear qual empresa pagou o frete do embarque (consistente com DespesaMensal)

-- 1. ADICIONAR COLUNA empresa_pagadora_id
ALTER TABLE embarque_moto
ADD COLUMN IF NOT EXISTS empresa_pagadora_id INTEGER;

-- 2. ADICIONAR FOREIGN KEY
ALTER TABLE embarque_moto
ADD CONSTRAINT fk_embarque_empresa_pagadora
FOREIGN KEY (empresa_pagadora_id)
REFERENCES empresa_venda_moto(id);

-- 3. ADICIONAR ÍNDICE
CREATE INDEX IF NOT EXISTS ix_embarque_moto_empresa_pagadora_id
ON embarque_moto(empresa_pagadora_id);

-- 4. COMENTÁRIOS
COMMENT ON COLUMN embarque_moto.empresa_pagadora_id IS 'Empresa que pagou o frete (FK para empresa_venda_moto)';

-- VERIFICAÇÃO
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'embarque_moto'
  AND column_name = 'empresa_pagadora_id';
