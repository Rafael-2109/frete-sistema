-- Migration 24: ALTER CHECK constraints para aceitar novos valores de status.
-- Padrao: DROP IF EXISTS antiga + ADD CHECK nova.
-- Se nao houver CHECK constraint, e no-op (idempotente).

BEGIN;

-- assai_separacao.status — adicionar CARREGADA
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_separacao_status') THEN
        ALTER TABLE assai_separacao DROP CONSTRAINT ck_assai_separacao_status;
    END IF;
    ALTER TABLE assai_separacao
        ADD CONSTRAINT ck_assai_separacao_status
        CHECK (status IN ('EM_SEPARACAO', 'FECHADA', 'CARREGADA', 'FATURADA', 'CANCELADA'));
END $$;

-- assai_nf_qpa.status_match — adicionar CANCELADA
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_nf_qpa_status_match') THEN
        ALTER TABLE assai_nf_qpa DROP CONSTRAINT ck_assai_nf_qpa_status_match;
    END IF;
    ALTER TABLE assai_nf_qpa
        ADD CONSTRAINT ck_assai_nf_qpa_status_match
        CHECK (status_match IN ('BATEU', 'DIVERGENTE', 'NAO_RECONCILIADO', 'CANCELADA'));
END $$;

-- assai_moto_evento.tipo — adicionar CARREGADA
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_moto_evento_tipo') THEN
        ALTER TABLE assai_moto_evento DROP CONSTRAINT ck_assai_moto_evento_tipo;
    END IF;
    ALTER TABLE assai_moto_evento
        ADD CONSTRAINT ck_assai_moto_evento_tipo
        CHECK (tipo IN (
            'ESTOQUE', 'MONTADA', 'PENDENTE', 'PENDENCIA_RESOLVIDA',
            'DISPONIVEL', 'REVERTIDA_PARA_MONTADA',
            'SEPARADA', 'CARREGADA', 'FATURADA', 'CANCELADA', 'MOTO_FALTANDO'
        ));
END $$;

-- assai_pedido_venda.status — simplificar para 4 status
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_pedido_venda_status') THEN
        ALTER TABLE assai_pedido_venda DROP CONSTRAINT ck_assai_pedido_venda_status;
    END IF;
    ALTER TABLE assai_pedido_venda
        ADD CONSTRAINT ck_assai_pedido_venda_status
        CHECK (status IN ('ABERTO', 'PARCIALMENTE_FATURADO', 'FATURADO', 'CANCELADO'));
END $$;

COMMIT;
