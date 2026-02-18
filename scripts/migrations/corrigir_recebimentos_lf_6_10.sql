-- Correção de dados — Recebimentos LF IDs 6-10 (incidente 2026-02-18)
-- ====================================================================
-- Executar no Render Shell (psql) ou via query_render_postgres
--
-- Contexto:
--   IDs 6-7: Worker morto por deploy (status 'processando' etapa 3)
--   ID 8: Step 25 fez match com CTe 33120 (DFe errado)
--   ID 9: OK (nenhuma ação)
--   ID 10: Robot timeout (retry-transfer resolve)
--
-- IMPORTANTE: Verificar estado atual ANTES de executar:
--   SELECT id, status, etapa_atual, transfer_status, odoo_cd_dfe_id
--   FROM recebimento_lf WHERE id IN (6,7,8,9,10);

-- IDs 6-7: Reset para 'erro' (somente se ainda estão 'processando')
UPDATE recebimento_lf
SET status = 'erro',
    erro_mensagem = 'Processamento interrompido (deploy worker 2026-02-18 15:56). Corrigido por script.'
WHERE id IN (6, 7)
  AND status = 'processando';

-- ID 8: Limpar DFe CD errado (CTe 33120) e resetar para etapa 24
UPDATE recebimento_lf
SET odoo_cd_dfe_id = NULL,
    odoo_cd_po_id = NULL,
    odoo_cd_po_name = NULL,
    odoo_cd_invoice_id = NULL,
    odoo_cd_invoice_name = NULL,
    etapa_atual = 24,
    transfer_status = 'erro',
    transfer_erro_mensagem = 'Corrigido: DFe CD 33120 era CTe (match errado). Resetado para etapa 24.'
WHERE id = 8
  AND odoo_cd_dfe_id = 33120;

-- Verificação pós-correção
SELECT id, status, etapa_atual, transfer_status, odoo_cd_dfe_id, erro_mensagem
FROM recebimento_lf
WHERE id IN (6, 7, 8, 9, 10)
ORDER BY id;
