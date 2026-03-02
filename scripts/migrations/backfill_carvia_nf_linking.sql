-- ==========================================================================
-- Backfill: CarVia NF Linking — NFs referencia
-- ==========================================================================
--
-- Cria CarviaNf stubs (tipo_fonte='FATURA_REFERENCIA') para NFs referenciadas
-- em carvia_fatura_cliente_itens que nao existem em carvia_nfs.
--
-- Idempotente: todas as operacoes verificam estado antes de agir.
-- Pode rodar N vezes com resultado identico.
--
-- Execucao no Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/backfill_carvia_nf_linking.sql
-- ==========================================================================

BEGIN;

-- 1. Estado ANTES
SELECT 'ANTES' AS fase,
       count(*) AS total_itens,
       count(nf_id) AS com_nf,
       count(*) - count(nf_id) AS sem_nf
FROM carvia_fatura_cliente_itens
WHERE nf_numero IS NOT NULL;

-- 2. Criar NFs referencia para itens sem nf_id
-- Usa DISTINCT ON para evitar duplicatas quando multiplos itens referenciam mesma NF
INSERT INTO carvia_nfs (
    numero_nf,
    cnpj_emitente,
    nome_emitente,
    valor_total,
    peso_bruto,
    tipo_fonte,
    criado_em,
    criado_por
)
SELECT DISTINCT ON (ltrim(i.nf_numero, '0'), regexp_replace(i.contraparte_cnpj, '[^0-9]', '', 'g'))
    i.nf_numero,
    COALESCE(i.contraparte_cnpj, 'DESCONHECIDO'),
    i.contraparte_nome,
    i.valor_mercadoria,
    i.peso_kg,
    'FATURA_REFERENCIA',
    NOW(),
    'backfill'
FROM carvia_fatura_cliente_itens i
WHERE i.nf_id IS NULL
  AND i.nf_numero IS NOT NULL
  AND i.contraparte_cnpj IS NOT NULL
  -- Idempotencia: verificar que NF nao existe ainda
  AND NOT EXISTS (
      SELECT 1 FROM carvia_nfs nf
      WHERE ltrim(nf.numero_nf, '0') = ltrim(i.nf_numero, '0')
        AND regexp_replace(nf.cnpj_emitente, '[^0-9]', '', 'g')
          = regexp_replace(i.contraparte_cnpj, '[^0-9]', '', 'g')
  )
ORDER BY ltrim(i.nf_numero, '0'),
         regexp_replace(i.contraparte_cnpj, '[^0-9]', '', 'g'),
         i.id;  -- Pegar primeiro item como fonte dos dados

-- 3. Vincular nf_id nos itens (match por numero + cnpj normalizado)
UPDATE carvia_fatura_cliente_itens i
SET nf_id = nf.id
FROM carvia_nfs nf
WHERE i.nf_id IS NULL
  AND i.nf_numero IS NOT NULL
  AND ltrim(nf.numero_nf, '0') = ltrim(i.nf_numero, '0')
  AND (
      -- Match por cnpj_emitente
      regexp_replace(nf.cnpj_emitente, '[^0-9]', '', 'g')
        = regexp_replace(i.contraparte_cnpj, '[^0-9]', '', 'g')
      -- OU match por cnpj_destinatario
      OR regexp_replace(COALESCE(nf.cnpj_destinatario, ''), '[^0-9]', '', 'g')
        = regexp_replace(i.contraparte_cnpj, '[^0-9]', '', 'g')
  );

-- 4. Criar junctions operacao <-> NF (onde item tem operacao_id e nf_id)
INSERT INTO carvia_operacao_nfs (operacao_id, nf_id, criado_em)
SELECT DISTINCT i.operacao_id, i.nf_id, NOW()
FROM carvia_fatura_cliente_itens i
WHERE i.operacao_id IS NOT NULL
  AND i.nf_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM carvia_operacao_nfs j
      WHERE j.operacao_id = i.operacao_id
        AND j.nf_id = i.nf_id
  );

-- 5. Estado DEPOIS
SELECT 'DEPOIS' AS fase,
       count(*) AS total_itens,
       count(nf_id) AS com_nf,
       count(*) - count(nf_id) AS sem_nf
FROM carvia_fatura_cliente_itens
WHERE nf_numero IS NOT NULL;

-- 6. NFs referencia criadas
SELECT count(*) AS nfs_referencia_total
FROM carvia_nfs
WHERE tipo_fonte = 'FATURA_REFERENCIA';

-- 7. Total junctions
SELECT count(*) AS junctions_total
FROM carvia_operacao_nfs;

COMMIT;
