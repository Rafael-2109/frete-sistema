# ROADMAP_SKILLS — task-list física (capinar átomo por átomo)

**Criado:** 2026-05-22 | **Constituição:** `app/odoo/estoque/CLAUDE.md` | **Mineração:** `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`
**Para:** Claude Code + agente web. Este é o **arquivo de progresso vivo** da migração 105-scripts → ~8 skills-átomos + subagente `gestor-estoque-odoo`.

> **HANDOFF enxuto v18 Fase 0** — antes (até 2026-05-26 v18) acumulava blocos "Sessão XYZ" cronológicos (~70 linhas/sessão; chegou a 807 linhas). Migrado para `VALIDACAO_FINAL_SESSAO.md` em v18 Fase 0 (decisão D-V18-5). **Próximas sessões NÃO adicionam mais bloco "Sessao XYZ" aqui — append em VALIDACAO**.

---

## ⏯️ ESTADO ATUAL E COMO CONTINUAR (HANDOFF — sempre ≤80 linhas)

### Como retomar (ordem)
1. `cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (worktree, branch `feat/estoque-odoo`).
2. `source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate`.
3. Carregar env: `set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a`.
4. **⭐ LER `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md` INTEIRO** (escudo contra desvios reincidentes — v18 Fase 0).
5. Ler `app/odoo/estoque/CLAUDE.md` (§1.1 + §3.1 + §6 + §6.5 + §14 + §15).
6. Ler este ROADMAP (handoff + checklist por skill).
7. Se sessão for sobre Skill 8 → ler `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (regra inviolável 0).

### Baseline pytest esperado
- **896 verdes** (tests/odoo/ em ~19s — 868 pós-WIRE R2 2026-06-15 + **28 net SAÍDA 2026-06-15** = 12 orchestrator saída + 10 provisionador + 6 monitor). Histórico: 688 v29+ (681 v28+ + 7 v29+) → 868 WIRE R2.

### Estado global (atualizado v18 Fase 0 — 2026-05-26)

| Skill / Componente | Status | Localização |
|--------------------|--------|-------------|
| Skill 1 `ajustando-quant-odoo` | ✅ MATURADA | `scripts/quant.py` |
| Skill 2 `transferindo-interno-odoo` | 🟡 **4 modos atômicos** (A/B/C/D) — D NOVO v21+ `transferir_loc_e_lote` (loc+lote em 1 chamada) — 44 pytest (33 v20+ + 11 net v21+) | `scripts/transfer.py` |
| Skill 2.4 `operando-reservas-odoo` | 🟡 mín viável (5 átomos) | `scripts/reserva.py` |
| Skill 4 `operando-mo-odoo` | 🟡 V7 (cancelar + concluir) | `scripts/mo.py` |
| Skill 5 `operando-picking-odoo` | 🟡 7 átomos LIVE v19+ (`preencher_lotes_picking` NOVO; `criar_picking_entrada_destino_manual` DEPRECATED) + **G-AUDIT-3 fix v22+** (idempotência cancel codificada) — 70 pytest (68 + 2 net v22+) | `scripts/picking.py` |
| Skill 6 `planejando-pre-etapa-odoo` | 🟡 mín viável COMPLETA v9 (planner + executor C3) | `scripts/pre_etapa.py` + `orchestrators/pre_etapa_executor.py` |
| Skill 7 `escriturando-odoo` | 🟡 **ABRANGENTE LIVE v25+ + WIRE R2 (2026-06-15)** (14 átomos: 10 v19+/v25+ + `montar_invoice_entrada_direta` (NF-2 montada-direto) + **3 NOVOS R2 15/06**: `resolver_chave_remessa` READ (R3 via referencia_ids da NF-1 saída — `s70`) · `marcar_vinculo_r3` (origin+refNFe na NF-1 entrada, substitui write cru s63/s64) · `postar_invoice` (action_post idempotente, NÃO SEFAZ, substitui s67 cru)) — +13 pytest R2 (`test_escrituracao_r3_atomos` 9 + `test_escrituracao_postar_invoice` 4); AP1+AP4 ✅ | `scripts/escrituracao.py` |
| Skill 8 `faturando-odoo` **ATÔMICA L2 v24+** (AP6 RESOLVIDO PARCIAL — NOVA arquitetura) | 🟢 **5 átomos ATÔMICOS LIVE v24+** (`validar_invoice_constants`, `liberar_faturamento`, `polling_invoice`, `validar_invoice_pos_robo`, `transmitir_sefaz`) — 28 pytest verdes — `scripts/faturamento.py` ~750 LOC | `scripts/faturamento.py` + `.claude/skills/faturando-odoo/SKILL.md` (fachada atualizada v24+) |
| Orchestrator C3 LEGACY `inventario_pipeline` (renomeado de `faturamento_pipeline` em v27+ S3 — **stub alias REMOVIDO v28+ S6.b** + **cleanup deprecated v16/v17.5 v28+ post-S7**) | 🟡 PIPELINE A-F + RECOVERY + FLUXO L3 1.2.x LIVE v19+ + **opt-in `--usar-fluxo-l3-v19` v20+** + **F1+F2b+F3a-d+F4 v25+** + **opt-in `--usar-skill8-atomica-v25` v27+ S1** + **helper `_executar_etapa_e_via_fluxo_l3` v28+ S7** + **F1+F3 v29+** (agregado detecta `'PARCIAL'` + audit trail `usuario` no FLUXO L3 via `_passo`/`ajuste_id_ref`) — 100 pytest = 96 v28+ + 4 F1 v29+ | `orchestrators/inventario_pipeline.py` (~6230 LOC) |
| **Orchestrator C3 `entrada_retorno_industrializacao` (WIRE do R2 — NOVO 2026-06-15)** | 🟡 **CONSTRUÍDO dry-run-first, validado PROD (READ)** — compõe o FLUXO L3 1.2.4 end-to-end (NF-1 caminho A + picking C9 + NF-2 montada-direto + revaloração + R3 + gate por ciclo); 8 modos CLI (plan→escriturar-nf1-po→escriturar-nf1-invoice→montar-nf2→postar-nf2→revalorar→postar-nf1→medir), cada escrita gated `--confirmar`; 12 pytest composição. **PENDENTE: execução real (go fresco) em ciclo natural + reconciliar 26489 (D)** | `orchestrators/entrada_retorno_industrializacao.py` |
| **Orchestrator C3 `saida_retorno_industrializacao` (lado nosso da SAÍDA — NOVO 2026-06-15)** | 🟡 **READ-only — oráculo/validar/medir** (DECISÃO SOT §6.3 Opção B: a EXECUÇÃO é server-side, ver `provisioning/`). `planejar(nf1_id)` (spec via descoberta) · `validar(nf1,nf2)` (NF-2 da SA vs spec: CFOP 5902/CST 50/conta 1150100012/total/R3) · `medir` (baixa PASSIVA 26667 pelo ciclo). 12 pytest. ZERO escrita Odoo. | `orchestrators/saida_retorno_industrializacao.py` |
| **Categoria INFRA-ODOO `provisioning/` (NOVO 2026-06-15 — fora do sistema de skills, §1.1+CLAUDE.md:410-412)** | 🟡 **framework testado + bodies versionados** — `sa_retorno_industrializacao` (provisionador idempotente SA+cron por `name` + `verificar` READ; bodies G1 montagem [🔴 genealogia safe_eval PENDENTE CANARY] / G2 transmissão [fiel s54 provado]) + `monitor_sa_industrializacao` (D8 grava flag + hook SessionStart lê). `dry_run` default; crons gated por canary. 16 pytest (10 provisionador + 6 monitor). **NADA escrito no Odoo.** | `provisioning/` + `.claude/hooks/sessionstart_industrializacao_sa.py` |
| Skill 9 `consultando-quant-odoo` (READ) | 🟡 mín viável (3 modos G030) | `scripts/consulta_quant.py` |
| Sub-skill C5 `auditando-cadastro-fiscal-odoo` | 🟡 V1 'inventario' + G038 v22+ + **G007+l10n_br_tipo_produto v24+** — 20 pytest (16 + 4 net v24+ standard_price=0 WARN + tipo_produto BLOQUEIO) | `scripts/cadastro_fiscal_audit.py` |
| Fluxos L3 escritos | 13: 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, **1.2.1 v19+**, **1.2.2 v19+**, **1.2.4 (WIRE entrada 15/06)**, **1.1.4 (emissão saída 15/06)** | `fluxos/` |
| Fluxos L3 pendentes (galho 1.1 + 1.3 + 2.3) | 1.1.1.x, 1.1.2, 1.1.3, 1.3, 2.3 | `fluxos/` ⬜ |

> **Sessão 2026-06-02 — Canary REAL remessa avulsa FB→LF (INDUSTRIALIZACAO_FB_LF) ✅ end-to-end** (linha de trabalho SEPARADA do canary S2 inventário). Fluxo **1.3.1** LIVE: SAÍDA NF RPI/2026/00248 autorizada SEFAZ (CFOP 5901) + ENTRADA NF ENTIN/2026/06/0004 posted (CFOP 1901). 4 fixes commitados local (NÃO pushados): **C7** (Skill 8 `_registrar_auditoria` guard avulso `ajuste_id None`, `9715c8f3d`) · **C9/C9.1** (Skill 5 `criar_picking_entrada_destino_manual` REABILITADO ex-DEPRECATED: `purchase_line_id` + `warehouse_id`/`partner_id` derivados, `a8835dbff`) · **C10** (Skill 7 `gerar_po_from_dfe` força context company do DFe — GOTCHA 1, `0169e1694`). +10 pytest. **Achado**: DFe-resumo (status 06) NÃO gera picking nativo → entrada manual vinculada à PO é o caminho padrão desta operação (ver `CLAUDE.md §14 D-V30-1` + `fluxos/1.3.1-remessa-avulsa-insumo.md` + memória `capacitacao_gestor_remessa_fb_lf`). **Pendente**: Rafael ajustar estoque (paliativo 15:40 + trânsito 26489) + follow-ups (b) limpar docs 'compra' + (c) avaliar 7 ações restantes do mapeamento. Prompt dedicado: `PROMPT_FOLLOWUPS_REMESSA_FB_LF.md`.

### Cleanup banco local v26+ (2026-05-27)

- 30 ajustes `FATURAMENTO_LF_2026_05_20 / F5d_BLOCKER_TX / INDUSTRIALIZACAO_FB_LF / APROVADO` DELETADOS (decisão Rafael "isso não existe mais").
- 67 registros `operacao_odoo_auditoria` vinculados (soft-link via `tabela_origem`+`registro_id`) DELETADOS junto.
- **Pós-cleanup**: zero candidatos naturais para canary REAL F1-F4 (apenas 177465 AVULSO_FRASCO em F5e_SEFAZ_OK, já idempotente Odoo via cirurgia manual v24+). Canary REAL deferido para próxima INDUSTRIALIZACAO_FB_LF natural do operador.
- Commit: `701e4885`.

### Próximo passo (v30+) — corrigir cadastro CFOP FB→5949 (R3b, fiscal) → desbloquear canary S2

**v29+ CONCLUÍDA** (2026-05-29 — commit pendente; histórico v28+ em VALIDACAO):
1. ✅ **F1 (HIGH)** — agregado `executar_pipeline_bulk` detecta `'PARCIAL' in s`; `EXECUTADO_PARCIAL` das etapas não escapa mais p/ `EXECUTADO_OK`. 4 pytest.
2. ✅ **F3 (MEDIUM)** — `usuario` propagado ao audit trail do FLUXO L3 via `_passo` (`ajuste_id_ref=ajs[0].id` + guard; `_registrar_auditoria` voltou a `ajuste_id: int` — fix pós code-review: `registro_id` é NOT NULL). 3 pytest.
3. ✅ **Code-review** (sonnet, background): "SHIP IT — zero findings ≥80%"; nota `registro_id` NOT NULL CORRIGIDA.
4. ✅ **Auditoria CFOP 5902** (2 subagentes READ): ~10 NFs LF→FB DEV tipo 4 com 5902 (correto 5949). Causa cadastral: Operação 2710 GENÉRICA (partner_ids=[]) vs 2719 (5949) restrita ao CD. Recomendação **R3b** (criar Operação LF→FB 5949 partner_ids=[1]). Decisão+execução fiscal Rafael. Detalhe: `CLAUDE.md §14 D-V29-1`.
5. ✅ Baseline: 681 → **688 verdes** (+7).
6. ⛔ **Canary S2 BLOQUEADO**: backlog 2026-05-20 (21/21) já escriturado → duplica; cadastro FB gera 5902 → novo DEV_LF_FB nasce errado. Desbloqueio = correção cadastral R3b.

**v30+ alvo**:
1. **Correção cadastral CFOP FB→5949** (R3b — Rafael/fiscal cria Operação LF→FB 5949 partner_ids=[1] no Odoo) → desbloqueia canary S2.
2. **Canary S2** ETAPA E v28+ S7 (após cadastro OK + lote natural X→FB/X→LF) via `--usar-fluxo-l3-v19`.
3. **Canary S2.a** skill8 ATÔMICA (INDUSTRIALIZACAO_FB_LF natural) via `--usar-skill8-atomica-v25 --confirmar-sefaz`.
4. **Após canary OK**: S6 cleanup NÍVEL 2 ~2500 LOC + flip defaults.
5. **Pendência fiscal Rafael**: tratamento das 10 NFs já emitidas com 5902 (SARET/2026/00003-12).

### Próximo passo (v27+) — opt-in `--usar-skill8-atomica-v25` + rename + expand CONSTANTS FB+CD + folhas L3 (S0 canary REAL deferido) [ARQUIVADO — ver v28+ acima]

**v25+ S0 CONCLUÍDA** (2026-05-27 — commit `ea505c0e`):
1. ✅ Validação Rafael dos 5 achados do agente v24+ (cirurgia AVULSO_FRASCO): corrigido diagnóstico errado #1 + confirmados #2/#3/#4 + descartados G039/G-PERM-1 como causa.
2. ✅ **F1** — `_executar_etapa_f_via_fluxo_l3` resolve `lotes_data` por invoice via `_resolver_pids_em_batch` + agrega `(product_id, lote_destino)` com `abs(qtd_ajuste)` (espelha legacy v17.5 + transform vazio/'MIGRAÇÃO' → `INV-{cod}-{HOJE}`).
3. ✅ **F1b** — `executar_fluxo_l3_1_2_x` default `lote_default='MIGRAÇÃO'` → `None`.
4. ✅ **F2a** — Novo átomo `EscrituracaoLfService.alinhar_dfe_lines_company` (~120 LOC) generaliza B-V23-1 p/ caminho A + invocado no passo 1.5.
5. ✅ **F2b** — Passo 6.5 força G023 company em picking + moves nativos.
6. ✅ **F3a-d** — `L10N_BR_TIPO_PEDIDO_POR_ACAO` refatorado `Dict[str,str]` → `Dict[str,Dict[str,str]]` (`'dfe'`/`'po'`); `INDUSTRIALIZACAO_FB_LF → {'dfe': 'compra', 'po': 'serv-industrializacao'}`; `preencher_po` aceita `l10n_br_tipo_pedido`. **(⚠️ `dfe` desta ação REVERTIDO p/ 'serv-industrializacao' por C6/D-V30-1 2026-06-02 — 'compra' quebra `escriturar_dfe`. As 7 ações restantes seguem `dfe='compra'` CANDIDATE = bug latente; ver §2.)**
7. ✅ **F4** — `team_id` STATIC FIXO **143** p/ LF + G039 by-pass quando `company_destino=5`.
8. ✅ 8 pytest novos (4 F2a + 3 F3c em `test_escrituracao_lf_service_v19.py`) + 2 testes G039 reescritos refletindo F4.
9. ✅ Baseline pytest: 655 → **662 verdes** (+7 net).
10. ⚠️ S1 opt-in `--usar-skill8-atomica-v25` + S3 rename + S4 expand CONSTANTS + S5 folhas L3 ADIADOS v26+ (priorizado S0 fixes pos-cirurgia).

**v24+ CONCLUÍDA** (2026-05-27 — commit `038e5e89`):
1. ✅ S2 AP6 refator (5 átomos separados): criada Skill 8 ATÔMICA L2 em `app/odoo/estoque/scripts/faturamento.py` (~750 LOC) com 5 átomos espelhando Skill 7 ABRANGENTE v19+: `validar_invoice_constants` · `liberar_faturamento` · `polling_invoice` · `validar_invoice_pos_robo` · `transmitir_sefaz`. Decisão arquitetural: 5 átomos separados (Rafael v24+) — NÃO 1 macro (recomendação Explore rejeitada porque macro = pattern DEPRECATED V1 STRICT).
2. ✅ 28 pytest verdes em `tests/odoo/services/test_faturamento_invoice_service.py`.
3. ✅ S4 Sub-skill C5 estender: 2 novos checks em `_check_ncm_weight_tracking` — G007 standard_price=0 (WARN) + l10n_br_tipo_produto ausente (BLOQUEIO). 4 pytest novos.
4. ✅ Atualizado SKILL.md fachada `faturando-odoo` (frontmatter ATÔMICA L2 + corpo seção "5 ÁTOMOS L2" + exemplo composição).
5. ✅ CLAUDE.md §6 Tabela 1 ganhou `faturando-odoo` ATÔMICA L2; §6.5 AP6 → RESOLVIDO PARCIAL; §14 D-V24-1 novo.
6. ✅ Baseline pytest: 622 → **654 verdes** (+32 net = 28 Skill 8 ATÔMICA + 4 C5).
7. ⚠️ S1 bulk REAL PROD PULADO: ciclo INVENTARIO_2026_05 só tinha 2 museums; FATURAMENTO_LF_2026_05_20 30 INDUSTR em F5d_BLOCKER_TX (risco SEFAZ); 261 PERDA/DEV destino=FB requer S3 (CONSTANTS FB) — ADIADO v25+.
8. ⚠️ S3 expand CONSTANTS FB+CD PULADO: requer discovery XML-RPC + tempo significativo — ADIADO v25+.
9. ⚠️ S5 folhas L3 1.1.x + 1.3 PULADO: dependem refator profundo orchestrator (substituir ETAPAs C+D pela nova skill ATÔMICA) — ADIADO v25+.

**v23+ + v23.5+ CONCLUÍDAS** (commit fd77f192 + d516ca69 + 26886c7d):
1. ✅ S0 G-PERM-1 investigado: causa raiz NÃO era ir.rule isolada; era cascata B-V23-1 + B-V23-2
2. ✅ S1 G039 átomo `garantir_purchase_team` + hook `_resolver_team_g039` + 14 pytest
3. ✅ S2 Fix raiz contador F status='EXECUTADO' + 3 pytest
4. ✅ S3 Caminho B FLUXO L3 1.2.x 100% PROD: invoice ENTIN/2026/05/0055 posted
5. ✅ S3 Workarounds manuais aplicados PROD (PO team 41→143, dfe.lines company 1→5, PO.lines account 22611→26459)
6. ✅ **B-V23-1 fix raiz** (v23.5+) `criar_dfe_a_partir_do_invoice_saida` codifica write `dfe.line.company_id=company_destino` pós-poll + 3 pytest
7. ✅ **B-V23-2 fix raiz** (v23.5+) novo átomo `resolver_account_id_por_company` + hook em `gerar_po_from_dfe` + 9 pytest
8. ✅ Baseline pytest: 580 → **609 verdes** (+29 net v23+v23.5+)

### Estado FINAL ajustes 176013/176014 PROD (v23+)
- status=EXECUTADO, fase_pipeline=F5f_ENTRADA_OK
- Picking SAÍDA 321601 (FB/SAI/IND/01602): state=done; Picking 321600 cancel preservado
- Invoice SAÍDA 716448 RPI/2026/00238: SEFAZ autorizada chave 35260561724241000178550010000945661007164482
- Invoice ENTRADA 717630 ENTIN/2026/05/0055: state=posted journal 1047 'ENTRADA REMESSA INDUSTRIALIZAÇÃO'
- PO 42419 C2619591: state=purchase, team=143 RAFAEL, picking 321617 done, invoice 717630
- DFe 43533: criado v22+, company=LF, lines company=LF (após fix v23+)

### Bugs arquiteturais descobertos v23+ (codificar v24+)

**B-V23-1**: Skill 7 `criar_dfe_a_partir_do_invoice_saida` cria dfe.lines com `company_id` da FONTE (FB) em vez de DESTINO (LF). Workaround manual v23+: write company_id=destino após criação. Fix raiz v24+ no átomo.

**B-V23-2**: Skill 7 `gerar_po_from_dfe`/`preencher_po` deixa PO.line.account_id apontando para account da company FONTE em vez de buscar account equivalente na company DESTINO. Workaround manual v23+: write account_id=equivalente_destino. Fix raiz v24+: novo átomo helper `resolver_account_id_por_company` + hook nos átomos da Skill 7.

**v26+ alvo** (canary REAL PROD F1-F4 + S1-S6 v25+ adiados):
1. **Canary REAL PROD F1-F4** — 1-5 ajustes INDUSTRIALIZACAO_FB_LF via `--usar-fluxo-l3-v19` validando que F1-F4 codificados eliminam workarounds manuais (lote correto + dfe.line.company alinhada + G023 force + tipos certo + team=143 fixo).
2. ✅ **Opt-in `--usar-skill8-atomica-v25`** no `executar_pipeline_bulk` (CONCLUÍDO v27+ S1 commit ab35d5f3 — helpers `_executar_etapa_c_via_skill8_atomica` + `_executar_etapa_d_via_skill8_atomica` delegam ETAPAs C+D aos atomos 3, 4 e 5 da Skill 8 ATOMICA L2; default OFF preserva 100% legacy = zero risco regressão; 6 pytest dispatch mockado verdes).
3. ✅ **Renomear orchestrator** `faturamento_pipeline.py` → `inventario_pipeline.py` + alias compat (CONCLUÍDO v27+ S3 2026-05-27 — stub re-exporta TODOS símbolos + main() entry-point CLI preservado; 8 imports externos preservados via stub; testes patcham via `inventario_pipeline.<nome>` no nome novo).
4. **Canary REAL PROD do opt-in skill8**: 1-5 ajustes validam paridade vs legacy. Após OK: remover ETAPAS C+D legacy (~500 LOC) + migrar 14 testes para `test_faturamento_invoice_service.py`.
5. **Bulk REAL PROD** via `--usar-fluxo-l3-v19` em conjunto maior de ajustes (validar B-V23-1+2 + F1-F4 fixes automáticos eliminam workarounds manuais).
6. ✅ **Expand CONSTANTS** FB=1 e CD=4 (CONCLUÍDO v27+ S4 2026-05-27 — discovery XML-RPC `stock.picking.type` confirma FB=1+52+54+6, CD=13+50+18, LF=19+24+64; CONSTANTS_FLUXO_L3 expandido p/ 3 companies; team_id=None p/ FB+CD com G039 dinâmico (LF STATIC=143 mantido); L10N_BR_TIPO_PEDIDO_POR_ACAO mapeado p/ todas 8 ações via MATRIZ_INTERCOMPANY (dfe='compra' p/ as 7 ações [CANDIDATE — **bug latente**, quebra `escriturar_dfe`, ver §2] + INDUSTRIALIZACAO_FB_LF corrigido p/ 'serv-industrializacao' C6/D-V30-1; po derivado de l10n_br_tipo_pedido_entrada); 4 pytest novos = 672 baseline; canary REAL FB/CD pendente próxima PERDA_LF_FB ou TRANSFERIR_*_CD natural — **alinhar `dfe` da ação a tipo da whitelist no mesmo canary**).
7. ✅ **Folhas L3 1.1.x + 1.3** (CONCLUÍDO v27+ S5 2026-05-27 — `1.1.1-faturamento-saida-pura.md` documenta composição Skill 8 ATÔMICA L2 ETAPAs C+D; `1.3-transferencia-completa.md` documenta composição 1.1.1 + 1.2.x end-to-end com decisão automática caminho A vs B; README árvore decisão atualizada com paths novos; markdown apenas, zero código novo).

### Estado dos ajustes 176013/176014 (v23+ retoma)
- id=176013/176014: `status='EXECUTADO', fase_pipeline='F5e_SEFAZ_OK', picking=321601, invoice=716448, chave_nfe='35260561724241000178550010000945661007164482'`
- Picking 321600 (FB/SAI/IND/01601): `state=cancel` (preservado pelo fix G-AUDIT-3)
- Picking 321601 (FB/SAI/IND/01602): `state=done` (criado v22+)
- Picking 321617 (LF/IN/...): gerado v22+ via button_approve PO 42419
- Invoice 716448 RPI/2026/00238: `state=posted, situacao_nf='autorizado', chave válida`
- DFe 43533 (LF): criado v22+ via caminho B com lines populadas
- PO 42419 C2619591: `state=purchase, team_id=143 'Aprovação LF - RAFAEL', picking_ids=[321617]`
- Invoice ENTRADA LF: NÃO CRIADA (passo 9 bloqueado G-PERM-1)
- Purchase team 143: criado v22+ (user_id=42, company=5)

**v23+ alvo**:
1. **S0 INVESTIGAR G-PERM-1** (task 15): listar `ir.rule` ativos em `l10n_br_ciel_it_account.dfe.line` + identificar rule que filtra Rafael (uid=42). Workaround: rodar pipeline com user com permissão.
2. **S1 CODIFICAR G039 INVARIANTE** (task 16): Skill 7 novo átomo `garantir_purchase_team(user_id, company_id)` + hook em `confirmar_po` OU `_executar_etapa_f_via_fluxo_l3` — SEMPRE criar/setar purchase.team ANTES de button_confirm.
3. **S2 FIX RAIZ CONTADOR F** (task 13): `_contar_pendentes_por_etapa` linha 4458 — ETAPA F filtro `status IN ('PROPOSTO','APROVADO','EXECUTADO')`.
4. **S3 COMPLETAR PASSO 9+10 CAMINHO B**: pós-S0 desbloqueio, re-rodar resume F → invoice entrada + ajustes F5f_OK.
5. **S4 INVESTIGAR PO to_approve regra exata** (task 14): comparar canary 627348 (caminho A autorizado) com PO 42419 (caminho B). Diferença: fiscal_position? valor? team_id?
6. **S2-S7 ORIGINAIS v22+** (se sobrar tempo): remoção tampão criar_picking_entrada_destino_manual + V1 STRICT wrapper + ETAPAS E/F legacy; refator AP6; expand CONSTANTS FB/CD; folhas L3 1.1/1.3/2.3; C5 G007+l10n_br_tipo_produto; lote literal P-15/05.

**Estimativa**: 2-3 sessões. **Bloqueia**: S2 remoção tampão depende de caminho B 100% (passo 9+10).

---

### Próximo passo (v22+) — pipeline retry + remoção tampão + refator nomenclatura (ARQUIVADO — ver bloco v23+ acima)

**v20+ CONCLUÍDA** (2026-05-26):
1. ✅ S1 cross-refs final (gestor-estoque-odoo árvore + ROUTING_SKILLS + fachada SKILL.md `faturando-odoo` Receita 5).
2. ✅ S2 canary REAL PROD FLUXO L3 1.2.x — caso INDUSTRIALIZACAO_FB_LF (invoice 627348, DFe 42868) — `FLUXO_OK` em 1190ms; ZERO duplicações em PROD. Validou caminho A; FIX B caminho 2 (`dfe_purchase_fiscal_id`) detectou IDEMPOTENT como previsto.
3. ✅ S2b FIX A em `escriturar_dfe` (idempotência via `campos_ja_iguais` + `data_preservada_tipo_igual`); FIX B em `gerar_po_from_dfe` (3 caminhos vínculo DFe↔PO minerados de `validacao_nf_po_service.py`); fix orchestrator whitelist linha 2939 aceitando `IDEMPOTENT_ESCRITURADO`. 4 pytest novos + 3 ajustados.
4. ✅ S3 opt-in `--usar-fluxo-l3-v19` no `executar_pipeline_bulk` + `_executar_etapa_f_via_fluxo_l3` + CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO (atual: só LF=5). Default OFF preserva 100% legacy. 3 pytest mockados.
5. ✅ S5 DeprecationWarning runtime em `criar_recebimento_orchestrado` (V1 STRICT wrapper). 1 pytest novo.
6. ✅ R3 doc fluxo 1.2.2 atualizado (premissa "INDUSTRIALIZACAO_FB_LF nunca tem DFe via SEFAZ" reescrita com fato empírico PROD 2026-05).

**v21+ FINALIZADA** (2026-05-26/27 — pausada com 3 bugs sequenciais descobertos no pipeline real):
1. ✅ Cancel 3 INT zumbi (317347, 320098, 320133) — Skill 5 modo cancelar
2. ✅ DELETE 23.483 linhas ciclo INVENTARIO_2026_05 (backup JSON em /tmp/backup_ajustes_INV_2026_05_20260526_191927.json)
3. ✅ **Skill 2 átomo NOVO `transferir_loc_e_lote`** (loc+lote em 1 chamada) — 11 pytest + SKILL.md + CLI modo D
4. ✅ Pre-criar lote literal 'P-15/05' lot_id=60033 (210010800 FB)
5. ✅ ETAPA 0 REAL: 250.330 SLEEVE + 1,8 CORANTE de Indisp/MIGRAÇÃO → Estoque/P-15/05 (4 quants atualizados/criados)
6. ✅ WRITE 2 produtos (price=0.05 + tipo='02'/'01' + auto-fix barcode)
7. ✅ INSERT 2 ajustes novos id=176013/176014 (status=APROVADO)
8. ✅ **Fix G-AUDIT-1**: removido `etapa=fase` do orchestrator linha 255 (pipeline_etapa carrega info) — bug schema INTEGER vs string crashou pipeline retry 1
9. ✅ **Migration G-AUDIT-2**: `operacao_odoo_auditoria.acao` VARCHAR(20)→VARCHAR(60), `status` →30, `pipeline_etapa` →40 (acomoda 'criar_picking_inter_company'=27 etc.) — arquivos .sql + .py em `scripts/migrations/`
10. ❌ **G-AUDIT-3 PENDENTE v22+**: Skill 5 `criar_picking_inter_company` reaproveita picking state=cancel (idempotência inadequada) → `action_assign` falha em F5b. 3 retries do pipeline NÃO chegaram ao SEFAZ.

### Estado dos ajustes 176013/176014 (v22+ retoma)
- id=176013/176014: `status=APROVADO, fase_pipeline='F5b_FALHA', picking_id_odoo=321600`
- Picking 321600 (FB/SAI/IND/01601): `state=cancel`
- Quants ETAPA 0: intactos (pipeline nunca tocou saldo)
- v22+ exige: fix Skill 5 G-AUDIT-3 + force-update ajustes (picking_id=NULL, fase=NULL) + retry pipeline

**v22+ alvo**:
1. Verificar resultado pipeline retry (rodando background ao final desta sessão)
2. Se pipeline OK: **remover tampão** `criar_picking_entrada_destino_manual` (Skill 5 v15a) + **remover wrapper V1 STRICT** `criar_recebimento_orchestrado` + **remover ETAPAS E/F legacy** do orchestrator
3. Se pipeline FALHA mid-stream: investigar erro novo (não G-AUDIT-1 mais — pode ser cadastro fiscal não cobertos por C5, robô CIEL IT lento, ou SEFAZ rejeição)
4. **Refator nomenclatura AP6** (S4 adiado v20+/v21+): extrair `executar_skill8_atomica(picking_ids, constants_por_acao, dry_run)` do orchestrator (5 ops C+D sobre `account.move`) + atualizar §6 catálogo (Tabela 1 ganha Skill 8 ATÔMICA L2; Tabela 2 renomeia para `inventario_pipeline`).
5. **Expandir** `CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO` para FB=1 e CD=4 (mapear team_id, payment_term_id, picking_type_id + validar canary).
6. **Expandir** `L10N_BR_TIPO_PEDIDO_POR_ACAO` para todas direções via lookup MATRIZ_INTERCOMPANY.
7. Escrever folhas L3 pendentes (1.1.x só saída, 1.3 transferência completa, 2.3 transferir saldo entre códigos) sobre Skill 8 ATÔMICA L2.
8. **Sub-skill C5 V1 estendido**: cobrir G007 (standard_price=0) + l10n_br_tipo_produto (descobertos v21+ como bloqueios SEFAZ não-detectados).
9. **Resolver lote 'P-15/05'**: arg `forcar_lote_literal=True` no resolver — diferenciar proxy (sem-lote) vs literal.

**Estimativa**: 2-3 sessões. **Bloqueia**: galhos L3 1.1 + 1.3 (precisam Skill 8 ATÔMICA L2 extraída).

### Pendências (Skill 8 — pós-v18)

| Checkpoint | Status |
|------------|--------|
| C14 recovery `executar_pipeline_resume` | ✅ v18 |
| C15 SKILL.md `faturando-odoo` | ✅ v18 |
| C16 baseline pytest ≥520 | ✅ v18 (521) |
| C17 smokes dry-run | ✅ v18 |
| C18 folhas fluxos L3 1.2.1+1.2.2 + dispatch `executar_fluxo_l3_1_2_x` | ✅ v19+ |
| C18b folhas fluxos L3 1.1.x + 1.3 (SAÍDA + transferência completa) | ⬜ pendente v20+ (depende refator nomenclatura AP6) |
| C19 cross-refs final | ✅ v20+ |
| C20 canary REAL PROD | ✅ v20+ (1 invoice INDUSTRIALIZACAO_FB_LF — FLUXO_OK 1190ms) |
| C21 bulk REAL PROD | ⬜ pendente v21+ |
| C22 code-review final | ⬜ pendente v22+ |
| C23 commit + arquivar `09_executar_onda1_bulk.py` | ⬜ pendente v22+ |

### Onde NÃO mexer

- `app/recebimento/services/recebimento_lf_odoo_service.py` (4562 LOC validados PROD)
- `app/fretes/services/lancamento_odoo_service.py` (16 etapas validados PROD)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (SUPERADO ao final v22+; antes disso é referência viva)

### Histórico cronológico das sessões

> Sessões v13 → v18 migradas para `VALIDACAO_FINAL_SESSAO.md` em v18 Fase 0 (era ~666 linhas no ROADMAP HANDOFF). **Próximas sessões DEVEM append em VALIDACAO, NÃO neste ROADMAP** (regra D-V18-5 do CLAUDE.md §14).

---

**Mentalidade (não esquecer):** átomo versátil auto-seguro + `--dry-run`→`--confirmar` (CLAUDE.md §1); **`fluxos>>skills`** (caso novo = folha de fluxo, não skill nova); premissas resolvidas via `_utils` (não copiar); **NUNCA criar script ad-hoc** — capinar a skill; operação VIVA = preservar os ad-hoc restantes até cada átomo maturar (arquivar SUPERADO só após checklist C1-C10 da skill correspondente). **Skills nascem de demandas reais** — sessão 23/05 provou: 3 skills criadas a partir de 2 casos reais (104 ajustes negativos + auditoria pós-WRITE).

> **Como usar:** 1 assunto por vez, bottom-up. Antes de capinar QUALQUER átomo: `find scripts/inventario_2026_05 -name '*.py'` (operação VIVA — o nº muda) e **ler integral** os scripts-fonte (a situação no MAPA_SCRIPTS foi inferida, não lida — validar reabrindo). Preservar os ad-hoc até o átomo maturar; arquivar SUPERADO só após C9.

---

## CHECKLIST FIXO POR SKILL (instanciado em cada seção abaixo)

```
[ ] C1  Minerar scripts-fonte: LER INTEGRAL, extrair lógica + gotchas + edge cases (não confiar na situação inferida)
[ ] C2  Service base em app/odoo/estoque/ com gotchas codificados como INVARIANTE + testes pytest verdes
[ ] C3  Contrato de átomo definido (input · output · pré-cond · pós-cond · gotchas-invariante) — ver CLAUDE.md §3
[ ] C4  SKILL.md em .claude/skills/<skill>/ (contrato + receitas caso→args + gotchas + fronteira NÃO-USAR)
[ ] C5  scripts/<skill>/*.py: --dry-run (default seguro) + --confirmar; importam app.odoo.estoque
[ ] C6  VALIDAÇÃO POR REPRODUÇÃO (scripts ad-hoc = evals — ver seção abaixo): p/ CADA script-fonte CORRETO, skill --dry-run com os mesmos inputs → plano BATE (ground-truth: log auditoria/ se já rodou; ou script --dry-run se reexecutável)
[ ] C7  Registrar: gestor-estoque-odoo (skills:) + ROUTING_SKILLS.md + tool_skill_mapper.py + cross-refs
[ ] C8  Referência(s) de fluxo em app/odoo/estoque/fluxos/ que compõem o átomo (se já houver fluxo que o use)
[ ] C9  MOVER cada script VALIDADO → scripts/inventario_2026_05/_validados/<skill>/ (após confirmar 0 imports externos) + registrar linha em _validados/<skill>/VALIDACAO.md
[ ] C10 MAPA_SCRIPTS situação→SUPERADO + atualizar status neste ROADMAP
```

**Doc por skill (item "documentar após substituir"):** a própria `SKILL.md` é a doc de uso (CC+agente). Além dela: marcar MAPA_SCRIPTS (C10) e migrar o conteúdo de `docs/inventario-2026-05/consolidacao/manuais/<service>.md` para dentro da SKILL.md.

---

## ESTRATÉGIA DE VALIDAÇÃO — os scripts ad-hoc SÃO os evals

Não criamos evals sintéticos. Os ~105 scripts ad-hoc **corretos** são o **ground-truth**: um átomo só "atende" quando **reproduz** o que eles fazem. Aprovado → o script é **movido para `_validados/<skill>/`** (registro físico de progresso).

**Protocolo por script-fonte:**
1. **Triar (no C1)** — classificar cada script-fonte:
   - `EVAL` = correto + reproduzível → vira caso de validação;
   - `COM-BUG` = bug/dead-code conhecido (ex: `ajuste_estoque_lf_pasta17` docstring stale) → a skill faz o **CERTO**; divergência é **melhoria**, não falha (anotar);
   - `JÁ-MORTO` = discovery/pontual → não é eval, arquiva em `_historico/` (não em `_validados/`).
2. **Reproduzir em `--dry-run`:**
   - script **reexecutável** (idempotente, tem `--dry-run`): rodar `script --dry-run` **E** `skill --dry-run` com os mesmos inputs → comparar o **plano** (produto/lote/local/qtd/sinal);
   - script **já executado** (input consumido): comparar `skill --dry-run` vs `auditoria/log_*.json` (o que de fato rodou).
3. **PASSOU** (plano bate) → `git mv` do script para `scripts/inventario_2026_05/_validados/<skill>/` + linha em `_validados/<skill>/VALIDACAO.md` (`script · inputs · ground-truth · resultado · data`).
4. **NÃO bateu** → investigar antes de mover: bug no átomo (corrigir) · bug no script (anotar, skill mantém o certo) · semântica diferente (ajustar args/`--semantica`).

**Pastas (distintas):** `_validados/<skill>/` = comprovadamente coberto pela skill (com evidência) · `_historico/` = JÁ-MORTO sem reuso · `_ad-hoc/` = ainda ativo, não capinado. Rastreabilidade: "quais ad-hoc o átomo X já cobre" = `ls _validados/<skill>/`.

> ⚠️ Mover só após **0 imports externos** ao script (C9) — a maioria é standalone (executável), mas conferir. Operação VIVA: se um script validado ainda for necessário para rodar, a skill (que o reproduz) é quem roda agora.

---

## ONDA 0 — pré-requisitos (desbloqueiam tudo)

```
[ ] 0.1  Materializar app/odoo/estoque/ (scripts/ orchestrators/ _utils.py __init__.py) + shims em services/ (PLANO_MIGRACAO §1/§7)
[ ] 0.2  Esqueleto subagente .claude/agents/gestor-estoque-odoo.md (prompt = árvore de DECISÃO §5; WRITE; diferenciar de gestor-estoque-producao)
[ ] 0.3  Esqueleto app/odoo/estoque/fluxos/ + README com a convenção de folha (CLAUDE.md §5.1)
[X] 0.4  (bloqueia faturamento) FECHAR G019/G020 — validar() engole erro / marca done falso ✅ FECHADO 2026-05-24 v3 (fix em `app/odoo/estoque/scripts/picking.py`; 8 testes pytest validando invariante; docs G019/G020 atualizados PROPOSTO→IMPLEMENTADO)
```

---

## ORDEM DE EXECUÇÃO (bottom-up)

| Onda | Skill | Por quê nesta ordem |
|------|-------|---------------------|
| 1 | `ajustando-quant-odoo` ✅ MATURADA | **PILOTO** validado em produção 2026-05-23 (100 ajustes em 55s) |
| 2 | `transferindo-interno-odoo` 🟡 (mín viável + MODO C PROD + FIX D-OPS-5 v14b) | **NOVA 2026-05-24 v2 / MODO C v4 / FIX D-OPS-5 v14b** — 61 pytest verdes (52 + 9 D-OPS-5), 3 modos atomicos + helper `distribuir_para_indisponivel` PROD-validado 158 cods FB; **v14b aceita produtos `tracking='none'` via `aceita_tracking_none=True` default + valida `product.tracking` quando `lot_id_origem=None`**; canary PROD cod 208000043 sem lote 1 un + reversão completa |
| 3 | `operando-reservas-odoo` 🟡 (mín viável) · `operando-mo-odoo` 🟡 (mín viável NOVA 2026-05-24 v5 — 29 pytest, guard G-MO-01 furo contábil, idempotência action_cancel) · `operando-picking-odoo` 🟡 (mín viável NOVA 2026-05-24 v3) | cancelamentos/limpeza (gaps); skill 3 ANTECIPADA por demanda real 2026-05-23; skill 5 capina StockPickingService + atomo NOVO `devolver` (idempotente); FECHA invariante G019/G020 (pre-req ONDA 0.4); skill 4 criada do zero (sem service legado) |
| 4 | `planejando-pre-etapa-odoo` 🟡 (mín viável NOVA 2026-05-24 v6 — 19 pytest verdes, 4 modos planejar/propor/listar/aprovar; capina 03b+04b; 09b executor mantém VIVO como C3 macro pendente) | planner D007 (READ Odoo + WRITE banco local); isolado |
| 5 | `escriturando-odoo` ⬜ | entrada IC + DFe; depende de contrato estável de transfer |
| 6 | `faturando-odoo` 🟡 PLANEJADA + 3 MINERAÇÕES + SUB-SKILL C5 LIVE | **ÚLTIMO** — macro perigoso (SEFAZ); ONDA 0.4 ✅ fechada 2026-05-24 v3 + sub-skill C5 ✅ LIVE 2026-05-25 v14b; 5 de 24 checkpoints concluidos; teste real 6 cods PROD v14a-ops; proxima v15a (3 atomos Skill 5 inter-company) |
| ANCILLARY | `consultando-quant-odoo` 🟡 | READ-only AO VIVO; nasceu sob demanda (auditoria pós-WRITE) — não bloqueia outras |
| SUB-SKILL | `auditando-cadastro-fiscal-odoo` 🟡 (V1 inventario LIVE 2026-05-25 v14b) | PRE-FLIGHT delegado pela Skill 8 v15+; cobre G017+G018+G035+G014+D-OPS-2/3; 14 pytest + smoke PROD 6 cods em 987ms; perfis multiplos previstos (V2 venda-cliente futuro) |

---

## SKILL 1 — `ajustando-quant-odoo`  (PILOTO)  ✅ MATURADA
- **Objeto:** stock.quant | **Camada:** C1 | **Service:** `StockQuantAdjustmentService` ✅ (existe + manual + 22 testes; orquestrador `ajuste_inventario.py` existe)
- **Scripts-fonte (MAPA_SCRIPTS):** SUPERADOS já cobertos → 11, 12, 13, 14_v2, criar_saldo. AO-CAPINAR (composições) → limpar_quants_ghost, zerar_negativos, corrigir_reserved_negativo, fat_lf_03_prestage, fat_lf_06_consolidar_validos.
- **Gotchas-invariante:** G028 (consolidar_move_lines), G029 (payment_provider), action_apply_inventory infla quant NEGATIVO (usar picking p/ destino negativo), `=`→`in` em lot.name (G002). **GUARD delta_esperado** (anti-bug CICLAMATO 2026-05-24): valida `|ajuste_aplicado - delta_esperado| <= tolerancia_delta`; modo `--corrigir-para-esperado` auto-aplica delta_esperado.
- **Checkpoints:** C1 🟡 · C2 ✅ · C3 ✅ · C4 ✅ · C5 ✅ · **C6 ✅** (dry-run 3 casos vs ground-truth + WRITE REAL 100 linhas em 2026-05-23: **84 EXECUTADO + 1 NOOP + 15 bloqueio anti-reservado correto**) · C7 ✅ · C8 ✅ · C9 ✅ · C10 ✅
  - **Status global da skill 1: ✅ MATURADA** (2026-05-23 — caso real de 104 ajustes negativos do usuário invocou o fluxo 2.1 ponta-a-ponta; HOST agente compôs `StockQuantAdjustmentService.ajustar_quant` em loop in-process; 4 políticas de premissa aplicadas: MIGRA→fallback `qualquer lote único`→`zerar quant insuficiente`→`PEPS multi-quant`; logs em [`auditoria/log_2.1_*.json`](../../scripts/inventario_2026_05/auditoria/) e evidência completa em [`_validados/ajustando-quant-odoo/VALIDACAO.md`](../../scripts/inventario_2026_05/_validados/ajustando-quant-odoo/VALIDACAO.md)).
  - 2026-05-22: shim provado — 11 consumidores intactos. SKILL.md (template) + ajustar_quant.py (ajuste pontual de 1 quant, dry-run default/--confirmar) criados; skill ligada ao gestor-estoque-odoo.
  - 2026-05-23: C6 dry-run rodado contra Odoo PROD com 3 casos reais dos logs `frete_sistema/scripts/inventario_2026_05/auditoria/`: (1) `11_ajuste_cd` cod=4310152/lote=119338/CD/Δ=-1.1e-05; (2) `12_ajuste_pos_cd` cod=205460830/lote=345232-25/CD/Δ=+2e-05; (3) `criar_saldo_positivo_lf` cod=104000127/lote=0730/682153-F3/LF/Δ=+37.5 --criar-se-faltar. **Premissas (product_id, company_id, location_id, lot_id, quant_id) bateram 100%**. Operação viva alterou `qty_antes` nos casos 1 e 3 (quant 207125 sumiu pós-zeragem; quant 256433 já tinha 37.5 do run de 20/05) — invariantes do átomo (`FALHA_QUANT_VAZIO`, regra `--criar-se-faltar` ignora lote existente) protegem corretamente. **Worktree não tinha `.env`** — solução: `set -a; . <(grep -E '^ODOO_' /home/.../frete_sistema/.env); set +a` (carrega só ODOO_*, sem DATABASE_URL para não tocar PROD).
  - 2026-05-23: C7 ✅ — `gestor-estoque-odoo` adicionado em [CLAUDE.md §SUBAGENTES](../../../CLAUDE.md); skill `ajustando-quant-odoo` adicionada em [ROUTING_SKILLS.md](../../../.claude/references/ROUTING_SKILLS.md) (Passo 1 row, Passo 3 árvore nodo 6, desambiguação `gestor-estoque-odoo vs gestor-estoque-producao` + `ajustando-quant-odoo vs transferindo-interno-odoo`, Skills Odoo 9→10) + em [tool_skill_mapper.py](../../../app/agente/services/tool_skill_mapper.py) (`Estoque Odoo (Write)`/`Odoo`). C8 ✅ — folha [fluxos/2.1-ajuste-saldo-por-planilha.md](fluxos/2.1-ajuste-saldo-por-planilha.md) criada cobrindo schema heterogêneo dos 5 scripts; README da árvore marcado ✅. C9 ✅ — 5 scripts (11, 12, 13, 14_v2, criar_saldo_lf) movidos via `git mv` para [`scripts/inventario_2026_05/_validados/ajustando-quant-odoo/`](../../../scripts/inventario_2026_05/_validados/ajustando-quant-odoo/VALIDACAO.md); 0 imports externos confirmado; sys.path interno corrigido `parents[2]→parents[4]` em cada um (museum vivo — ainda executáveis). C10 ✅ — [MAPA_SCRIPTS.md](../../../docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md) §"scripts/quant.py" linkado para `_validados/` e VALIDACAO.md.

## SKILL 2 — `transferindo-interno-odoo`  🟡 (mín viável + MODO C PROD + 61 pytest verdes + FIX D-OPS-5 v14b)
- **Objeto:** transferência interna intra-empresa | **Camada:** C2 | **Service:** [`app/odoo/estoque/scripts/transfer.py`](scripts/transfer.py) (StockInternalTransferService — API v1 preservada + API v2 que delega a `ajustar_quant` 2x + helpers MIGRAÇÃO + `transferir_entre_locations`)
- **Scripts-fonte:** 10 (SUPERADO 2026-05-24), padronizar_migracao (SUPERADO 2026-05-24 com limitação 2-grafias), 13_transferencia_migracao_fb, 15_transferencia_para_migracao, 15r, 15_transferir_preprod, 17_transferir_preprod_lf, substituir_lote_205030410, transferir_lote, transferir_local_pasta22, recuperar_aumentos_falhos, mover_migracao_para_indisponivel, ajuste_fb_cd_indisponivel, transferir_indisp_para_estoque_p15_cd, relotar_migracao_para_lotes_fb, transferir_fluxo_c (COM-BUG G-TRANSFER-01), executar_fluxo_b_vivas (COM-BUG), consolidar_lote_104000015_sal_fb.
- **Semânticas (explícitas via arg, nunca inferir):** D010 sinal diff_qtd · D012 delta · D013 De-Para+wildcard (vivem nos orquestradores externos; a skill cobre o ÁTOMO).
- **Gotchas-invariante codificados (11):** G021 (lot_id empresa errada — filtro company_id em TODA busca de lote), G022 (2 lotes MIGRACAO/produto — wildcard 3 grafias + maior saldo na loc), G027 (reserved_quantity stale — `--resetar-reserva-origem` opcional), G028 (consolidar_move_lines — herdado), G002 (lot.name `=` instável — herdado), G_proxy_vazio (P-15/05 = literal + sem lote), G-TRANSFER-01 (criar_se_nao_existe retorna tuple), action_apply_inventory infla quant negativo (herdado), delta_esperado propagado a CADA passo (regra inviolável 11), G_clamp_arred (TOL=0.001), **D-OPS-5 v14b (NOVO 2026-05-25): `aceita_tracking_none=True` default + valida `product.tracking` quando `lot_id_origem=None` — raise se != 'none' (anomalia quant orfao sem lote em produto rastreavel); helper `distribuir_para_indisponivel` propaga o parametro**.
- **Átomos implementados (4) + 1 helper alto-nivel + fix D-OPS-5 v14b:** `transferir_entre_lotes` (v1 preservada — 12 testes originais), `transferir_entre_lotes_v2` (v2 nova, delega `ajustar_quant`×2 com `delta_esperado` propagado), `transferir_entre_locations` (mesmo lote, 2 locs), `transferir_quantidade_para_lote_v2` (wrapper v2 com criar destino), `transferir_para_indisponivel` (Modo C atomico — relaxado em v14b para `lot_id_origem: Optional[int]` + campo novo `tracking_origem` no retorno), `distribuir_para_indisponivel` (helper alto-nivel — v10 greedy MIGRACAO_FIRST_FIFO + v12 fallback Modo B + v14b propaga `aceita_tracking_none`).
- **Helpers (4):** `is_migracao` (3 variantes), `_lotes_migracao_ids` (G021), `_melhor_lote_migracao_na_loc` (G022), `resolver_lote_origem/destino` (públicos).
- **Limitações conhecidas (genealogia — memoria dev aposentada 2026-06-11):** `transferir_quantidade_para_lote_v2` com destino SEM lote levanta `ValueError` (usar `transferir_entre_locations` ou `ajustar_quant`); `_melhor_lote_migracao_na_loc` com zero-saldo faz fallback `lids[0]` (não-determinístico — Odoo search order, sem teste explícito).
- **Checkpoints:** C1 ✅ (18 scripts lidos integral — 9 por mim + 7 por subagente Explore + 2 do main) · C2 ✅ (service `transfer.py` movido + estendido; 33 testes pytest verdes) · C3 ✅ (contrato em SKILL.md) · C4 ✅ ([`SKILL.md`](../../.claude/skills/transferindo-interno-odoo/SKILL.md)) · C5 ✅ ([`transferir.py`](../../.claude/skills/transferindo-interno-odoo/scripts/transferir.py)) · **C6 ✅** (3 casos dry-run PROD: lote→lote OK; padronizar OK com limitação; loc→loc OK detalhado) · C7 ✅ (subagente + ROUTING_SKILLS + tool_skill_mapper `Estoque Odoo (Write)` + CLAUDE.md raiz) · C8 ✅ ([fluxo 2.2](fluxos/2.2-realocar-saldo.md) com 8 sub-casos) · C9 ✅ (2 scripts movidos: 10_emergenciais + padronizar_migracao; sys.path corrigido parents[2]→parents[4]; outros 16+ permanecem VIVOS — operação viva) · C10 ✅ (MAPA_SCRIPTS + este ROADMAP atualizados)
- **Status global da skill 2: 🟡 mín viável + FIX D-OPS-5 LIVE** (2026-05-25 v14b — átomo composto pronto + helper `distribuir_para_indisponivel` PROD-validado em 158 cods FB; FIX D-OPS-5 v14b aceita produtos `tracking='none'`; **9 pytest novos** v14b + canary PROD cod 208000043 sem lote 1 un + reversão completa). [VALIDACAO.md](../../scripts/inventario_2026_05/_validados/transferindo-interno-odoo/VALIDACAO.md) + memoria `[[skill2_distribuir_indisp_pattern]]` (atualizada v14b).

## SKILL 3 — `operando-reservas-odoo`  🟡 (mínimo viável + write real validado)
- **Objeto:** stock.move.line + stock.picking + stock.quant (residual) | **Camada:** C1/C2 | **Service:** [`reserva.py`](scripts/reserva.py) (StockReservaService — 3 átomos)
- **Scripts-fonte (MAPA_SCRIPTS):** SUPERADOS → remover_reservas_saida, cancelar_reservas_migracao, limpar_reservas_fantasma (movidos para `_validados/operando-reservas-odoo/` em 2026-05-23).
- **Gotchas-invariante codificados (5):** G024 (`reserved_uom_qty` inexistente Odoo 16/17), G025 (Odoo CIEL IT: `stock.move._action_cancel` é PRIVADO via XML-RPC), G026 (MO `to_close/done` tem `picked=True` — não mexer), G027 (`reserved_quantity` interno SEMPRE vem de saída — zerar residual stale é seguro), G028 (batch 50 com fallback individual).
- **Átomos implementados (3):** `cancelar_moves_orfaos(picking_id, ml_ids, moves_writes)` (cirurgia), `cancelar_picking_inteiro(picking_id)` (action_cancel cascade), `zerar_reserved_residual(quant_ids)` (cleanup pós-unlink — descoberta 2026-05-23).
- **Átomos previstos:** `unreserve_picking`, `unreserve_mo(reassign=)`, `find_orphan_mls` — implementar conforme demanda.
- **Checkpoints:** C1 ✅ (4 scripts-fonte lidos integral + probes Odoo 17) · C2 ✅ ([`reserva.py`](scripts/reserva.py)) · C3 ✅ (contrato em SKILL.md) · C4 ✅ (`SKILL.md`) · C5 ✅ ([`operar_reserva.py`](../../.claude/skills/operando-reservas-odoo/scripts/operar_reserva.py)) · **C6 ✅** (write real 2026-05-23 — 6 pickings/15 quants em 3,6s + 15 quants `zerar_reserved_residual` em 62ms) · C7 ✅ (subagente + ROUTING_SKILLS + tool_skill_mapper) · C8 ✅ ([fluxo 2.4](fluxos/2.4-cancelar-reserva-orfa.md)) · C9 ✅ (3 scripts movidos `parents[2]→parents[4]`) · C10 ✅ (MAPA_SCRIPTS seção `scripts/reserva.py`)
- **Status global da skill 3: 🟡 — mínimo viável maturado, demais átomos previstos** (2026-05-23 — caso real "15 MLs órfãs em 6 pickings pós-`--resetar-reserva`" resolvido ponta-a-ponta; gotcha descoberto: `--resetar-reserva` + unlink ML gera `reserved` negativo, exige `zerar_reserved_residual` após; documentado em SKILL.md e [`VALIDACAO.md`](../../scripts/inventario_2026_05/_validados/operando-reservas-odoo/VALIDACAO.md)).

## SKILL 4 — `operando-mo-odoo`  🟡 (V7 cancelar+concluir · 57 pytest verdes)
- **Objeto:** mrp.production | **Camada:** C2 | **Service:** [`app/odoo/estoque/scripts/mo.py`](scripts/mo.py) (StockMOService — criado do zero 2026-05-24 v5; shim preventivo em `services/stock_mo_service.py`)
- **Scripts-fonte:** cancelar_mos (SUPERADO 2026-05-24 v5), 14_cancelar_mos_antigas_fb (SUPERADO 2026-05-24 v5).
- **Gotchas-invariante codificados (4):** G-MO-01 (consumo>0=furo contábil — bloqueia cancelamento default; CLI V1 NÃO expõe forcar_consumo; operador deve usar mrp.unbuild via fluxo cross-skill), G-MO-02 (manual_consumption não reserva via action_assign — NÃO relevante para cancelar, relevante p/ criar/alterar não cobertos V1), G-MO-03 (componente em local errado — não relevante para cancelar), G-MO-04 (picked=True em to_close/done herdado de Skill 2.4 G026 — action_cancel é seguro). G019-like (re-le state pós action_cancel; FALHA_STATE_INESPERADO se state != cancel).
- **Átomos implementados (3 WRITE):** `concluir_mo(mo_id, nome_lote, motivo, dry_run)` V7 2026-06-12 — Produzir Tudo + Validar via button_mark_done; guards G-MO-05 (picked=True anti-produção-fantasma, ex-G-ENT-10 do piloto industrialização validado PROD 2026-06-01) + G-MO-06 (raw sem ML pós-assign bloqueia); single-only (escrita contábil irreversível); context multi-company derivado da MO (lição D-V30-1); demanda real MO LF/MO/03556 + decisão Rafael 2026-06-12 ("necessidade, não roadmap"); canary `--confirmar` PENDENTE demanda natural (dry-run PROD validado: MOs 20606 NOOP + 19762 plano); `cancelar_mo(mo_id, motivo, forcar_consumo, consumo_total, dry_run)` — wrapper sobre `mrp.production.action_cancel` + guard G-MO-01 + G019-like re-le state + idempotência state=cancel = NOOP; `cancelar_mos_em_massa(criterio, max_n, motivo, dry_run)` — composição com filtros (create_de/ate, states, empresas, consumo) + medir_consumo batch (perf) + FIFO por create_date.
- **Helper:** `medir_consumo_mo(mo_ids)` — soma `stock.move.quantity` (state != 'cancel') por raw_material_production_id (chunks 200, TOL=0.0001).
- **Átomos previstos (sem demanda):** `criar_mo` (sem demanda real isolada — pipeline cria via Odoo); `alterar_mo` (caso real existe — ver [[mo_componente_local_consumo]] — mas é fluxo cross-skill Skill 2 + write stock.move, NÃO átomo). `mrp_unbuild` (procedimento manual documentado em [[reaproveitar-semiacabado-orfao-mo-cancelada]] §3; skill futura se padrão repetir).
- **Checkpoints:** C1 ✅ (2 scripts-fonte lidos integral + investigação AO VIVO via `/tmp/investigar_mos_skill4.py`: 10.000 MOs FB / 17 CD / 3367 LF; estrutura mrp.production validada; idempotência action_cancel confirmada em FB/OP/BALDE/00009 id=4192) · C2 ✅ ([`scripts/mo.py`](scripts/mo.py) novo; **29 testes pytest verdes** cobrindo todos os cenários — caminho feliz, NOOP idempotente, guard G-MO-01 default + bypass, state='done', state inesperado, exceção, dry-run, helpers, batch com filtros/limite/FIFO) · C3 ✅ (contrato 1 átomo único + composição em SKILL.md) · C4 ✅ ([`SKILL.md`](../../.claude/skills/operando-mo-odoo/SKILL.md)) · C5 ✅ ([`operar_mo.py`](../../.claude/skills/operando-mo-odoo/scripts/operar_mo.py) — CLI single OU batch, --dry-run default, exit codes 0/1/2/4) · **C6 ✅** (4 casos dry-run PROD 2026-05-24 v5: NOOP idempotente, DRY_RUN_OK sem consumo, FALHA_FURO_CONTABIL bloqueia consumo=1410.05, batch FB ate 2025-06 com filtro consumo zero; log em `/tmp/log_skill4_C6_validacao_dry_run.json`) · C7 ✅ (subagente `gestor-estoque-odoo` adicionou skill + galho 3.1 com [folha 3.1]; ROUTING_SKILLS 47 invocaveis + 15 Skills Odoo + triggers MO; tool_skill_mapper `'operando-mo-odoo': 'Estoque Odoo (Write)'`; CLAUDE.md raiz + app/odoo/CLAUDE.md atualizados) · C8 ✅ ([fluxo 3.1](fluxos/3.1-cancelar-mo.md) com 3 sub-casos a/b/c; 3.1.c DELEGADO para mrp.unbuild cross-skill) · C9 ✅ (2 scripts SUPERADOS em `_validados/operando-mo-odoo/`: `cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` + VALIDACAO.md; sys.path corrigido parents[2]→parents[4]; museum vivo validado via import) · C10 ✅ (MAPA_SCRIPTS atualizado seção `scripts/mo.py` + README fluxos atualizado).
- **Status global da skill 4: 🟡 V7** (cancelar maturado v6 — 342 MOs PROD 2026-05-27; concluir V7 2026-06-12 com dry-run PROD validado e canary `--confirmar` pendente demanda natural — primeira execução real exige confirmação explícita + verificação SVL no Odoo, ver [fluxo 3.2](fluxos/3.2-concluir-mo.md)).
- **Pattern "criar skill WRITE do zero" (genealogia v5 — memoria dev aposentada 2026-06-11):** quando NÃO há service legado em `services/`: (1) pattern Skill 1 (do zero) > Skill 5 (capinar) — criar shim PREVENTIVO em `services/`, escrever testes do zero, confirmar 0 consumers via grep; (2) investigação AO VIVO antes do C1 final (volumes reais, idempotências não documentadas, semântica de campos); (3) guard de segurança como invariante INVIOLÁVEL no service com status canônico (CLI não expõe bypass); (4) re-ler state pós-ação (G019-like é geral, não só pickings); (5) status `cancel_deleted` quando `_ler` retorna None pós-ação (cascade delete customizado Odoo) → tratar como EXECUTADO + warning; (6) code-review paralelo CODE+DOCS pega bugs ortogonais.

## SKILL 5 — `operando-picking-odoo`  🟡 (mín viável ESTENDIDA v15a + 61 pytest verdes + 6 dry-run PROD)
- **Objeto:** stock.picking | **Camada:** C2 | **Service:** [`app/odoo/estoque/scripts/picking.py`](scripts/picking.py) (StockPickingService — capinado de `services/` em 2026-05-24 v3, shim preservado)
- **Scripts-fonte:** 16_cancelar_pickings_fantasmas (SUPERADO 2026-05-24 v3); pipeline-only e cross-skill permanecem VIVOS (executar_fluxo_b_vivas, teste_210030325_lf, fat_lf_05_executar_clean, 09_executar_onda1_bulk, fat_lf_cleanup, substituir_lote_205030410_fb).
- **Gotchas-invariante codificados (4):** G019 (validar() re-le state pós-button_validate; raise se != 'done'; trata marshal None), G020 (liberar_faturamento valida pre-cond state=done — usado por Skill 8 pipeline, NÃO exposto na CLI da Skill 5), G023 (consolidar_move_lines opcional em validar(linhas_esperadas=)), G011 (preencher_qty_done existe mas é PRÉ-REQUISITO de caller — pipeline preenche antes).
- **Átomos implementados (3):** `cancelar(picking_id, motivo)` — wrapper sobre `action_cancel`; `validar(picking_id, linhas_esperadas=None)` — `button_validate` + G019 invariante + G023 opcional; `devolver(picking_id)` — NOVO (wizard `stock.return.picking` + `create_returns` + valida; idempotente via `origin ilike "Devolução de NAME"`).
- **Átomos previstos (sem demanda):** `alterar_lote_no_picking` (caso `substituir_lote_205030410` é fluxo cross-skill, não átomo); `criar_picking_interno` (sem demanda ad-hoc isolada — pipeline cria via `svc.criar_transferencia` existente).
- **Checkpoints:** C1 ✅ (4 scripts-fonte minerados integral: 16_cancelar_pickings_fantasmas, fat_lf_cleanup, substituir_lote_205030410, picking_service.py existente; + 4 docs gotchas G011/G019/G020/G023) · C2 ✅ ([`app/odoo/estoque/scripts/picking.py`](scripts/picking.py) capinado + método novo `devolver`; **42 testes pytest verdes** — 19 originais + 16 novos cobrindo G023/ajustar_qty_done/validar-com-linhas + 7 cobrindo `devolver`) · C3 ✅ (contrato 3 átomos em SKILL.md) · C4 ✅ ([`SKILL.md`](../../.claude/skills/operando-picking-odoo/SKILL.md)) · C5 ✅ ([`operar_picking.py`](../../.claude/skills/operando-picking-odoo/scripts/operar_picking.py) — 3 modos `--modo cancelar/validar/devolver`, `--dry-run` default, exit codes 0/1/2/4) · **C6 ✅** (6 casos dry-run PROD 2026-05-24 v3: cancelar/assigned ✅, validar/assigned ✅, devolver/done ✅, cancelar/done=FALHA_STATE_DONE ✅, cancelar/cancel=NOOP ✅, devolver/assigned=FALHA_STATE_NAO_DONE ✅; 100% bate) · C7 ✅ (subagente `gestor-estoque-odoo` adicionou skill + árvore 2.5; ROUTING_SKILLS 46 invocaveis + 14 Skills Odoo; tool_skill_mapper `'operando-picking-odoo': 'Estoque Odoo (Write)'`) · C8 ✅ ([fluxo 2.5](fluxos/2.5-cancelar-validar-devolver-picking.md) com 3 sub-casos a/b/c) · C9 ✅ (1 script SUPERADO em `_validados/operando-picking-odoo/`: `16_cancelar_pickings_fantasmas.py` + VALIDACAO.md; sys.path corrigido parents[2]→parents[4]) · C10 ✅ (MAPA_SCRIPTS atualizado).
- **Status global da skill 5: 🟡 mín viável ESTENDIDA em v15a** (2026-05-25 v15a — 6 átomos LIVE: cancelar/validar/devolver + `criar_picking_inter_company` (D-OPS-3 fix) + `validar_picking_inter_company` (F5b completo + G018) + `criar_picking_entrada_destino_manual` (ETAPA F G023+idempotencia) + helper `aplicar_peso_volumes_fallback`; **61 pytest verdes** (42 + 19 novos v15a); constants ETAPA F centralizadas em `picking_types.py`; smoke PROD validou D-OPS-3 detection em 6 cods v14a-ops; FECHOU ONDA 0.4 ✅ + agora **destrava orchestrator base Skill 8 v15b** que invocara os 3 atomos em F5a/F5b/ETAPA F).

## SKILL 6 — `planejando-pre-etapa-odoo`  🟡 (mín viável COMPLETA — 5 modos + 42 pytest verdes + 6 smokes CLI)
- **Objeto:** planner D007 (READ Odoo + WRITE banco local) | **Camada:** C2 | **Service:** [`app/odoo/estoque/scripts/pre_etapa.py`](scripts/pre_etapa.py) (PreEtapaEstoqueService + 4 helpers top-level + 4 constantes; capinado 2026-05-24 v6)
- **Scripts-fonte:** 03b_planejar_pre_etapa_cd (SUPERADO 2026-05-24 v6 — modo planejar da skill), 04b_propor_pre_etapa_cd (SUPERADO 2026-05-24 v6 — modos propor/listar-onda/aprovar-onda da skill), 09b_executar_pre_etapa (VIVO — C3 macro pendente capinagem para `orchestrators/pre_etapa_executor.py`), 04_propor_ajustes (outras ondas — VIVO operação viva).
- **Gotchas-invariante codificados (10):** G-PRE-01 D007 restricao temporal FB pos-etapa (caller filtra), G-PRE-02 FIFO determinístico por quant_id, G-PRE-03 lote inv sem nome → 'P-15/05', G-PRE-04 MIGRAÇÃO consolidador NEG vs alvo, G-PRE-05 outliers cod[0] != 1-4 skipados (retornados em `outliers_skipados`), G-PRE-06 custo médio ponderado D004 (value/quantity), G-PRE-07 hash sha256 sensível a campos críticos (anti-replay), G-PRE-08 idempotência propor (DELETE+INSERT gera novos IDs → hash muda), G-PRE-09 Onda 2 depende de Onda 5 (lotes alvo criados pela Onda 5), G-PRE-10 executor 09b NÃO é átomo da Skill 6 (C3 macro).
- **Átomos implementados (4 modos CLI):** `planejar` (READ Odoo + grava JSON+Excel — chama `planejar_pre_etapa_batch_company`), `propor` (WRITE banco local DELETE+INSERT — chama `propor_ajustes_pre_etapa`), `listar-onda` (READ + hash sha256 — chama `listar_onda_pre_etapa`), `aprovar-onda` (WRITE banco local com hash check — chama `aprovar_onda_pre_etapa`).
- **Helpers (3):** `enriquecer_quants_para_planejar` (mockado nos testes), `gerar_excel_plano_pre_etapa` (lazy import openpyxl), `_calcular_hash_onda` (sha256 ordenado por id).
- **Checkpoints:** C1 ✅ (3 scripts-fonte + service + 13 testes lidos integral; **v9**: 09b remineração + 4 services extras) · C2 ✅ ([`scripts/pre_etapa.py`](scripts/pre_etapa.py) capinado + estendido; **v9**: novo orchestrator [`orchestrators/pre_etapa_executor.py`](orchestrators/pre_etapa_executor.py) compondo Skills 1+2; **42 testes pytest verdes** — 21 service + 21 orchestrator) · C3 ✅ (contrato **5 modos** em SKILL.md — v9 adicionou `executar-onda`) · C4 ✅ ([`SKILL.md`](../../.claude/skills/planejando-pre-etapa-odoo/SKILL.md)) · C5 ✅ ([`planejar_pre_etapa.py`](../../.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py) — CLI **5 modos**, --dry-run default em writes, exit codes 0/1/2/4) · **C6 ✅** (v6 3 smokes + **v9 3 smokes executar-onda**: company_id invalido argparse exit 2, ciclo inexistente FALHA_NENHUM_APROVADO exit 1, dry-run real INVENTARIO_2026_05 cid=4 DRY_RUN_OK_EXECUTADO exit 4 encontrou 1 APROVADO real id=163696 e dispatch correto via Skill 2 v2; log `/tmp/log_skill6_C6_validacao_executar_onda.json`) · C7 ✅ (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md módulo) · C8 ✅ ([fluxo 4.1](fluxos/4.1-pre-etapa-cd-d007.md) com **5 sub-casos a/b/c/d/e** — v9 adicionou sub-caso 4.1.e executar Onda) · C9 ✅ (**3 scripts SUPERADOS** em `_validados/planejando-pre-etapa-odoo/`: 03b + 04b + **09b v9** + VALIDACAO.md) · C10 ✅ (MAPA_SCRIPTS + este ROADMAP atualizados).
- **Status global da skill 6: 🟡 mín viável COMPLETA (5 modos)** (2026-05-25 v9 — ciclo planejar→propor→listar→aprovar→**executar** fechado; 0 execuções `--confirmar` real nesta sessão em executar-onda; pattern já validado em PROD em sessões anteriores via script 09b legacy). [VALIDACAO.md](../../scripts/inventario_2026_05/_validados/planejando-pre-etapa-odoo/VALIDACAO.md).

## SKILL 7 — `escriturando-odoo`  (SÓ ENTRADA)  ⬜
- **Objeto:** entrada DFe/NF → in_invoice | **Camada:** C3 (macro + etapas E→F) | **Service:** pipeline (etapa entrada) + `escriturar_dfe_lf.py` (assunto NOVO)
- **Scripts-fonte:** entrada_fb_piloto (etapas 0-18), escriturar_dfe_lf (Fluxo A, NÃO reusa RecebimentoLf), fat_lf_resume_entrada.sh (resiliente a hang robô).
- **Gotchas-invariante:** G034 (CFOP entrada 1xxx ≠ saída 5xxx), G023, quirk DFe status 04, action_gerar_po_dfe usa company do USUÁRIO (forçar allowed_company_ids), tipo='serv-industrializacao' p/ CFOP 1901.
- **Fronteira:** recebimento de COMPRAS → gestor-recebimento; CTe → fretes; pallet → pallet.
- **Checkpoints:** C1–C10 ⬜

## SKILL 8 — `faturando-odoo`  (SÓ SAÍDA — ÚLTIMO)  🟡 PLANEJADA + 3 MINERAÇÕES + TESTE REAL PROD + SUB-SKILL C5 LIVE (v14b) + 3 ÁTOMOS INTER-COMPANY LIVE (v15a)
- **Objeto:** NF saída→robô CIEL IT→SEFAZ | **Camada:** C3 (macro + etapas A→F) | **Service:** `InventarioPipelineService` 🟡 (macro 1346 LOC, ~20 gotchas, minerado v13 §7.2 D1-D9 do `PLANEJAMENTO_SKILL8_FATURANDO.md`)
- **PRÉ-REQUISITO:** ONDA 0.4 ✅ FECHADA (G019/G020 codificados no service de Skill 5 — 2026-05-24 v3) + **sub-skill C5 LIVE** ✅ (v14b — pre-flight delegado).
- **Documento vivo MACRO:** [`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`](PLANEJAMENTO_SKILL8_FATURANDO.md) (~1450 LOC, 14 secoes + §7.5 5 dificuldades operacionais D-OPS-1..5 do teste real v14a-ops). **Regra inviolavel 0**: LER inteiro ANTES de tocar codigo Skill 8.
- **Scripts-fonte minerados:** 09_executar_onda1_bulk (A-F — minerado §7.3 D10-D18 v14a), 09c_executar_onda2_fb_cd (transfer_only 19-37), fat_lf_02_carregar (TIPO→ação), fat_lf_04_executar (driver B-F), fat_lf_05_executar_clean (G028 reserva multi-lote), fat_lf_cleanup (return+cancel+reset), fat_lf_resume.sh (loop B→D SSL-resiliente), teste_210030325 (→ exemplo no fluxo). **Service externo READ-only:** `RecebimentoLfOdooService` (4562 LOC, 37 etapas em 7 fases — minerado §7.4 G-RECLF-1..11 v14a-fix — **NAO MEXER**).
- **Gotchas-invariante:** G004, G011, G016 (SSL), G019/G020 ✅ (fechados em Skill 5 v3), quarteto fiscal G035/G017/G007/G018 ✅ (pré-flight cobrado pela sub-skill C5 v14b), G028, G023, **D-OPS-1..5 v14a-ops** (CICLO hardcoded → arg orchestrator; D-OPS-2 duplicação pipeline → C5; D-OPS-3 tracking='none' bug L965 → fix no atomo Skill 5 v15a; D-OPS-4 picking automatico pos-RecLF → pos-hook ETAPA E v17; D-OPS-5 Skill 2 mesmo padrao → ✅ FIXADO v14b).
- **Skills NOVAS criadas pela Skill 8 ate agora:** (1) `auditando-cadastro-fiscal-odoo` ✅ V1 inventario LIVE (v14b — sub-skill C5; ver seção abaixo); (2) **3 atomos NOVOS na Skill 5 ✅ LIVE v15a** — `criar_picking_inter_company` (D-OPS-3 fix codificado) + `validar_picking_inter_company` (F5b completo) + `criar_picking_entrada_destino_manual` (ETAPA F G023+origin idempotente); 19 pytest novos.
- **Checkpoints:** **5 de 24 concluidos** (C1 ✅ pre-mortem §7.1 v13 + C2 ✅ mineracao service §7.2 v13 + C3 ✅ mineracao script §7.3 v14a + C4 ✅ escopo v13 + **C5 ✅ sub-skill auditando-cadastro-fiscal-odoo V1 inventario v14b**) · C6+C6.5+C7+C8 ⬜ v15a/v15b · C9+C10 ⬜ v16 · C11+C12+C13 ⬜ v17 · C14-C17 ⬜ v18 · C18+C19+C20 ⬜ v19 · C21-C23 ⬜ v20+
- **Status global da skill 8: 🟡 PLANEJADA COMPLETA + 3 MINERAÇÕES + TESTE REAL 6 CODS PROD (v14a-ops 695.945 un + 3 NFs SEFAZ autorizadas) + SUB-SKILL C5 PRONTA (v14b)** | Proxima sessao v15a (3 atomos Skill 5 inter-company).

## SKILL 9 — `consultando-quant-odoo`  (READ ANCILLARY)  🟡
- **Objeto:** stock.quant (READ-only) ao vivo via XML-RPC | **Camada:** READ (sem WRITE) | **Service:** [`consulta_quant.py`](scripts/consulta_quant.py) (StockQuantQueryService — 2 átomos)
- **Origem:** nasceu da demanda de auditoria pós-WRITE (2026-05-23: "sobrou saldo em loc !=Indisponivel para os 104 produtos ajustados?"). NÃO faz parte da ordem bottom-up das skills WRITE — é skill ANCILLARY (suporte às outras).
- **Scripts-fonte minerados (parcial):** `monitor/1_baixar_estoques.py` (pattern de search batch), `auditoria/levantar_estoque_fora_principal.py` (classificação por usage+parent_path). Os ~35 outros READ legados (monitor/*, auditoria/comparar_sot_*, diff_*, relatorio_*, investiga_*) continuam VIVOS — átomos previstos cobrem subconjunto, demais permanecem ad-hoc.
- **Átomos implementados (2):** `listar_quants(cods, pids, empresas, pares_cod_empresa, locations_excluir, com_lote, only_principal, agregar)` (query versátil — 8 parâmetros) + `auditar_pares(pares_cod_empresa)` (helper de alto nível — classifica em zerado/so_indisp/com_saldo/sem_produto).
- **Átomos previstos:** `listar_move_lines`, `listar_pickings`, `find_orphan_mls(quant_ids)`, `snapshot_estoque_por_lote(empresa)`, `saldo_fora_principal(empresa)` — implementar conforme demanda.
- **Checkpoints:** C1 🟡 (mineração parcial — 2 scripts-fonte essenciais lidos; ~33 outros READ permanecem como referência) · C2 ✅ ([`consulta_quant.py`](scripts/consulta_quant.py)) · C3 ✅ (contrato em SKILL.md) · C4 ✅ (`SKILL.md`) · C5 ✅ ([`consultar_quants.py`](../../.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py)) · **C6 ✅** (dogfood 2026-05-23 — investigação 4856125 + auditoria 104 pares: `auditar_pares` retornou 17+46+39+2=104 ✓) · C7 ✅ (subagente READ direto + ROUTING_SKILLS + tool_skill_mapper `Estoque Odoo (Read)`/`Odoo`) · C8 ✅ ([fluxo 2.9](fluxos/2.9-consulta-quant-ao-vivo.md)) · C9 ⏸️ (decisão: NÃO mover scripts READ ainda — skill mínima cobre subconjunto; átomos previstos cobrirão mais cenários, scripts ad-hoc continuam VIVOS) · C10 ✅ (MAPA_SCRIPTS seção `scripts/consulta_quant.py`)
- **Status global da skill 9: 🟡 — READ-only mínimo viável, ancillary** (2026-05-23 — pattern de "auditar saldo restante" cristalizado em `auditar_pares`; corrige erro de produto-cartesiano (cods × empresas) presente na 1ª query inline; case real "sobrou saldo dos 104 produtos?" → 17 zerados + 46 só_indisp + 39 com_saldo + 2 sem_produto = 104 ✓).

## SUB-SKILL C5 — `auditando-cadastro-fiscal-odoo`  (PRE-FLIGHT)  🟡 (V1 inventario LIVE + 14 pytest + smoke PROD 6 cods 987ms)
- **Objeto:** product.product + l10n_br_ncm + stock.lot (G014) + AjusteEstoqueInventario (D-OPS-2) | **Camada:** READ-only + WRITE opcional (G035 auto-fix) | **Service:** [`app/odoo/estoque/scripts/cadastro_fiscal_audit.py`](scripts/cadastro_fiscal_audit.py) (CadastroFiscalAuditService — capinado 2026-05-25 v14b a partir de `validar_cadastro_fiscal` no script 09 + `gtin_validator.py` + queries D-OPS-2 em AjusteEstoqueInventario)
- **Origem:** decisao Rafael v13 (§4.0 do PLANEJAMENTO_SKILL8_FATURANDO.md) — pre-flight como sub-skill agnostica com perfis multiplos para reuso futuro em venda-cliente. NAO entry-point da Skill 8 (amarraria reuso).
- **Perfis previstos:** V1 ✅ `inventario` (LIVE v14b) · V2 ⬜ `venda-cliente` (futuro: certificado A1 + IE destinatario + tabela_preco + FCI) · V3 ⬜ `compras-importacao` (futuro hipotetico — NCM + dados aduaneiros)
- **Gotchas cobertos V1 inventario (6):** G017 NCM ausente (BLOQUEIO), G018 weight=0 (WARN — fallback no picking F5b->F5c), G035 barcode invalido GTIN (BLOQUEIO ou AUTO-FIX via `gtin_validator.clear_invalid_barcodes`), G014 lote vencido com saldo (WARN — ETAPA B resolve on-the-fly via Skill 2; filtra LOCAIS_INDISPONIVEL CR-HIGH-2), D-OPS-2 duplicacao pipeline (BLOQUEIO — AjusteEstoqueInventario com mesmo cod+company em fase F5a..F5e), D-OPS-3 tracking='none' (INFO — apos fix Skill 2 v14b nao bloqueia mais).
- **Atomos implementados (4 checks + 1 entry-point):** `_check_ncm_weight_tracking(produto_ids)` (G017+G018+D-OPS-3 em 1 query bulk), `_check_barcode_invalido(produto_ids, auto_corrigir, dry_run)` (G035 + auto-fix opcional sem double round-trip CR-HIGH-1), `_check_lote_vencido(produto_ids)` (G014 — filtra Indisp para saldo real), `_check_duplicacao_pipeline(produtos, ciclo)` (D-OPS-2 — query AjusteEstoqueInventario, skipped sem db_session), `auditar_perfil_inventario(produto_ids OR cods_produto OR ciclo, ...)` (entry-point unificado retornando `status_global`/`pode_faturar`/`bloqueios`/`warnings`/`acoes_aplicadas`/`tempo_ms`).
- **3 formas de input mutuamente exclusivas:** `produto_ids` (lista int) | `cods_produto` (lista default_code) | `ciclo` (le AjusteEstoqueInventario com status ATIVOS do ciclo — exige db_session no construtor).
- **Modos CLI:** `--produtos/--cods/--ciclo` (mutuamente exclusivos) + flags `--auto-corrigir-barcode` (G035 auto-fix) + `--no-pipeline-check` (skip D-OPS-2) + `--no-lote-vencido-check` (skip G014) + `--confirmar` (autoriza WRITE de barcode). Exit codes: 0=OK, 1=BLOQUEADO, 2=WARN, 3=erro uso.
- **Checkpoints:** C1 ✅ (mineracao 3 fontes: `validar_cadastro_fiscal` script 09 L228-294 + `gtin_validator.py` 117 LOC + modelo AjusteEstoqueInventario.fase_pipeline) · C2 ✅ ([`scripts/cadastro_fiscal_audit.py`](scripts/cadastro_fiscal_audit.py) ~430 LOC; **14 testes pytest verdes** cobrindo resolucao 4 + NCM/weight/tracking 1 + barcode auto-fix 2 + entry-point status global 5 + constantes 2) · C3 ✅ (contrato em SKILL.md com 3 formas input + perfis + cobertura V1) · C4 ✅ ([`SKILL.md`](../../.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md)) · C5 ✅ ([`auditar_cadastro_inventario.py`](../../.claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py) CLI com 3 modos input + flags) · **C6 ✅** (smoke PROD v14a-ops 6 cods em 987ms: detectou 2 G014 lotes 0711/24 vencidos cods 4829046+4879046 + 1 D-OPS-3 cod 103500105 PIMENTA JALAPENO + 0 bloqueios; status PRE_FLIGHT_WARN + pode_faturar=true; esperado) · C7 ✅ (subagente `gestor-estoque-odoo` skills frontmatter + header v14b; `ROUTING_SKILLS.md` header count 48→49 + tabela skills + decision tree §8 + lista skills Odoo; `tool_skill_mapper.py` 'Pre-Flight Cadastro Fiscal Odoo'; `CLAUDE.md estoque` §6 nova tabela sub-skills PRE-FLIGHT) · C8 ⬜ (folha de fluxo ainda nao criada — pendencia v15b quando orchestrator Skill 8 base invocar sub-skill via subprocess) · C9 N/A (NAO move scripts — service novo do zero) · C10 ✅ (este ROADMAP atualizado v14b)
- **Code-review v14b aplicados (HIGH-1+HIGH-2+HIGH-3):** evita double round-trip Odoo em `_check_barcode_invalido` (reusa lista de find_invalid_barcodes); exclui LOCAIS_INDISPONIVEL na quant query de `_check_lote_vencido` (saldo fantasma nao conta); usa `app.utils.timezone.agora_utc` (convencao projeto).
- **Status global da sub-skill C5: 🟡 V1 inventario LIVE** (2026-05-25 v14b — invocavel diretamente pelo usuario OU via subprocess pela Skill 8 v15b+; 0 execuções `--confirmar` em PROD nesta sessao; G035 auto-fix preparado mas nao testado em PROD — usar `--auto-corrigir-barcode --confirmar` quando demanda real surgir). Memoria: `[[sub-skill-c5-pattern]]`.

---

## NÃO VIRAM SKILL (registro)
- **Leitura/diff/SOT batch** (~33 scripts restantes: `monitor/2,3,4`, `01_extrair_estoque_odoo`, `08_extrair_pos_execucao`, `comparar_sot_*`, `confronto_4_fontes`, `diff_*`, `relatorio_*`, `investiga_*`, etc.) → continuam como scripts ad-hoc operação viva. A skill 9 cobre o pattern essencial de busca `stock.quant`; casos específicos (snapshot CSV batch, classificação por usage, cross-source com Render local) são átomos PREVISTOS na skill 9 — implementar conforme demanda. **Justificativa do C9 ⏸️ da skill 9:** mover scripts READ sem cobertura completa quebra fluxos que dependem deles (operação viva).
- **JÁ-MORTO** (discovery F0: 00-00e, auditoria/investiga_*, baixar_xml_preview_626032, debug_sefaz_608607) → arquivar em `_historico/`.
- **`operando-lote`** (stock.lot) = **utils** em `app/odoo/estoque/_utils.py` (chamado por skills 1/2).

---

## LEGENDA
⬜ não iniciado · 🟡 parcial · ✅ concluído · C# = checkpoint do checklist fixo.
Atualizar status do checkpoint e da skill A CADA avanço (este arquivo é o progresso vivo).
