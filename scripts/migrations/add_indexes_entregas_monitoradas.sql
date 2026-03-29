-- Migration: Indexes de performance para entregas_monitoradas
-- Colunas filtradas frequentemente sem indice
-- Data: 2026-03-29

-- Indexes simples para colunas de filtro
CREATE INDEX IF NOT EXISTS idx_em_status_finalizacao ON entregas_monitoradas (status_finalizacao);
CREATE INDEX IF NOT EXISTS idx_em_data_embarque ON entregas_monitoradas (data_embarque);
CREATE INDEX IF NOT EXISTS idx_em_data_agenda ON entregas_monitoradas (data_agenda);
CREATE INDEX IF NOT EXISTS idx_em_data_faturamento ON entregas_monitoradas (data_faturamento);
CREATE INDEX IF NOT EXISTS idx_em_transportadora ON entregas_monitoradas (transportadora);

-- Partial indexes para booleans (tabelas pequenas, alta seletividade)
CREATE INDEX IF NOT EXISTS idx_em_entregue ON entregas_monitoradas (entregue) WHERE entregue = false;
CREATE INDEX IF NOT EXISTS idx_em_nf_cd ON entregas_monitoradas (nf_cd) WHERE nf_cd = true;
CREATE INDEX IF NOT EXISTS idx_em_reagendar ON entregas_monitoradas (reagendar) WHERE reagendar = true;

-- Atualizar estatisticas apos criar indexes
ANALYZE entregas_monitoradas;
