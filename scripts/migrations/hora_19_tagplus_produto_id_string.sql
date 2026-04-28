-- Migration HORA 19: tagplus_produto_id INTEGER -> VARCHAR(50).
-- API TagPlus aceita string no campo `produto` do POST /nfes (codigo string,
-- nao apenas ID inteiro). Confirmado em 2026-04-27.
-- Idempotente: so altera se ainda for INTEGER.

DO $$
DECLARE
    tipo_atual TEXT;
BEGIN
    SELECT data_type INTO tipo_atual
      FROM information_schema.columns
     WHERE table_name = 'hora_tagplus_produto_map'
       AND column_name = 'tagplus_produto_id';

    IF tipo_atual IS NULL THEN
        RAISE NOTICE 'Coluna hora_tagplus_produto_map.tagplus_produto_id nao existe — pular';
        RETURN;
    END IF;

    IF tipo_atual = 'character varying' THEN
        RAISE NOTICE 'Coluna ja e VARCHAR — pular';
        RETURN;
    END IF;

    -- Converte INTEGER -> VARCHAR(50) preservando valores existentes.
    ALTER TABLE hora_tagplus_produto_map
        ALTER COLUMN tagplus_produto_id TYPE VARCHAR(50)
        USING tagplus_produto_id::text;

    RAISE NOTICE 'Coluna alterada para VARCHAR(50).';
END $$;
