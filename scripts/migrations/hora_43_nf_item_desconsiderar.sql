-- hora_43: NF entrada item — flag desconsiderado + relaxar FK numero_chassi -> hora_moto
-- Spec: docs/superpowers/specs/2026-06-03-hora-desconsiderar-moto-nf-design.md
-- Idempotente (Render Shell).

ALTER TABLE hora_nf_entrada_item
    ADD COLUMN IF NOT EXISTS desconsiderado BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_item_desconsiderado
    ON hora_nf_entrada_item (desconsiderado);

-- Drop da FK numero_chassi -> hora_moto (nome auto-gerado pelo PG; descobre via catalogo).
DO $$
DECLARE cname text;
BEGIN
    SELECT conname INTO cname
      FROM pg_constraint
     WHERE conrelid = 'hora_nf_entrada_item'::regclass
       AND contype = 'f'
       AND confrelid = 'hora_moto'::regclass
     LIMIT 1;
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE hora_nf_entrada_item DROP CONSTRAINT %I', cname);
    END IF;
END $$;
