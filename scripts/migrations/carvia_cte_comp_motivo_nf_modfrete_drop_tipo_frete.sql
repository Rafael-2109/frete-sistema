-- Migration idempotente:
--   0. BACKUP tipo_frete + BACKFILL cte_tomador nas operacoes (preserva SOT)
--   1. ADD carvia_cte_complementares.motivo (varchar 500) — texto extraido de <ObsCont xCampo="2"><xTexto>MOTIVO: ...
--   2. ADD carvia_nfs.modalidade_frete (varchar 1)       — modFrete NF-e (0=CIF, 1=FOB, 2=Terceiros, 3/4=Proprio, 9=Sem)
--   3. DROP carvia_faturas_cliente.tipo_frete            — removido: SOT do tomador e o CTe, nao a fatura
--
-- Uso (Render Shell):
--   psql $DATABASE_URL -f scripts/migrations/carvia_cte_comp_motivo_nf_modfrete_drop_tipo_frete.sql

BEGIN;

-- 0a. BACKUP: preserva tipo_frete antes do DROP (auditoria retroativa)
CREATE TABLE IF NOT EXISTS carvia_faturas_cliente_tipo_frete_backup AS
    SELECT id, numero_fatura, cnpj_cliente, tipo_frete, status,
           NOW() AS backup_em
      FROM carvia_faturas_cliente
     WHERE 1 = 0;  -- cria schema vazio; populamos com INSERT condicional abaixo

-- Popula backup apenas se ainda nao ha registros (idempotente)
INSERT INTO carvia_faturas_cliente_tipo_frete_backup (id, numero_fatura, cnpj_cliente, tipo_frete, status, backup_em)
SELECT f.id, f.numero_fatura, f.cnpj_cliente, f.tipo_frete, f.status, NOW()
  FROM carvia_faturas_cliente f
 WHERE f.tipo_frete IS NOT NULL
   AND EXISTS (
       SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_faturas_cliente'
          AND column_name = 'tipo_frete'
   )
   AND NOT EXISTS (
       SELECT 1 FROM carvia_faturas_cliente_tipo_frete_backup b
        WHERE b.id = f.id
   );

-- 0b. BACKFILL: popula cte_tomador das operacoes cuja fatura tinha tipo_frete
--     Regra (corrigida R19): FOB=DESTINATARIO, CIF=REMETENTE
--     So atualiza se cte_tomador IS NULL (nao sobrescreve SOT do XML).
--     Idempotente por natureza (WHERE cte_tomador IS NULL).
UPDATE carvia_operacoes op
   SET cte_tomador = CASE f.tipo_frete
                         WHEN 'FOB' THEN 'DESTINATARIO'
                         WHEN 'CIF' THEN 'REMETENTE'
                     END
  FROM carvia_faturas_cliente f
 WHERE op.fatura_cliente_id = f.id
   AND op.cte_tomador IS NULL
   AND f.tipo_frete IN ('FOB', 'CIF')
   AND EXISTS (
       SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_faturas_cliente'
          AND column_name = 'tipo_frete'
   );

-- 1. CTe Complementar: motivo (generico, nao apenas descarga)
ALTER TABLE carvia_cte_complementares
    ADD COLUMN IF NOT EXISTS motivo VARCHAR(500);

COMMENT ON COLUMN carvia_cte_complementares.motivo IS
    'Texto extraido de <compl>/<ObsCont xCampo="N">/<xTexto> iniciando por "MOTIVO:". Preservado integral (descarga, reentrega, pedagio, etc).';

-- 2. NF-e: modalidade_frete (SEFAZ modFrete)
ALTER TABLE carvia_nfs
    ADD COLUMN IF NOT EXISTS modalidade_frete VARCHAR(1);

COMMENT ON COLUMN carvia_nfs.modalidade_frete IS
    'Campo <transp>/<modFrete> da NF-e. 0=CIF (remetente contrata), 1=FOB (destinatario contrata), 2=Terceiros, 3=Proprio Rem, 4=Proprio Dest, 9=Sem transporte.';

-- 3. Fatura Cliente: drop tipo_frete (obsoleto — SOT = CTe.cte_tomador)
ALTER TABLE carvia_faturas_cliente
    DROP COLUMN IF EXISTS tipo_frete;

-- Verificacao (resultados aparecem no log do psql antes do COMMIT)
SELECT 'carvia_cte_complementares.motivo' AS campo,
       COUNT(*) FILTER (WHERE motivo IS NOT NULL) AS com_valor,
       COUNT(*) AS total
  FROM carvia_cte_complementares
 UNION ALL
SELECT 'carvia_nfs.modalidade_frete',
       COUNT(*) FILTER (WHERE modalidade_frete IS NOT NULL),
       COUNT(*)
  FROM carvia_nfs;

SELECT 'backup tipo_frete preservado' AS info,
       COUNT(*) AS registros
  FROM carvia_faturas_cliente_tipo_frete_backup;

SELECT 'cte_tomador populado por backfill' AS info,
       COUNT(*) AS operacoes_com_tomador
  FROM carvia_operacoes
 WHERE cte_tomador IS NOT NULL;

SELECT 'tipo_frete existe em carvia_faturas_cliente?' AS check,
       EXISTS (
           SELECT 1 FROM information_schema.columns
            WHERE table_name = 'carvia_faturas_cliente'
              AND column_name = 'tipo_frete'
       ) AS ainda_existe;

COMMIT;
