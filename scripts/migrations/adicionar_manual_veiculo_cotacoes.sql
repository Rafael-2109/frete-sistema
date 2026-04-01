-- Adiciona campos para cotacao manual e veiculo (carga direta) em carvia_cotacoes
-- Idempotente: usa IF NOT EXISTS / verifica antes de adicionar

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'cotacao_manual'
    ) THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN cotacao_manual BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'valor_manual'
    ) THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN valor_manual NUMERIC(15,2);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'veiculo_id'
    ) THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN veiculo_id INTEGER REFERENCES veiculos(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_carvia_cotacoes_veiculo_id ON carvia_cotacoes (veiculo_id);
