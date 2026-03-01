-- Migration: Adicionar campo sistema_seguranca na tabela usuarios
-- Executar no Render Shell (SQL idempotente)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'usuarios' AND column_name = 'sistema_seguranca'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN sistema_seguranca BOOLEAN DEFAULT FALSE NOT NULL;
        RAISE NOTICE 'Campo sistema_seguranca adicionado com sucesso';
    ELSE
        RAISE NOTICE 'Campo sistema_seguranca ja existe';
    END IF;
END $$;
