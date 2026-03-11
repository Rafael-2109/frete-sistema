-- Migration: Alterar tipo_separacao de VARCHAR(10) para VARCHAR(30)
-- Tabela: alertas_separacao_cotada
-- Motivo: Sentry PYTHON-FLASK-A/X — DataError "value too long for type character varying(10)"
-- Data: 2026-03-11

DO $$
BEGIN
    -- Verificar se a coluna existe e precisa ser alterada
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'alertas_separacao_cotada'
          AND column_name = 'tipo_separacao'
          AND character_maximum_length = 10
    ) THEN
        ALTER TABLE alertas_separacao_cotada
            ALTER COLUMN tipo_separacao TYPE VARCHAR(30);
        RAISE NOTICE 'tipo_separacao alterado para VARCHAR(30)';
    ELSE
        RAISE NOTICE 'tipo_separacao ja e VARCHAR(30) ou nao existe — nada a fazer';
    END IF;
END $$;
