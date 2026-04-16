-- Migration: Adicionar flag sistema_remessa_vortx + tabela remessa_vortx_cache + sequence
-- Executar no Render Shell: psql $DATABASE_URL < scripts/migrations/adicionar_remessa_vortx.sql

-- 1. Flag no usuario
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'usuarios' AND column_name = 'sistema_remessa_vortx'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN sistema_remessa_vortx BOOLEAN NOT NULL DEFAULT FALSE;
        RAISE NOTICE 'Coluna sistema_remessa_vortx adicionada.';
    ELSE
        RAISE NOTICE 'Coluna sistema_remessa_vortx ja existe.';
    END IF;
END
$$;

-- 2. Tabela remessa_vortx_cache
CREATE TABLE IF NOT EXISTS remessa_vortx_cache (
    id SERIAL PRIMARY KEY,
    etapa VARCHAR(30) NOT NULL DEFAULT 'CNAB_GERADO',
    tentativas INTEGER NOT NULL DEFAULT 0,
    ultimo_erro TEXT,

    odoo_escritural_id INTEGER,
    odoo_remessa_id INTEGER,

    move_line_ids_marcados TEXT,
    move_line_ids_pendentes TEXT,
    mapa_nn_move_line TEXT,

    company_id_odoo INTEGER NOT NULL,
    tipo_cobranca_id_odoo INTEGER,
    nome_arquivo VARCHAR(200) NOT NULL,
    qtd_boletos INTEGER NOT NULL DEFAULT 0,
    valor_total NUMERIC(15, 2) NOT NULL DEFAULT 0,
    nosso_numero_inicial BIGINT,
    nosso_numero_final BIGINT,
    arquivo_cnab BYTEA,

    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id),
    concluido_em TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_remessa_vortx_etapa ON remessa_vortx_cache (etapa);
CREATE INDEX IF NOT EXISTS idx_remessa_vortx_company ON remessa_vortx_cache (company_id_odoo);

-- 4. Sequence para nosso numero
CREATE SEQUENCE IF NOT EXISTS nosso_numero_vortx_seq START 1;
