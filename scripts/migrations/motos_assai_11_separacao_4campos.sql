-- Motos Assaí — Migration 11: 4 campos de agendamento (override) em assai_separacao
-- Idempotente. NULL = herda do AssaiPedidoVendaLoja correspondente.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_separacao' AND column_name='expedicao'
    ) THEN
        ALTER TABLE assai_separacao ADD COLUMN expedicao DATE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_separacao' AND column_name='agendamento'
    ) THEN
        ALTER TABLE assai_separacao ADD COLUMN agendamento DATE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_separacao' AND column_name='protocolo'
    ) THEN
        ALTER TABLE assai_separacao ADD COLUMN protocolo VARCHAR(50);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_separacao' AND column_name='agendamento_confirmado'
    ) THEN
        ALTER TABLE assai_separacao
            ADD COLUMN agendamento_confirmado BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;
