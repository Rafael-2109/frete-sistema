-- Migration: campos de geocoding em assai_loja
-- Idempotente

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assai_loja' AND column_name='latitude') THEN
        ALTER TABLE assai_loja ADD COLUMN latitude NUMERIC(10,7);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assai_loja' AND column_name='longitude') THEN
        ALTER TABLE assai_loja ADD COLUMN longitude NUMERIC(11,7);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assai_loja' AND column_name='geocoding_provider') THEN
        ALTER TABLE assai_loja ADD COLUMN geocoding_provider VARCHAR(20);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assai_loja' AND column_name='geocoded_at') THEN
        ALTER TABLE assai_loja ADD COLUMN geocoded_at TIMESTAMP;
    END IF;
END $$;
