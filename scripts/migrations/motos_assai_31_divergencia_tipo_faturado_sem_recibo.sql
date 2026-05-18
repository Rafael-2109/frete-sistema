-- 2026-05-17: adiciona novo tipo CHASSI_FATURADO_SEM_RECIBO ao CHECK constraint
-- de `assai_divergencia.tipo`. Emitido por `_calcular_match` quando chassi esta
-- em assai_moto mas SEM AssaiReciboItem conferido (parser PDF errado, digitacao
-- errada na conferencia, ou faturamento sem recebimento fisico).
--
-- Idempotente: DROP IF EXISTS + recriar.

ALTER TABLE assai_divergencia
    DROP CONSTRAINT IF EXISTS ck_assai_divergencia_tipo;

ALTER TABLE assai_divergencia
    ADD CONSTRAINT ck_assai_divergencia_tipo
    CHECK (tipo IN (
        'NF_CHASSI_FORA_CARREGAMENTO',
        'CARREGAMENTO_CHASSI_FORA_NF',
        'CHASSI_NAO_CADASTRADO',
        'CHASSI_OUTRA_LOJA',
        'LOJA_DIVERGENTE',
        'VALOR_DIVERGENTE',
        'MODELO_DIVERGENTE',
        'CHASSI_SEM_SEPARACAO',
        'CHASSI_FATURADO_SEM_RECIBO'
    ));
