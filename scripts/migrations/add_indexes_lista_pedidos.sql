-- Indexes para otimizar a rota /pedidos/lista_pedidos
-- Executar no Render Shell (PostgreSQL)
-- Usar CONCURRENTLY para zero downtime

-- Partial index: falta_item (maioria e false, index fica muito pequeno)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_falta_item_sync
    ON separacao (falta_item, sincronizado_nf) WHERE falta_item = true;

-- Partial index: falta_pagamento
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_falta_pgto_sync
    ON separacao (falta_pagamento, sincronizado_nf) WHERE falta_pagamento = true;

-- Partial index: nf_cd
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_nf_cd
    ON separacao (nf_cd) WHERE nf_cd = true;
