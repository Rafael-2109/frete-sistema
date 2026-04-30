-- hora_21: adiciona modalidade_frete + parcelamento em hora_venda.
--
-- Motivacao: PayloadBuilder TagPlus precisa enviar:
--   - modalidade_frete (TagPlus enum 0/1/2/3/4/9 — antes hardcoded '9').
--   - faturas[].parcelas[] com N parcelas (NF #738 emitida com 18 parcelas).
--
-- Idempotente para Render Shell.

-- 1) modalidade_frete (string '0'-'4' ou '9' conforme doc TagPlus).
ALTER TABLE hora_venda
  ADD COLUMN IF NOT EXISTS modalidade_frete VARCHAR(1) NOT NULL DEFAULT '9';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.constraint_column_usage
    WHERE table_name = 'hora_venda'
      AND constraint_name = 'ck_hora_venda_modalidade_frete'
  ) THEN
    ALTER TABLE hora_venda
      ADD CONSTRAINT ck_hora_venda_modalidade_frete
      CHECK (modalidade_frete IN ('0', '1', '2', '3', '4', '9'));
  END IF;
END $$;

-- 2) numero_parcelas (>=1, <=60).
ALTER TABLE hora_venda
  ADD COLUMN IF NOT EXISTS numero_parcelas INTEGER NOT NULL DEFAULT 1;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.constraint_column_usage
    WHERE table_name = 'hora_venda'
      AND constraint_name = 'ck_hora_venda_numero_parcelas'
  ) THEN
    ALTER TABLE hora_venda
      ADD CONSTRAINT ck_hora_venda_numero_parcelas
      CHECK (numero_parcelas BETWEEN 1 AND 60);
  END IF;
END $$;

-- 3) intervalo_parcelas_dias (1..90; mensal=30, semanal=7, diario=1).
ALTER TABLE hora_venda
  ADD COLUMN IF NOT EXISTS intervalo_parcelas_dias INTEGER NOT NULL DEFAULT 30;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.constraint_column_usage
    WHERE table_name = 'hora_venda'
      AND constraint_name = 'ck_hora_venda_intervalo_parcelas_dias'
  ) THEN
    ALTER TABLE hora_venda
      ADD CONSTRAINT ck_hora_venda_intervalo_parcelas_dias
      CHECK (intervalo_parcelas_dias BETWEEN 1 AND 90);
  END IF;
END $$;
