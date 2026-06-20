-- Migration 33: adiciona DEMONSTRACAO ao CHECK constraint de assai_moto_evento.tipo.
-- Origem: skill corrigindo-dados-assai (backfill manual) + IMP-2026-06-19-001 item 3
-- (3 motos em DEMONSTRACAO na planilha da Rayssa, estado inexistente no dominio).
-- Padrao: DROP IF EXISTS antiga + ADD CHECK nova (idempotente).

BEGIN;

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
            'SEPARADA', 'CARREGADA', 'FATURADA', 'CANCELADA', 'MOTO_FALTANDO',
            'DEMONSTRACAO'
        ));
END $$;

COMMIT;
