-- GAP-08: Adicionar ON DELETE CASCADE na FK nf_id da junction carvia_operacao_nfs.
-- Ao deletar NF, junctions sao removidas automaticamente.
-- Idempotente: verifica confdeltype antes de alterar.

DO $$
DECLARE
    v_fk_name TEXT;
    v_del_type CHAR(1);
BEGIN
    -- Descobrir nome e tipo da FK
    SELECT conname, confdeltype INTO v_fk_name, v_del_type
    FROM pg_constraint
    WHERE conrelid = 'carvia_operacao_nfs'::regclass
      AND confrelid = 'carvia_nfs'::regclass
      AND contype = 'f'
    LIMIT 1;

    IF v_fk_name IS NULL THEN
        RAISE NOTICE 'FK nf_id nao encontrada em carvia_operacao_nfs. Nada a fazer.';
        RETURN;
    END IF;

    IF v_del_type = 'c' THEN
        RAISE NOTICE 'FK % ja tem ON DELETE CASCADE. Nada a fazer.', v_fk_name;
        RETURN;
    END IF;

    RAISE NOTICE 'Removendo FK antiga %...', v_fk_name;
    EXECUTE format('ALTER TABLE carvia_operacao_nfs DROP CONSTRAINT %I', v_fk_name);

    RAISE NOTICE 'Criando FK com ON DELETE CASCADE...';
    ALTER TABLE carvia_operacao_nfs
    ADD CONSTRAINT carvia_operacao_nfs_nf_id_fkey
    FOREIGN KEY (nf_id) REFERENCES carvia_nfs(id) ON DELETE CASCADE;

    RAISE NOTICE 'FK nf_id agora tem ON DELETE CASCADE.';
END $$;
