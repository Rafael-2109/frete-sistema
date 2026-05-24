# MAPA DE MINERAÇÃO — os 90 scripts → gold-scripts

**Criado:** 2026-05-20 | Companheiro de [`MAPA_ASSUNTOS.md`](MAPA_ASSUNTOS.md) (assunto→gold) e [`PLANO_MIGRACAO.md`](PLANO_MIGRACAO.md) (como migrar).
Este é o **inverso**: cada um dos 90 scripts → **qual gold-script absorve sua lógica** + **o que preservar** + **situação**.

> **PRINCÍPIO INVIOLÁVEL — MINERAR, NÃO RECRIAR.** Os 90 scripts ad-hoc são a **matéria-prima**: contêm
> lógica de negócio, gotchas resolvidos e edge cases pagos com dor. Antes de criar/mover qualquer gold-script,
> **ler os scripts-fonte deste índice e extrair** o que eles já resolvem. A duplicação que gerou os 90 veio de
> "não procurar → recriar"; a estrutura `gold-*` só vence isso se for **destilada** deles, não reescrita do zero.

**Situação (gatilho por estado do arquivo):**
`SUPERADO` = gold já cobre, arquivar quando confirmado (checklist PLANO §7) ·
`AO-CAPINAR` = minerar quando o assunto entrar no roadmap ·
`MANTER` = já versátil, vira gold de leitura ·
`JÁ-MORTO` = discovery/pontual concluído, arquivar agora.

**Tratamento temporário dos scripts:** permanecem em `scripts/inventario_2026_05/` (zona ad-hoc — ainda rodam **e** são fonte). A pasta esvazia conforme cada gold absorve a lógica.

> 📏 **Nível de validação (honestidade):** a cobertura de NOMES está provada (102/102 via `find`). Mas a coluna "o que minerar" + "situação" foi **inferida de docstrings/categorização, não de leitura integral** dos 102 — só ~5 scripts (tema ajuste) foram lidos a fundo. Este doc é um **GUIA**; a mineração real (lógica + gotchas exatos) valida-se **ao capinar cada assunto**, lendo o script-fonte. Não confiar cegamente na situação de um script sem reabri-lo.

> ⚠️ **OPERAÇÃO VIVA — o número cresce.** Em 2026-05-20 a contagem mudou 4× durante a sessão (89→90→100→101 `.py`). Scripts criados em paralelo, ex.: `transferir_lote.py` (o genérico de transferência que eu ia "criar do zero") e `transferir_local_pasta22.py` (**achado pelo code-reviewer, não por mim**). **Antes de capinar qualquer assunto, reconciliar com `find scripts/inventario_2026_05 -name '*.py'`** — nunca confiar num levantamento antigo. Prova viva do anti-padrão "não procurar → recriar".

---

## → `scripts/quant.py` (StockQuantAdjustmentService) — ajuste de inventário

**Skill:** `ajustando-quant-odoo` ([SKILL.md](../../../.claude/skills/ajustando-quant-odoo/SKILL.md))  ·  **Fluxo:** [`2.1 ajuste-saldo-por-planilha`](../../../app/odoo/estoque/fluxos/2.1-ajuste-saldo-por-planilha.md)  ·  **Subagente:** `gestor-estoque-odoo`  ·  **Arquivados em:** [`_validados/ajustando-quant-odoo/`](../../../scripts/inventario_2026_05/_validados/ajustando-quant-odoo/VALIDACAO.md) (2026-05-23, validação por log; `--confirmar` em caso real pendente).

| Script | O que MINERAR (valor único) | Situação |
|--------|------------------------------|----------|
| `11_ajuste_negativo_cd` | validação anti-negativar + anti-reserva | SUPERADO → _validados/ (2026-05-23) |
| `12_ajuste_positivo_cd` | criar lote+quant se faltar | SUPERADO → _validados/ (2026-05-23) |
| `13_ajuste_positivo_fb` | idem (FB) | SUPERADO → _validados/ (2026-05-23) |
| `14_ajuste_positivo_cd_v2` | idem | SUPERADO → _validados/ (2026-05-23) |
| `criar_saldo_positivo_lf` | tracking lot/none/serial; soma; sem-lote | SUPERADO → _validados/ (2026-05-23) |
| `ajuste_estoque_lf_pasta17` | realocação +/- entre lotes; **NÃO valida soma=0** (quem valida net-zero é `transferir_lote.py`); ⚠️ **dead-code** branch `COMPOSTO` (`:180`) + docstring stale — a "salvaguarda de lote-composto" anunciada **não existe** no código | AO-CAPINAR (corrigir docstring ao capinar) |
| `limpar_quants_ghost_210030005_fb` | zerar por `quant_id`; quant ghost residual | AO-CAPINAR (hook quant_id pronto) |
| `zerar_negativos_fb` | **algoritmo de compensação** (consome outros lotes p/ zerar negativo) | AO-CAPINAR (orquestrador sobre quant) |
| `corrigir_reserved_negativo_fb` | `resetar_reserva` (reserved<0) | AO-CAPINAR (hook pronto) |
| `fat_lf_03_prestage` | relocar saldo de sub-locais → location principal | AO-CAPINAR |
| `fat_lf_06_consolidar_validos` | **G014**: pular lote vencido / exigir lote válido | AO-CAPINAR |

## → `scripts/transfer.py` (StockInternalTransferService) — transferência de lote

**Skill:** `transferindo-interno-odoo` ([SKILL.md](../../../.claude/skills/transferindo-interno-odoo/SKILL.md)) · **Fluxo:** [`2.2 realocar-saldo`](../../../app/odoo/estoque/fluxos/2.2-realocar-saldo.md) · **Subagente:** `gestor-estoque-odoo` · **Arquivados em:** [`_validados/transferindo-interno-odoo/`](../../../scripts/inventario_2026_05/_validados/transferindo-interno-odoo/VALIDACAO.md) (2026-05-24, dry-run validados; --confirmar pendente demanda real).

| Script | O que MINERAR | Situação |
|--------|---------------|----------|
| `10_executar_emergenciais_fb` | MIGRAÇÃO→canônico (9 casos) | SUPERADO → _validados/ (2026-05-24) |
| `padronizar_migracao` | renomear `MIGRACAO`→`MIGRAÇÃO` (cedilha) | SUPERADO → _validados/ (2026-05-24, com limitação 2-grafias documentada) |
| `substituir_lote_205030410_fb` | lote→lote, 1 produto (unreserve→transfer→reassign) | AO-CAPINAR (composição cross-skill com 2.4 — VIVO) |
| `13_transferencia_migracao_fb` | MIGRAÇÃO→lote canônico (lista) | AO-CAPINAR (orquestrador planilha — VIVO) |
| `15_transferencia_para_migracao` | **semântica D010**: `diff>0 → lote→MIGRAÇÃO` (4.888 linhas) | AO-CAPINAR (orquestrador planilha — VIVO) |
| `15r_transferencia_reversa` | **semântica D010 inversa**: `diff>0 → MIGRAÇÃO→lote` | AO-CAPINAR (orquestrador planilha — VIVO) |
| `15_transferir_preprod_para_estoque_fb` | Pré-Prod→Estoque (já argparse) | AO-CAPINAR (fundir c/ 17 — VIVO) |
| `17_transferir_preprod_lf_para_estoque` | idem LF | AO-CAPINAR (fundir c/ 15 — VIVO) |
| `ajuste_fb_cd_indisponivel` | **semântica D013**: De-Local/De-Lote→Para + wildcard sub-locais; gotcha 2 lotes MIGRAÇÃO/produto (G022); checkpoint incremental | AO-CAPINAR (orquestrador planilha + wildcard — VIVO) |
| `transferir_local_pasta22` | **De/Para LOCAL+LOTE (Pasta22)**, multi-empresa (FB/CD/LF), wildcard saída → Indisponível/MIGRAÇÃO; 3 premissas explícitas (qty BRUTA, P-15/05 literal+sem-lote, todos internos) | AO-CAPINAR (orquestrador planilha + wildcard — VIVO) |
| `transferir_indisp_para_estoque_p15_cd` | Indisponível→Estoque/P-15/05 no CD (B inter-local, 2 passos); guard de quant_id esperado; hard-fail saldo insuficiente | AO-CAPINAR (caso ad-hoc — VIVO; Skill 2 modo B cobre o átomo) |

> **Skill 2 status 🟡 mín viável:** átomos `transferir_entre_lotes_v2` (lote→lote mesma loc) + `transferir_entre_locations` (loc→loc mesmo lote) cobertos pela skill. Orquestradores (planilha, retries, sharding, checkpoint, semânticas D010/D012/D013) permanecem VIVOS até fluxos compostos serem escritos (demanda-driven).

## → `scripts/quant.py` + orquestrador MIGRAÇÃO↔Indisponível

> **Nota arquitetural (CR2#2, 2026-05-24 v2):** os scripts que MOVEM saldo entre locations
> (`mover_migracao_para_indisponivel`, `ajuste_fb_cd_indisponivel`, `transferir_local_pasta22`,
> `transferir_indisp_para_estoque_p15_cd`) são **orquestradores que compõem a Skill 2
> `transferindo-interno-odoo`** (modo B loc→loc, ou modo A wildcard). Estão listados na seção
> [`scripts/transfer.py`](#-scriptstransferpy-stockinternaltransferservice--transferência-de-lote) acima.
> Mantemos referência aqui apenas para os scripts cujo PADRÃO específico é "movimento
> envolvendo MIGRAÇÃO↔Indisponível com lógica adicional" (CSV de pulados, etc).

| Script | O que MINERAR | Situação |
|--------|---------------|----------|
| `mover_migracao_para_indisponivel` | 3 filiais (B mover_loc para FB/CD + A relocate_lote para LF); **quants com reserva pulam → gera CSV** (liga a cancelar_reserva); MIGRAÇÃO se mantém | AO-CAPINAR (Skill 2 cobre o átomo; orquestração + CSV pulados pertencem a fluxo composto — VIVO) |
| `executar_fluxo_b_vivas` | **fluxo composto cross-skill**: cancel invoice + return picking + transfer→Indisponível. Passo 3 = Skill 2; passos 1+2 = `faturando-odoo` (futuro) + `operando-picking-odoo` (futuro) | AO-CAPINAR (fluxo composto cross-skill — VIVO; ver MINERACAO_SKILL2_2026_05_24.md §"COM-BUG G-TRANSFER-01") |

> **Removidos desta seção (2026-05-24 v2 — CR2#2 reconciliação):** `ajuste_fb_cd_indisponivel`, `transferir_local_pasta22`, `transferir_indisp_para_estoque_p15_cd` movidos para a seção `scripts/transfer.py` (são orquestradores de transferência interna — Skill 2 cobre o átomo; orquestração permanece VIVA).

## → `scripts/picking.py`

| Script | O que MINERAR | Situação |
|--------|---------------|----------|
| `16_cancelar_pickings_fantasmas` | filtro picking fantasma (>7d, origin C24xxxxx/sem origin) | AO-CAPINAR |

## → `scripts/cancelar_mo.py` (GAP — criar)

| Script | O que MINERAR | Situação |
|--------|---------------|----------|
| `cancelar_mos` | base genérica (argparse, filtro data/estado) | AO-CAPINAR (base do gold) |
| `14_cancelar_mos_antigas_fb` | **filtro consumo=0** (cancelar com consumo = furo contábil); sub-locais Pré-Prod | AO-CAPINAR |

## → `scripts/reserva.py` (StockReservaService) — operar reservas no Odoo

**Skill:** `operando-reservas-odoo` ([SKILL.md](../../../.claude/skills/operando-reservas-odoo/SKILL.md))  ·  **Fluxo:** [`2.4 cancelar-reserva-orfa`](../../../app/odoo/estoque/fluxos/2.4-cancelar-reserva-orfa.md)  ·  **Subagente:** `gestor-estoque-odoo`  ·  **Arquivados em:** [`_validados/operando-reservas-odoo/`](../../../scripts/inventario_2026_05/_validados/operando-reservas-odoo/VALIDACAO.md) (2026-05-23, write real validado em 6 pickings + 15 quants).

| Script | O que MINERAR (valor único) | Situação |
|--------|------------------------------|----------|
| `remover_reservas_saida` | base 4 companies; 3 fases (pickings.do_unreserve + MOs.do_unreserve + zerar reserved residual); batch 50 com fallback | SUPERADO → _validados/ (2026-05-23) |
| `cancelar_reservas_migracao` | **G024/G025**: cirurgia por CSV — unlink ML órfã + recompute manual; `do_unreserve` por picking | SUPERADO → _validados/ (2026-05-23) |
| `limpar_reservas_fantasma` | fallback de métodos Odoo CIEL IT (`do_unreserve`/`button_unreserve`/`action_unreserve`); reassign opcional pós-unreserve | SUPERADO → _validados/ (2026-05-23) |

> **Átomos implementados** (mínimo viável, write real validado): `cancelar_moves_orfaos` (cirurgia preservando picking), `cancelar_picking_inteiro` (action_cancel cascade), `zerar_reserved_residual` (cleanup pós-unlink).
> **Previstos** (catálogo): `unreserve_picking`, `unreserve_mo(reassign=)`, `find_orphan_mls` — adicionar conforme demanda.

## → `scripts/consulta_quant.py` (StockQuantQueryService) — READ ao vivo no Odoo

**Skill:** `consultando-quant-odoo` ([SKILL.md](../../../.claude/skills/consultando-quant-odoo/SKILL.md))  ·  **Fluxo:** [`2.9 consulta-quant-ao-vivo`](../../../app/odoo/estoque/fluxos/2.9-consulta-quant-ao-vivo.md)  ·  **Subagente:** `gestor-estoque-odoo` (READ direto)  ·  **Arquivados em:** [`_validados/consultando-quant-odoo/`](../../../scripts/inventario_2026_05/_validados/consultando-quant-odoo/VALIDACAO.md) (2026-05-23, dogfooding caso real 4856125 + auditoria 104 pares).

| Script (read) | O que MINERAR | Situação |
|---|---|---|
| `monitor/1_baixar_estoques` | snapshot batch CSV `(filial, cod, lote, location, qty, valor)` | MANTER (snapshot pesado, fluxo CSV — átomo previsto `snapshot_estoque_por_lote`) |
| `auditoria/levantar_estoque_fora_principal` | classificação por `parent_path` + `usage` (ESTOQUE_RAIZ / FILHA / INTERNAL_FORA / TRANSIT / VIRTUAL_*) | AO-CAPINAR (átomo previsto `saldo_fora_principal`) |
| `auditoria/{comparar_sot_*, diff_*, relatorio_*, investiga_*}` (~30 scripts) | queries específicas (cross-SOT, diff entre snapshots, investigação) | MANTER (operação viva — átomos previstos cobrem subconjunto) |

> **Átomos implementados** (mínimo viável): `listar_quants(cods, empresas, pares_cod_empresa, locations_excluir, com_lote, only_principal, agregar)` + `auditar_pares(pares_cod_empresa)`.
> **Previstos** (catálogo): `listar_move_lines`, `listar_pickings`, `find_orphan_mls`, `snapshot_estoque_por_lote`, `saldo_fora_principal` — adicionar conforme demanda.

## → `orchestrators/inventario_pipeline.py` (faturamento inter-company — ~20 gotchas)

| Script | O que MINERAR | Situação |
|--------|---------------|----------|
| `09_executar_onda1_bulk` | pipeline A-F; **G004/G011/G016/G019/G023** + quarteto fiscal G035/G017/G007/G018 | AO-CAPINAR |
| `09c_executar_onda2_fb_cd` | `processar_transfer_only` (etapas 19-37) | AO-CAPINAR |
| `entrada_fb_piloto` | entrada via DFe (etapas 0-18) | AO-CAPINAR |
| `fat_lf_02_carregar` | mapeamento TIPO→ação; ciclo isolado | AO-CAPINAR |
| `fat_lf_04_executar` | driver B-F por ciclo | AO-CAPINAR |
| `fat_lf_05_executar_clean` | **G028**: reserva explícita p/ bug multi-lote (59.9→12.3) | AO-CAPINAR |
| `fat_lf_cleanup` | fluxo de erro: return picking + cancel invoice + reset fase | AO-CAPINAR |
| `fat_lf_resume.sh` | **shell**: loop resume B→D **resiliente a SSL drop (G016)**, idempotente | AO-CAPINAR (resiliência do orquestrador) |
| `fat_lf_resume_entrada.sh` | **shell**: loop resume E+F resiliente a hang do robô CIEL IT | AO-CAPINAR |
| `teste_210030325_lf` | piloto E2E histórico | JÁ-MORTO (vira exemplo no GUIA) |

## → `orchestrators/pre_etapa_executor.py` (+ fluxo de proposta F2-F4)

| Script | O que MINERAR | Situação |
|--------|---------------|----------|
| `03b_planejar_pre_etapa_cd` | chama `PreEtapaEstoqueService.planejar` | AO-CAPINAR |
| `04b_propor_pre_etapa_cd` | persistir ajustes pré-etapa (DELETE+INSERT, backup) | AO-CAPINAR |
| `09b_executar_pre_etapa` | executor: TRANSF_INTERNA_POS/NEG + POSITIVO_PURO | AO-CAPINAR |
| `04_propor_ajustes` | `resolver_operacao_por_tipo_produto`; ondas; aprovar c/ hash | AO-CAPINAR |

## → gold de LEITURA / DIFF (`_utils.py` + 1-2 scripts de leitura consolidados) 📖

| Script | O que MINERAR | Situação |
|--------|---------------|----------|
| `monitor/0_pipeline`, `monitor/1_baixar_estoques`, `monitor/2_baixar_movimentacoes`, `monitor/3_agregar_lote`, `monitor/4_gerar_diffs`, `monitor/_comum` | pipeline estoque→movs→agregação→diff; `norm_lote`/`is_migracao`/`m2o_id` p/ `_utils` | MANTER (vira gold leitura) |
| `01_extrair_estoque_odoo` | extração quants por company | MANTER → gold leitura |
| `08_extrair_pos_execucao` | comparar proposto×realizado | MANTER → gold leitura |
| `02_carregar_inventario_xlsx` | parser planilha inventário | MANTER (helper) |
| `extrair_estoque_locais_emp` | extração excluindo Indisponível | MANTER → gold leitura |
| `auditar_migracao_fora_indisponivel` | check MIGRAÇÃO fora dos locais 31088-91 | MANTER → gold check |
| `auditoria/checar_autorizacao_sefaz` | check SEFAZ real (l10n_br_xml_aut_nfe) | MANTER → gold check |
| `auditoria/verifica_reservas_pos_cancel` | check reservas pós-cancel | MANTER → gold check |
| `auditoria/auditar_pickings_sem_fatura_e_nf_pendente` | detecta picking LF sem fatura + DFe pendente (risco de duplicar entrada) | MANTER → gold check |
| `rastrear_movs_item` | rastreio movs por produto (já argparse) | MANTER (utilitário) |
| `03_confrontar_inv_vs_odoo` | confronto inv×odoo (regras lote **P6/P9**) | AO-CAPINAR (gold diff) |
| `auditoria/comparar_sot_full`, `comparar_sot_vs_fontes`, `confronto_4_fontes`, `diff_inv_vs_odoo_atual_sem_migracao`, `diff_lotes_nao_migracao`, `inv_teorico_e_novo_diff`, `relatorio_final_sot`, `sot_com_lotes` | **9 variações da MESMA comparação SOT** → consolidar em 1 gold diff | AO-CAPINAR (maior redução de duplicação de leitura) |
| `auditoria/levantar_estoque_fora_principal`, `levantar_mos_antigas_nao_efetivadas`, `medir_consumo_mos_antigas`, `datas_reservas_preprod`, `saldo_transito_industrializacao_fb`, `relatorio_faturas_intercompany_sem_entrada`, `cruzar_entrada_lf_manual_vs_dfe`, `conferir_fluxo_c_e_canary_a` | levantamentos pontuais (alguns viram checks reutilizáveis) | QUANDO-OP-FECHAR (maioria) |
| `auditoria/extrair_movimentacoes_odoo` | extração movs (exclui recebimento LF Render) | MANTER → gold leitura |
| `fat_lf_00_preflight`, `fat_lf_01_stock_audit`, `fat_lf_diag`, `fat_lf_inspect_invoice` | pré-flight/diagnóstico do faturamento | QUANDO-OP-FECHAR |

## → JÁ-MORTO (discovery F0 + pontuais — arquivar agora em `_historico/`)

`00_audit_odoo_realidade`, `00b_investigar_gotchas`, `00c_investigar_g003`, `00d_investigar_variacoes`, `00e_investigar_pickings`,
`auditoria/investiga_metodo_entrada`, `auditoria/investiga_picking_317297`, `auditoria/investiga_vinculo_fatura_picking`,
`auditoria/rastrear_moves_pickings_fb_s2`, `auditoria/dados_pickings_fb_suspeita2`, `auditoria/verificar_hipotese_c_devolucao_manual`,
`baixar_xml_preview_626032` (G008 pontual), `debug_sefaz_608607` (debug piloto).

> Valor residual desses: a lógica de descoberta deles (location_id/picking_type/fiscal_position reais) **já foi destilada** nas decisões D000-D003 e nas constantes — por isso JÁ-MORTO.

---

## Scripts criados DURANTE a sessão (2026-05-20) — operação viva (+10 → 100)

| Script | O que é / MINERAR | Gold destino | Situação |
|--------|--------------------|--------------|----------|
| `ajuste_inventario.py` | orquestrador da Família A que **eu criei** nesta sessão (planilha → `quant.py`) | exemplo de orquestrador | EXEMPLO (vira referência do GUIA) |
| `transferir_lote.py` | **JÁ É o genérico de transferência net-zero** (planilha `diff_qtd`, net-zero por filial/produto) — supera 15/15r/pasta17 | orquestrador sobre `transfer.py` | **PROMOVER (não recriar!)** |
| `recuperar_aumentos_falhos.py` | **gotcha novo**: `lot_id` de empresa errada ('Empresas incompativeis') quebra AUMENTO em transfer | `transfer.py` (preservar gotcha) | AO-CAPINAR |
| `relotar_migracao_para_lotes_fb.py` | MIGRAÇÃO→lotes reais + envio a Estoque (inv-adjust 2 passos) | MIGRAÇÃO↔Indisponível | AO-CAPINAR |
| `transferir_fluxo_c.py` | **FLUXO C**: 2 NFs canceladas → FB/Indisponível/MIGRAÇÃO | MIGRAÇÃO↔Indisponível | AO-CAPINAR |
| `escriturar_dfe_lf.py` | **FLUXO A / assunto NOVO**: escriturar in_invoice de entrada LF a partir do DFe (direção inversa; NÃO reusa RecebimentoLf) | orquestrador escrituração (novo) | AO-CAPINAR |
| `limpar_reservas_fantasma.py` | **GAP cancelar_reserva já implementado**: `action_unreserve` + reassign por MO | `cancelar_reserva.py` | AO-CAPINAR (melhor base do gold) |
| `auditoria/teste_unlink_moveline_fantasma.py` | canary destrutivo: unlink de 1 move.line fantasma | `cancelar_reserva.py` | AO-CAPINAR (validação) |
| `auditoria/analise_picked_reservas.py` | **quirk CIEL IT #9 `picked`**: consumo realizado vs reserva real | leitura/check | MANTER → gold check |
| `auditoria/investiga_residual_reservas.py` | caracteriza over-reservation (move.line `assigned` sem lastro) | leitura/check | MANTER → gold check |

**Reflexos no `MAPA_ASSUNTOS.md` (a propagar):** (1) assunto NOVO *Escrituração DFe entrada* (FLUXO A); (2) os **Fluxos A/B/C** de tratamento de NFs problemáticas (escriturar / cancelar+devolver / transferir→Indisponível); (3) GAP cancelar_reserva já tem base concreta (`limpar_reservas_fantasma`); (4) gotchas novos: quirk `picked` #9, `lot_id` de empresa errada em transfer.

---

## Cobertura — INSTANTÂNEO (não estável)

> Em 2026-05-20 ~23h: **103 scripts** (101 `.py` + 2 `.sh`). **NÃO é uma garantia de 100%** — o nº já mudou 4×
> nesta operação (89→90→100→101 `.py`). O reviewer independente achou `transferir_local_pasta22.py` que meu
> `find` (rodado mais cedo) não tinha. **Reconciliar com `find` é obrigatório antes de qualquer ação.**

| Destino | Qtd | Destino | Qtd |
|---------|-----|---------|-----|
| quant.py | 11 | inventario_pipeline + escrituração (orch) | 11 (9 py + 2 sh) |
| transfer.py | 9 | pre_etapa_executor (orch) | 4 |
| MIGRAÇÃO↔Indisponível | 6 | leitura/diff/check | 39 |
| picking.py | 1 | JÁ-MORTO | 13 |
| cancelar_mo.py | 2 | cancelar_reserva.py | 4 |
| orquestradores-exemplo (ajuste_inventario, transferir_lote) | 2 | | |

> **Conferência (instantâneo):** write `34` (quant 11 + transfer 9 + indisp **7** + picking 1 + cancelar_mo 2 + cancelar_reserva 4) + orquestradores `15` (pipeline/escrit/resume 11 + pre_etapa 4) + exemplos `2` + leitura/check `39` (monitor 6 + raiz 11 + auditoria 22) + JÁ-MORTO `13` = **103** (101 `.py` + 2 `.sh`). Não contam: 106 logs `auditoria/log_*.json` (saída) + 2 `README.md` (docs).
