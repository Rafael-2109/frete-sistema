-- Adiciona campos de endereco de entrega na cotacao (override do destino)
-- Idempotente: usa IF NOT EXISTS

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='carvia_cotacoes' AND column_name='entrega_uf') THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN entrega_uf VARCHAR(2);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='carvia_cotacoes' AND column_name='entrega_cidade') THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN entrega_cidade VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='carvia_cotacoes' AND column_name='entrega_logradouro') THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN entrega_logradouro VARCHAR(255);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='carvia_cotacoes' AND column_name='entrega_numero') THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN entrega_numero VARCHAR(20);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='carvia_cotacoes' AND column_name='entrega_bairro') THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN entrega_bairro VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='carvia_cotacoes' AND column_name='entrega_cep') THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN entrega_cep VARCHAR(10);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='carvia_cotacoes' AND column_name='entrega_complemento') THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN entrega_complemento VARCHAR(255);
    END IF;
END $$;
