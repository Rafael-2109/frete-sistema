-- Migration 2026-05-28: cria tabela nf_transferencia_desconsiderada.
--
-- Persiste flag "desconsiderar do calculo de em_transito" por NF inter-company.
-- Sobrevive ao refresh do snapshot (NfTransferenciaSnapshot e
-- apagado e recriado a cada refresh; FK e' apenas LOGICA via
-- account_move_id_origem).
--
-- Idempotente: usa CREATE TABLE IF NOT EXISTS + indexes idempotentes.

CREATE TABLE IF NOT EXISTS nf_transferencia_desconsiderada (
    id SERIAL PRIMARY KEY,
    account_move_id_origem INTEGER NOT NULL UNIQUE,
    motivo VARCHAR(500),
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    criado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS ix_nf_transf_descons_account_move
    ON nf_transferencia_desconsiderada(account_move_id_origem);

COMMENT ON TABLE nf_transferencia_desconsiderada IS
    'NFs inter-company marcadas para EXCLUSAO do calculo em_transito_* '
    '(ja foram ajustadas manualmente no estoque). FK logica via '
    'account_move_id_origem (sobrevive ao DELETE+INSERT do refresh).';
