-- Migration: Alargar tipo_separacao em alertas_separacao_cotada
-- VARCHAR(30) → VARCHAR(50) para alinhar com modelo SQLAlchemy String(50)
-- Causa raiz: Sentry PYTHON-FLASK-1G — DataError: value too long for type character varying

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alertas_separacao_cotada'
          AND column_name = 'tipo_separacao'
          AND character_maximum_length < 50
    ) THEN
        ALTER TABLE alertas_separacao_cotada
        ALTER COLUMN tipo_separacao TYPE VARCHAR(50);
        RAISE NOTICE 'tipo_separacao alargado para VARCHAR(50)';
    ELSE
        RAISE NOTICE 'tipo_separacao ja tem tamanho >= 50 ou nao existe';
    END IF;
END $$;
