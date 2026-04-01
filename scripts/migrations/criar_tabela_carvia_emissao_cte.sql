-- Migration: Criar tabela carvia_emissao_cte
-- Controle de emissoes automaticas de CTe no SSW via Playwright
-- Funcoes: mutex (evita dupla emissao), log de progresso, auditoria

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'carvia_emissao_cte') THEN

        CREATE TABLE carvia_emissao_cte (
            id SERIAL PRIMARY KEY,
            nf_id INTEGER NOT NULL REFERENCES carvia_nfs(id),
            operacao_id INTEGER REFERENCES carvia_operacoes(id),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            etapa VARCHAR(30),
            job_id VARCHAR(100),
            ctrc_numero VARCHAR(20),
            placa VARCHAR(20) NOT NULL DEFAULT 'ARMAZEM',
            cnpj_tomador VARCHAR(20),
            frete_valor NUMERIC(15,2),
            data_vencimento DATE,
            medidas_json JSONB,
            erro_ssw TEXT,
            resultado_json JSONB,
            fatura_numero VARCHAR(20),
            fatura_pdf_path VARCHAR(500),
            xml_path VARCHAR(500),
            dacte_path VARCHAR(500),
            criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
            criado_por VARCHAR(100) NOT NULL,
            atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_carvia_emissao_cte_status CHECK (
                status IN ('PENDENTE', 'EM_PROCESSAMENTO', 'SUCESSO', 'ERRO', 'CANCELADO')
            )
        );

        CREATE INDEX IF NOT EXISTS ix_carvia_emissao_cte_status
            ON carvia_emissao_cte(status);

        CREATE INDEX IF NOT EXISTS ix_carvia_emissao_cte_nf_id
            ON carvia_emissao_cte(nf_id);

        CREATE INDEX IF NOT EXISTS ix_carvia_emissao_cte_job_id
            ON carvia_emissao_cte(job_id);

        RAISE NOTICE 'Tabela carvia_emissao_cte criada com sucesso';
    ELSE
        RAISE NOTICE 'Tabela carvia_emissao_cte ja existe — ignorando';
    END IF;
END $$;
