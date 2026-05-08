-- Migration: Toggle sistema_motos_assai em usuarios
-- Idempotente; pode ser executada múltiplas vezes sem efeito colateral.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'usuarios'
          AND column_name = 'sistema_motos_assai'
    ) THEN
        ALTER TABLE usuarios
        ADD COLUMN sistema_motos_assai BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;
END $$;
