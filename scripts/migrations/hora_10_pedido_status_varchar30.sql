-- Migration HORA 10: aumenta hora_pedido.status VARCHAR(20) -> VARCHAR(30)
--
-- MOTIVO: valor 'PARCIALMENTE_FATURADO' (22 char) excede VARCHAR(20).
-- Producao: 500 em /hora/nfs/upload com psycopg2.errors.StringDataRightTruncation
-- no UPDATE hora_pedido SET status='PARCIALMENTE_FATURADO'.
--
-- Idempotente: ALTER TYPE para maior largura e no-op quando ja aplicado.
-- PostgreSQL 9.2+ nao faz rewrite ao aumentar VARCHAR.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'hora_pedido'
          AND column_name = 'status'
          AND character_maximum_length < 30
    ) THEN
        ALTER TABLE hora_pedido
            ALTER COLUMN status TYPE VARCHAR(30);
        RAISE NOTICE 'hora_pedido.status ampliado para VARCHAR(30)';
    ELSE
        RAISE NOTICE 'hora_pedido.status ja esta em VARCHAR(30) ou maior — nada a fazer';
    END IF;
END $$;
