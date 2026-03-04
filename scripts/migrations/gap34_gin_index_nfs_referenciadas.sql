-- GAP-34: Criar indice GIN em carvia_operacoes.nfs_referenciadas_json.
-- Otimiza queries de linking retroativo (vincular_nf_a_operacoes_orfas).
-- Idempotente: IF NOT EXISTS.

CREATE INDEX IF NOT EXISTS ix_carvia_operacoes_nfs_ref_json_gin
ON carvia_operacoes
USING GIN (nfs_referenciadas_json)
WHERE nfs_referenciadas_json IS NOT NULL;
