<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: scripts/inventario_2026_05/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# _deprecated — scripts aposentados na Onda 3 PAD-A
> **Papel:** scripts mortos/superados movidos para fora do lint (ignore_globs). Preservados via git para historico; NAO usar.

| script | categoria | motivo | substituto |
|--------|-----------|--------|------------|
| 00_audit_odoo_realidade.py | DEAD | discovery F0 concluido (logica destilada em D000-D003) | — |
| 00b_investigar_gotchas.py | DEAD | discovery F0 concluido (logica destilada em D000-D003) | — |
| 00c_investigar_g003.py | DEAD | discovery F0 concluido (logica destilada em D000-D003) | — |
| 00d_investigar_variacoes.py | DEAD | discovery F0 concluido (logica destilada em D000-D003) | — |
| 00e_investigar_pickings.py | DEAD | discovery F0 concluido (logica destilada em D000-D003) | — |
| ajuste_quant_cd.py | DEAD | ajuste pontual 1 quant (AZEITE 4729098) ja executado | — |
| baixar_xml_preview_626032.py | DEAD | preview XML pontual (G008) | — |
| debug_sefaz_608607.py | DEAD | debug piloto pontual | — |
| desfazer_ajustes_indevidos_lf.py | DEAD | desfaz ajustes Maria 09/04 (pontual executado) | — |
| recuperar_aumentos_falhos.py | DEAD | recupera 11 aumentos falhos especificos (executado) | — |
| relotar_migracao_para_lotes_fb.py | DEAD | 2 itens FB ja executado 2026-05-20 | — |
| transferir_fluxo_c.py | DEAD | 2 NFs canceladas hardcoded (executado) | — |
| consolidar_lote_104000015_sal_fb.py | DEAD | caso pontual lote 104000015 SAL FB (par; executado) | — |
| corrigir_fantasma_104000015_sal_fb.py | DEAD | caso pontual lote 104000015 SAL FB (par; executado) | — |
| fat_lf_00_preflight.py | DEAD | diagnostico read-only do faturamento LF (ciclo encerrado) | — |
| fat_lf_01_stock_audit.py | DEAD | diagnostico read-only do faturamento LF (ciclo encerrado) | — |
| fat_lf_diag.py | DEAD | diagnostico read-only do faturamento LF (ciclo encerrado) | — |
| fat_lf_inspect_invoice.py | DEAD | diagnostico read-only do faturamento LF (ciclo encerrado) | — |
| 13_transferencia_migracao_fb.py | SUPERSEDED | superado por transfer.py (StockInternalTransferService) | app/odoo/estoque/scripts/transfer.py |
| 15_transferencia_para_migracao.py | SUPERSEDED | superado por transfer.py (StockInternalTransferService) | app/odoo/estoque/scripts/transfer.py |
| 15r_transferencia_reversa.py | SUPERSEDED | superado por transfer.py (StockInternalTransferService) | app/odoo/estoque/scripts/transfer.py |
| 17_transferir_preprod_lf_para_estoque.py | SUPERSEDED | superado por quant.py / transfer.py | app/odoo/estoque/scripts/quant.py |
| fat_lf_03_prestage.py | SUPERSEDED | superado por quant.py / transfer.py | app/odoo/estoque/scripts/quant.py |
| 15_transferir_preprod_para_estoque_fb.py | SUPERSEDED | superado por quant.py / transfer.py | app/odoo/estoque/scripts/quant.py |
| corrigir_reserved_negativo_fb.py | SUPERSEDED | superado por reserva.py (resetar_reserva) | app/odoo/estoque/scripts/reserva.py |
| fat_lf_02_carregar.py | SUPERSEDED | superado por orchestrators/inventario_pipeline.py | app/odoo/estoque/scripts/orchestrators/inventario_pipeline.py |
| fat_lf_04_executar.py | SUPERSEDED | superado por orchestrators/inventario_pipeline.py | app/odoo/estoque/scripts/orchestrators/inventario_pipeline.py |
| limpar_quants_ghost_210030005_fb.py | SUPERSEDED | superado por quant.py (zerar por quant_id) | app/odoo/estoque/scripts/quant.py |
