-- Migration HORA 40: Origem do pedido (XLSX/IMAGEM/MANUAL) + XLSX gerado em background.
--
-- Adiciona suporte a import de pedidos via imagem (print de WhatsApp). Quando o
-- pedido e criado a partir de imagem, um job RQ gera um XLSX equivalente em
-- background para auditoria. A imagem original e o XLSX existente continuam
-- sendo gravados em arquivo_origem_s3_key (campo ja existente — reuso).
--
-- Campos novos:
--   origem                  VARCHAR(20) NOT NULL DEFAULT 'XLSX'
--                            Valores: XLSX, IMAGEM, MANUAL
--   xlsx_origem_s3_key      VARCHAR(500) NULL
--                            S3 key do XLSX equivalente (so quando origem=IMAGEM,
--                            preenchido pelo worker apos geracao em background).
--   xlsx_origem_gerado_em   TIMESTAMP NULL
--                            Quando o worker gerou o XLSX equivalente.
--
-- Backfill:
--   - Pedidos com arquivo_origem_s3_key NOT NULL → 'XLSX' (default).
--   - Pedidos com arquivo_origem_s3_key IS NULL → 'MANUAL'.
--   - origem='IMAGEM' so para registros novos criados via /pedidos/importar-imagem.
--
-- Idempotente: rodar 2x nao tem efeito.

ALTER TABLE hora_pedido
  ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'XLSX';

ALTER TABLE hora_pedido
  ADD COLUMN IF NOT EXISTS xlsx_origem_s3_key VARCHAR(500);

ALTER TABLE hora_pedido
  ADD COLUMN IF NOT EXISTS xlsx_origem_gerado_em TIMESTAMP;

-- CHECK constraint nos valores validos. Idempotente via DO block.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'hora_pedido_origem_check'
  ) THEN
    ALTER TABLE hora_pedido
      ADD CONSTRAINT hora_pedido_origem_check
      CHECK (origem IN ('XLSX', 'IMAGEM', 'MANUAL'));
  END IF;
END $$;

-- Backfill: distingue MANUAL de XLSX para pedidos legados.
-- So aplica em registros que ainda estao com o default 'XLSX' (nao re-aplica).
UPDATE hora_pedido
SET origem = 'MANUAL'
WHERE origem = 'XLSX' AND arquivo_origem_s3_key IS NULL;
