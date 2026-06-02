<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Scripts inventario 2026-05 — indice dos vivos
> **Papel:** indice navegavel dos scripts vivos da operacao de inventario 2026-05. So ponteiros + 1 linha por script. Mineracao detalhada (script->atomo, gotchas): `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Aposentados: `_deprecated/README.md`.

## Pipeline / orquestradores (raiz)

- `01_extrair_estoque_odoo.py` — F7.1: extrai estoque atual FB/CD/LF via stock.quant e gera Excel + JSON para confronto
- `02_carregar_inventario_xlsx.py` — F7.2: carrega planilha do inventario fisico (abas FB/CD/LF) em /tmp para confronto
- `03_confrontar_inv_vs_odoo.py` — F7.3: confronto inventario fisico x estoque Odoo, aplica regras de lote P6/P9
- `04_propor_ajustes.py` — F7.4: persiste propostas de ajuste em ajuste_estoque_inventario e suporta aprovar-onda com hash anti-replay
- `08_extrair_pos_execucao.py` — F7.7: extrai estado pos-execucao do Odoo e gera Excel comparativo proposto x realizado
- `09_executar_onda1_bulk.py` — bulk de ajustes ordenado por tipo de processo (ETAPA A transferencia de lotes, B faturamento, etc.)
- `09c_executar_onda2_fb_cd.py` — F9c: executor Onda 2 TRANSFERIR_FB_CD via reuso RecebimentoLf (etapas 19-37, NF inter-company)
- `ajuste_estoque_lf_pasta17.py` — realocacao de lote na LF via planilha Pasta17.xlsx (aumenta/reduz por diff_qtd, net-zero por produto)
- `ajuste_fb_cd_indisponivel.py` — ajuste FB + transf CD: transferencias Estoque <-> Indisponivel/MIGRACAO (planilhas AJUSTE FB/TRANSF CD, D011)
- `ajuste_inventario.py` — orquestrador generico de ajuste de inventario por planilha (consolida familia A: scripts 11-14 + criar_saldo_positivo_lf)
- `encontro_contas_lf.py` — encontro de contas FB<->LF por produto (Pasta23.xlsx): mov_liquido decide direcao de faturamento/MIGRACAO
- `entrada_fb_piloto.py` — fecha piloto produto 210030325 via RecebimentoLf: NF LF -> DFe FB -> PO -> picking entrada -> invoice FB
- `escriturar_dfe_lf.py` — FLUXO A: escritura in_invoice de entrada na LF a partir de DFe de industrializacao FB->LF (status 04, generalizado multi-linha)
- `executar_fluxo_b_vivas.py` — FLUXO B: reverte 7 out_invoice FB->LF nao transmitidas (cancelar NF + devolver picking + isolar em FB/Indisponivel/MIGRACAO)
- `fat_lf_05_executar_clean.py` — faturamento LF com reserva explicita FIFO corrigindo bug multi-lote do executor 09 (produtos sem lote_origem)
- `fat_lf_06_consolidar_validos.py` — garante estoque valido (lote nao-vencido) >= QTD por produto antes do action_assign do CIEL IT (generaliza G014)
- `fat_lf_cleanup.py` — fluxo de erro: devolve picking + cancela invoice + reseta ajuste para NFs com quantidade errada nao transmitidas
- `mover_migracao_para_indisponivel.py` — move quants do lote MIGRACAO para os locais Indisponivel nas 3 filiais CD/FB/LF (D011)
- `substituir_lote_unico.py` — operacao pontual: substituicao de lote de UM produto (ex-205030410 em FB/Pre-Producao/Linha Balde)
- `teste_e2e_lf_exemplo.py` — exemplo/piloto end-to-end LF (ex-210030325): 4 TRANSFERIR_LOTE + 2 PERDA_LF_FB via CFOP 5903
- `transferir_indisp_para_estoque_p15_cd.py` — operacao pontual: 2 itens CD/Indisponivel/MIGRACAO -> CD/Estoque/P-15/05 via inventory adjustment 2 passos
- `transferir_local_pasta22.py` — transferencia De/Para LOCAL+LOTE multi-empresa (Pasta22): SAIDA p/ Indisponivel/MIGRACAO ou RETORNO ao estoque
- `transferir_lote.py` — realocacao de lote no mesmo local via planilha diff_qtd (net-zero por produto, transferencia de saldo entre lotes)
- `zerar_negativos_fb.py` — zera todos os quants negativos da FB via inventory adjustment consumindo outros lotes (estrategia 3 passos com fallback MIGRACAO)

## Auditoria / diff / leitura (auditoria/ + raiz)

- `03_confrontar_inv_vs_odoo.py` — ver Pipeline acima (F7.3)
- `08_extrair_pos_execucao.py` — ver Pipeline acima (F7.7)
- `auditar_migracao_fora_indisponivel.py` — lista quants com lote MIGRACAO/MIGRAÇÃO fora dos locais Indisponivel de cada filial (D011 compliance)
- `extrair_estoque_locais_emp.py` — extrai estoque atual Odoo para as 4 companies (FB/SC/CD/LF) excluindo locais Indisponivel por padrao
- `rastrear_movs_item.py` — rastreia movimentacoes stock.move.line de um produto no Odoo desde uma data (read-only, mostra cronologia + estoque atual)
- `auditoria/comparar_sot_full.py` — versao completa: compara SOT contra todas as 3 fontes derivadas (diffs originais + plano-pre-etapa + visao macro)
- `auditoria/comparar_sot_vs_fontes.py` — compara SOT (inventario fisico + Odoo snapshot 17/05) com as 3 fontes derivadas, gera Excel comparativo
- `auditoria/confronto_4_fontes.py` — confronto direto SOT vs 3 fontes derivadas por (filial, cod) agregado e por (filial, cod, lote) detalhado
- `auditoria/diff_inv_vs_odoo_atual_sem_migracao.py` — diff direto inventario fisico 16/05 vs Odoo atual, apenas lotes != MIGRACAO
- `auditoria/diff_lotes_nao_migracao.py` — refiltra diff anterior considerando apenas lotes nao-MIGRACAO (saldo "real disponivel")
- `auditoria/extrair_movimentacoes_odoo.py` — extrai todas as movimentacoes Odoo desde 2026-05-16 excluindo recebimentos LF do Render
- `auditoria/inv_teorico_e_novo_diff.py` — aplica movimentacoes Odoo ao inventario fisico e compara com estoque atual (diff residual)
- `auditoria/relatorio_final_sot.py` — relatorio final definitivo: SOT vs fontes derivadas com descoberta que apenas 33% dos SKUs foram inventariados
- `auditoria/sot_com_lotes.py` — auditoria com lotes + regras de negocio por filial (LF via NF, CD/FB via MIGRACAO)

## Monitor (pipeline estoque->movs->diff)

- `monitor/0_pipeline.py` — orquestrador: roda os scripts 1-4 em sequencia com suporte a --skip e --so
- `monitor/1_baixar_estoques.py` — baixa estoques atuais do Odoo (stock.quant) para FB/CD/LF e grava cache CSV
- `monitor/2_baixar_movimentacoes.py` — baixa movimentacoes stock.move.line desde DATA_INICIO_INV e classifica por origem
- `monitor/3_agregar_lote.py` — agrega inventario fisico + movimentacoes RECEBIMENTO_LF_RENDER em saldo teorico (cache CSV)
- `monitor/4_gerar_diffs.py` — gera diffs por (filial, cod, lote) filtrando MIGRACAO, compara teorico vs Odoo atual
- `monitor/_comum.py` — helpers compartilhados pelos scripts 1-4 do monitor (constantes LOTES_MIGRACAO, path setup)
- `monitor/export_excel_completo.py` — export Excel sob demanda: 3 abas (Movimentacoes + Estoque_por_Local + Estoque_Sistema)
- `monitor/relatorio_apontamentos_compras.py` — relatorio de apontamentos de producao (componentes + PA) e compras externas recebidas desde 16/05

## _validados (referencias validadas por skill)

> Scripts arquivados como "museum vivo" apos superacao pela skill correspondente. Permanecem executaveis para reproducibilidade historica.

- `_validados/ajustando-quant-odoo/11_ajuste_negativo_cd.py` — ajuste negativo residual CD via inventory adjustment puro (planilha AJUSTE SALDO CD.xlsx, 182 linhas)
- `_validados/ajustando-quant-odoo/12_ajuste_positivo_cd.py` — ajuste positivo CD via inventory adjustment puro (planilha AJUSTE SALDO CD.xlsx v2, 35 linhas)
- `_validados/ajustando-quant-odoo/13_ajuste_positivo_fb.py` — ajuste positivo FB via inventory adjustment puro (planilha AJUSTE SALDO CD.xlsx v3, 93 linhas FB)
- `_validados/ajustando-quant-odoo/14_ajuste_positivo_cd_v2.py` — ajuste positivo CD V2 via inventory adjustment puro (planilha AJUSTE SALDO CD.xlsx v4, 15 linhas)
- `_validados/ajustando-quant-odoo/criar_saldo_positivo_lf.py` — ajuste de inventario positivo puro na LF (criar saldo, NAO transferir de MIGRACAO)
- `_validados/operando-mo-odoo/14_cancelar_mos_antigas_fb.py` — cancela MOs antigas confirmed que reservam MIGRACAO em Pre-Prod FB (superado pela Skill 4)
- `_validados/operando-mo-odoo/cancelar_mos.py` — cancela Ordens de Producao por criterio parametrizavel (superado pela Skill 4 operando-mo-odoo)
- `_validados/operando-picking-odoo/16_cancelar_pickings_fantasmas.py` — cancela pickings fantasmas que reservam lotes da planilha transf para MIGRACAO (superado pela Skill 5)
- `_validados/operando-reservas-odoo/cancelar_reservas_migracao.py` — cancela reservas em lote MIGRACAO dos quants listados em migracao_mover_pulados.csv
- `_validados/operando-reservas-odoo/limpar_reservas_fantasma.py` — limpa reservas fantasma das MOs em Pre-Producao FB+LF via action_unreserve + action_assign
- `_validados/operando-reservas-odoo/remover_reservas_saida.py` — remove todas as reservas de saida (origem interna) das 4 companies FB/SC/CD/LF
- `_validados/planejando-pre-etapa-odoo/03b_planejar_pre_etapa_cd.py` — F7.5b: planejar pre-etapa CD (superado pela Skill 6 modo planejar)
- `_validados/planejando-pre-etapa-odoo/04b_propor_pre_etapa_cd.py` — F7.6b: propor ajustes da pre-etapa CD Onda 5 (superado pela Skill 6 modos propor/listar/aprovar)
- `_validados/planejando-pre-etapa-odoo/09b_executar_pre_etapa.py` — F9b: executor da Pre-etapa CD/FB Onda 5/6 (superado pela Skill 6 modo executar-onda)
- `_validados/transferindo-interno-odoo/10_executar_emergenciais_fb.py` — executa 9 transferencias internas emergenciais FB de MIGRACAO para lotes canonicos
- `_validados/transferindo-interno-odoo/padronizar_migracao.py` — padroniza lote 'MIGRACAO' (sem cedilha) -> 'MIGRAÇÃO' (com cedilha+til) para manter D005
