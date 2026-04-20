-- Reconciliacao historica: auditorias ERRO em lancamentos que chegaram ao final.
--
-- Criterio: frete/despesa em LANCADO_ODOO OU auditoria etapa=16 SUCESSO
-- para o mesmo frete_id/despesa_extra_id. Qualquer linha ERRO do lancamento
-- e marcada como SUCESSO (com menssagem explicando que foi reconciliada).
--
-- Uso (Render Shell):
--   psql $DATABASE_URL -f scripts/migrations/reconciliar_auditoria_erro_to_sucesso.sql
--
-- Idempotente (so atualiza status='ERRO').

BEGIN;

-- Preview: contagem por etapa ANTES do UPDATE
SELECT '[ANTES] auditorias ERRO em lancamentos completos' AS info;

SELECT a.etapa, COUNT(*) AS qtd
  FROM lancamento_frete_odoo_auditoria a
  LEFT JOIN fretes f ON f.id = a.frete_id AND f.status = 'LANCADO_ODOO'
  LEFT JOIN despesas_extras d ON d.id = a.despesa_extra_id AND d.status = 'LANCADO_ODOO'
  LEFT JOIN LATERAL (
      SELECT 1 FROM lancamento_frete_odoo_auditoria a16
       WHERE a16.etapa = 16 AND a16.status = 'SUCESSO'
         AND (
             (a.frete_id IS NOT NULL AND a16.frete_id = a.frete_id)
          OR (a.despesa_extra_id IS NOT NULL AND a16.despesa_extra_id = a.despesa_extra_id)
         )
       LIMIT 1
  ) c16 ON TRUE
 WHERE a.status = 'ERRO'
   AND (f.id IS NOT NULL OR d.id IS NOT NULL OR c16 IS NOT NULL)
 GROUP BY a.etapa
 ORDER BY a.etapa;

-- UPDATE efetivo
WITH completos_frete AS (
    SELECT id AS frete_id, odoo_purchase_order_id AS po_final
      FROM fretes
     WHERE status = 'LANCADO_ODOO'
),
completos_despesa AS (
    SELECT id AS despesa_extra_id, odoo_purchase_order_id AS po_final
      FROM despesas_extras
     WHERE status = 'LANCADO_ODOO'
),
concluiu16 AS (
    SELECT DISTINCT frete_id, despesa_extra_id, purchase_order_id AS po_final
      FROM lancamento_frete_odoo_auditoria
     WHERE etapa = 16 AND status = 'SUCESSO'
),
alvos AS (
    SELECT
        a.id AS audit_id,
        COALESCE(a.purchase_order_id, cf.po_final, cd.po_final, c16f.po_final, c16d.po_final) AS po_final,
        CASE
            WHEN cf.frete_id IS NOT NULL THEN 'frete LANCADO_ODOO'
            WHEN cd.despesa_extra_id IS NOT NULL THEN 'despesa LANCADO_ODOO'
            WHEN c16f.frete_id IS NOT NULL THEN 'audit etapa 16 SUCESSO (frete)'
            WHEN c16d.despesa_extra_id IS NOT NULL THEN 'audit etapa 16 SUCESSO (despesa)'
        END AS fonte
      FROM lancamento_frete_odoo_auditoria a
      LEFT JOIN completos_frete cf ON cf.frete_id = a.frete_id AND a.frete_id IS NOT NULL
      LEFT JOIN completos_despesa cd ON cd.despesa_extra_id = a.despesa_extra_id AND a.despesa_extra_id IS NOT NULL
      LEFT JOIN concluiu16 c16f ON c16f.frete_id = a.frete_id AND a.frete_id IS NOT NULL
      LEFT JOIN concluiu16 c16d ON c16d.despesa_extra_id = a.despesa_extra_id AND a.despesa_extra_id IS NOT NULL
     WHERE a.status = 'ERRO'
       AND (
           cf.frete_id IS NOT NULL
        OR cd.despesa_extra_id IS NOT NULL
        OR c16f.frete_id IS NOT NULL
        OR c16d.despesa_extra_id IS NOT NULL
       )
)
UPDATE lancamento_frete_odoo_auditoria a
   SET status = 'SUCESSO',
       purchase_order_id = COALESCE(a.purchase_order_id, alvos.po_final),
       mensagem = COALESCE(a.mensagem, '')
           || ' | Reconciliado por SQL ('
           || to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI')
           || ' UTC): lancamento foi completado posteriormente (fonte: '
           || COALESCE(alvos.fonte, 'desconhecida') || ')'
  FROM alvos
 WHERE a.id = alvos.audit_id
   AND a.status = 'ERRO';

-- Verificacao pos-UPDATE
SELECT '[DEPOIS] auditorias ERRO remanescentes (legitimas)' AS info;

SELECT etapa, COUNT(*) AS qtd
  FROM lancamento_frete_odoo_auditoria
 WHERE status = 'ERRO'
 GROUP BY etapa
 ORDER BY etapa;

COMMIT;
