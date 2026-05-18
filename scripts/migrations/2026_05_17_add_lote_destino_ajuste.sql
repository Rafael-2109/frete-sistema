-- D004/D005: lote_destino em ajuste_estoque_inventario
-- Para RENOMEAR_LOTE: lote_destino = lote alvo (ex: 26014)
-- Para PERDA_LF_FB / TRANSFERIR_*_FB: lote_destino = 'MIGRACAO' (na FB)
-- Para INDUSTRIALIZACAO_FB_LF: lote_destino = lote inv (na LF)
-- Para INDISPONIBILIZAR_*: lote_destino = NULL (lote_odoo ja eh suficiente)

ALTER TABLE ajuste_estoque_inventario
    ADD COLUMN IF NOT EXISTS lote_destino VARCHAR(60);

ALTER TABLE ajuste_estoque_inventario
    ADD COLUMN IF NOT EXISTS lote_origem VARCHAR(60);

-- lote_origem: para RENOMEAR_LOTE, o lote Odoo de origem (ex: MIGRACAO, vazio)
--              para PERDA/TRANSFERIR, o lote no Odoo de origem (= lote_odoo)
