-- Migration: Adicionar campo sistema_carvia na tabela usuarios
-- Executar no Render Shell (SQL idempotente)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'usuarios' AND column_name = 'sistema_carvia'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN sistema_carvia BOOLEAN DEFAULT FALSE NOT NULL;
        RAISE NOTICE 'Campo sistema_carvia adicionado com sucesso';
    ELSE
        RAISE NOTICE 'Campo sistema_carvia ja existe';
    END IF;
END $$;
