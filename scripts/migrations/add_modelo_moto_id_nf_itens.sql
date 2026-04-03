-- Migration: Adicionar modelo_moto_id em carvia_nf_itens
-- Persiste modelo detectado na importacao (editavel manualmente)
-- Idempotente — seguro para rodar multiplas vezes

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_nf_itens' AND column_name = 'modelo_moto_id'
    ) THEN
        ALTER TABLE carvia_nf_itens
            ADD COLUMN modelo_moto_id INTEGER
            REFERENCES carvia_modelos_moto(id);

        CREATE INDEX IF NOT EXISTS ix_carvia_nf_itens_modelo_moto_id
            ON carvia_nf_itens(modelo_moto_id);

        RAISE NOTICE 'Coluna modelo_moto_id adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna modelo_moto_id ja existe — nada a fazer';
    END IF;
END $$;
