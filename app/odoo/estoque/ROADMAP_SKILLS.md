# ROADMAP_SKILLS — task-list física (capinar átomo por átomo)

**Criado:** 2026-05-22 | **Constituição:** `app/odoo/estoque/CLAUDE.md` | **Mineração:** `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`
**Para:** Claude Code + agente web. Este é o **arquivo de progresso vivo** da migração 105-scripts → ~8 skills-átomos + subagente `gestor-estoque-odoo`.

---

## ⏯️ ESTADO ATUAL E COMO CONTINUAR (handoff — atualizar a cada avanço)

**Onde:** worktree `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, base atual 7+ commits sobre main@a937748b — último v14a). `main` está VIVO (Rafael commita em paralelo — avancou 11 commits desde v13: SPED V36, weekly, fix tabelas, SDK 0.2.87, D8) → merge coordenado depois. Nenhum conflito esperado em `app/odoo/estoque/` (SPED V36 e' em `app/relatorios_fiscais`, SDK em `app/agente`).

**Retomar (ordem):** 1) `cd` na worktree + `source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate`; 2) carregar DATABASE_URL+ODOO_* (worktree sem `.env`): `set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a`; 3) ler `app/odoo/estoque/CLAUDE.md` (constituição/mentalidade); 4) ler este ROADMAP; 5) **se sessao for sobre Skill 8 `faturando-odoo` — LER `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO + atualizar checkpoint ativo (regra inviolavel 0 do planejamento)**. Baseline esperado: **393 pytest verdes** (tests/odoo/ — v14a confirmado em 15.87s).

**Sessão 2026-05-25 v14a (C3 mineração script + revalidação R1 — sem código, só docs):**
- ✅ **Verificação main**: avançou 11 commits (SPED V36, weekly, fix tabelas Sentry, SDK 0.2.87, D8) — nenhum conflito esperado em `app/odoo/estoque/`. Sem rebase nesta sessão.
- ✅ **Pytest baseline confirmado**: 393 verdes em 15.87s (tests/odoo/).
- ✅ **AskUserQuestion**: foco v14a só escolhido (preserva contexto para v14b fresca conforme pre-mortem R6).
- ✅ **C3 mineração completa** do script `09_executar_onda1_bulk.py` (1866 LOC):
  - Estrutura mapeada: 11 funções top-level em 6 etapas A→F + main() + helpers.
  - Tabela §7.3 do PLANEJAMENTO com funções+linhas+side-effects+deps documentada.
  - Pattern de orchestração identificado em `main()` L1771-1860: **etapa = barreira de sincronização** confirmada (cada `if 'X' in etapas` → executa → `db.session.expire_all() + carregar_ajustes()` → só depois próxima).
  - **9 descobertas novas D10-D18** documentadas como padrões a PRESERVAR no orchestrator Skill 8:
    - D10: `db.engine.dispose()` PROFILÁTICO antes E após C+D (mais agressivo que retry interno)
    - D11: `expire_all() + carregar_ajustes()` entre etapas (barreira sincronização)
    - D12: `--apenas-etapa` + `--ate-etapa` para recovery operacional
    - D13: ETAPA A é SEQUENCIAL (max_workers arg legacy — XML-RPC não thread-safe Request-sent)
    - D14: `_commit_resilient` (script) MAIS FORTE que `_commit_with_retry` (service) — faz `engine.dispose()` se SSL
    - D15: ETAPA A 100% DELEGÁVEL para Skill 2 `transferindo-interno-odoo`
    - D16: `time.sleep(5)` entre chunks ETAPA B (G022 over-reservation mitigation)
    - D17: `ACAO_PARA_CFOP_ENTRADA` 5xxx→1xxx (não centralizada — pendência §9)
    - D18: default `dry_run=True` + `--confirmar` + `--confirmar-sefaz` (2 níveis)
- ✅ **R1 RESPONDIDO — decisão 10.3 INTACTA**:
  - Macro: pattern script CONFIRMA "etapa = barreira" (mecanismo explícito).
  - Micro ETAPA B: sub-nuance descoberta — pipeline POR PICKING com sleep 5s (G022 mitigation D16). Documentada em §6.2 + §7.3 + §10.3. **Não requer AskUserQuestion adicional**.
- ✅ **Pendências §9 atualizadas**:
  - Resolvidas: `validar_cadastro_fiscal` LOCALIZADO em script (não precisa de `gtin_validator.py` separado para G017/G018 V1); decisões 10.4/10.5 já fechadas em v13.
  - NOVAS pendências para v15b/v17: centralizar `ACAO_PARA_CFOP_ENTRADA` + 5 outras constantes inline em `app/odoo/constants/`.
  - NOVA pendência v14b: decidir se G035 (barcode inválido) entra na sub-skill V1 ou adia.
  - NOVA pendência v15b/v16: consolidar helper `_commit_resilient` (versão MAIS FORTE D14) em arquivo único para reuso.
- ✅ **Refatorações §0/§6.2/§7-tabela-C3/§9/§10.3/§11/§12 aplicadas** no PLANEJAMENTO_SKILL8.
- 🟢 **Sem mudanças em código** (só docs/planejamento).
- 🟢 **Pytest baseline mantido: 393 verdes**.

**Status global após v14a:**
- Skill 8 `faturando-odoo` 🟡 **PLANEJADA + 2 MINERAÇÕES COMPLETAS** (C1 + C2 + C3 + C4 ✅; 20 checkpoints ⬜; 6 decisões RESOLVIDAS + R1 INTACTA).
- 1 sub-skill nova prevista: `auditando-cadastro-fiscal-odoo` (C5 v14b).
- Skill 5 `operando-picking-odoo` será ESTENDIDA com 2 átomos novos em v15a (C6.5).
- Baseline pytest mantido: 393 verdes.
- Próximo passo: sessão v14b com criação da sub-skill `auditando-cadastro-fiscal-odoo` perfil inventário V1.

**Sessão 2026-05-25 v13 (Planejamento Skill 8 `faturando-odoo` — estruturacao C1+C4):**
- ✅ **Verificacao main**: main = `a937748b` (merge v12); sem avanco; sem rebase.
- ✅ **Pytest baseline confirmado**: 393 verdes em `tests/odoo/` (18s). Observacao: rodar `tests/odoo/services/` isolado produz 27 falhas (fixture pollution pre-existente); usar `tests/odoo/` como baseline canonico.
- ✅ **AskUserQuestion**: foco A (Skill 8) escolhido. Rafael: "estruturar bem a skill, depois trabalhar em casos reais" + lembrete explicito "erros + SSL connection timeout".
- ✅ **Levantamento contexto Skill 8** (subagente Explore + leituras complementares):
  - Service `inventario_pipeline_service.py` (1.346 LOC, F5a-F5e + helpers `_commit_with_retry`/`_garantir_payment_provider`/`_garantir_fiscal_setup`/`_corrigir_price_zero_em_invoice`).
  - Script-fonte macro `09_executar_onda1_bulk.py` (~1.850 LOC, etapas A-F).
  - 15 scripts ad-hoc vivos (`fat_lf_*`, `09*`, `debug_sefaz_*`).
  - Constants OK (MATRIZ_INTERCOMPANY + picking_types + ids_diversos); journals (847/1002/987) NAO centralizados.
  - 9 gotchas mapeados (G004/G007/G011/G016/G017/G018/G023/G029/G034/G035).
  - Pattern Skill 6 v9 `pre_etapa_executor.py` identificado como template.
  - Galho 1.1/1.3 dos fluxos: NENHUMA folha criada.
- ✅ **Mapeamento SSL/timeout completo**:
  - G016 fix codificado: combinacao A (commit antes operacao longa) + B (try/except + retry + re-fetch via `db.session.get`) + C (TCP keepalive em `config.py:115-118`).
  - Recovery scripts `fat_lf_resume.sh` (B→D, 18 iter timeout 900s, stagnation detector) + `fat_lf_resume_entrada.sh` (E:30 iter + F:12 iter, timeout 600s).
  - Quirks CIEL IT timing (3-5min madrugada, 5-10min manha, >2h pico).
- ✅ **NOVO ARQUIVO**: `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~600 LOC) — documento vivo de planejamento persistente.
  - 14 secoes: cabecalho de estado, visao macro, escopo, decomposicao etapas A-F, pre-flight, SSL/timeout/recovery, pattern Skill 6 v9 reuso, 23 checkpoints granulares, pre-mortem 4 dimensoes x 6 etapas, riscos arquiteturais, pendencias vivas, decisoes (6, 2 RESOLVIDAS + 4 pendentes v14), cronograma (8 sessoes v13→v20+), trilha de auditoria, glossario, ponteiros.
  - **Regra inviolavel 0** documentada: ANTES de qualquer modificacao em codigo Skill 8 LER este arquivo INTEIRO + atualizar checkpoint ativo.
  - Checkpoints C1 (pre-mortem) + C4 (escopo) marcados ✅; restantes ⬜.
  - Cronograma realista: v14 (C2/C3 mineracao + C5 pre-flight) → v15 (C6/C7/C8 base+F5a+F5b) → v16 (C9/C10 F5c+F5d) → v17 (C11/C12/C13 F5e+E+F) → v18 (C14/C15/C16/C17 recovery+SKILL+tests) → v19 (C18/C19/C20 folhas+cross-refs+canary) → v20+ (C21/C22/C23 bulk+code-review+commit).
- ✅ **Decisoes RESOLVIDAS** com Rafael:
  - 10.1 Escopo COMPLETO A-F em N sessoes (nao incremental)
  - 10.2 Estruturar antes; casos reais apos C18
- ⬜ **Decisoes PENDENTES** para v14:
  - 10.3 Pattern paralelismo (preservar Semaphore=5 vs refatorar ThreadPool Skill 6) — recomendacao: preservar
  - 10.4 Centralizar journals nesta skill (vs adiar) — recomendacao: adiar para Skill 7
  - 10.5 Pre-flight como sub-skill vs entry-point — recomendacao: entry-point (b)
  - 10.6 Refatorar F5a/F5b para Skill 5 — recomendacao: nao refatorar
- 🟢 **Sem mudancas em codigo nesta sessao** (so docs/planejamento).
- 🟢 **Pytest baseline mantido: 393 verdes**.

**v13 mid-sessao (continuou apos commit 63d817d5)**: Rafael pediu para aproveitar contexto e fechar A+B+C.
- ✅ **A — Decisao 10.5 RESOLVIDA**: pre-flight como **sub-skill nova `auditando-cadastro-fiscal-odoo`** (agnostica com perfis multiplos — atende Skill 8 inventario + futuro venda-cliente). Razao Rafael: "podem haver faturamentos para cliente cujo pre-flight tera regras DIFERENTES (certificado A1, IE, FCI, etc.)". §4 reescrita inteira como DELEGADO + contrato V0 + perfis multiplos.
- ✅ **B — 3 decisoes adicionais RESOLVIDAS**:
  - **10.3 Paralelismo**: PRESERVAR Semaphore=5 + **ETAPA = BARREIRA DE SINCRONIZACAO** (todos pickings → todas validacoes → todas emissoes; mitiga DetachedInstanceError + SSL drop). Razao explicita Rafael ("erros de DetachedInstanceErros e SSL connection timeout").
  - **10.4 Journals**: ADIAR para Skill 7 escriturando (tarefa ortogonal).
  - **10.6 Refatorar F5a/F5b**: **REFATORAR COMPLETAMENTE** seguindo principio "Fluxo >> Skills" — atomos NOVOS na Skill 5 (`criar_picking_inter_company` + `validar_picking_inter_company`). Razao Rafael: "Se mexe com picking, devera ser atraves da Skill 5; principio da atomicidade e funcao especifica".
  - **NOVO checkpoint C6.5 v15**: estender Skill 5 com atomos inter-company (~1 dia extra; +1 sessao no cronograma).
- ✅ **C — Mineracao detalhada `inventario_pipeline_service.py` COMPLETA** (~70k tokens consumidos):
  - Tabela §7.2 com 14 metodos+linhas+side-effects+deps (cabecalho L1-L575 + F5a-F5e L581-1346).
  - **9 descobertas-chave D1-D9** documentadas como padroes a PRESERVAR no orchestrator:
    - D1: SNAPSHOT antes de threads | D2: agrupamento por picking | D3: bug L19/L20/L21 fix (preencher_qty_done sequencia)
    - D4: G023 linhas_esperadas | D5: SNAPSHOT meta + db.session.get re-fetch em polling longo
    - D6: sub-etapas F5d.5/.6/.7 em try/except | D7: HARD_FAIL_CONFIG_ERRORS aborta batch
    - D8: idempotencia TRIPLA em F5e | D9: db.session.get re-fetch + commit_with_retry apos Playwright
  - Achados secundarios MED-B-2 / MED-C-1 / MED-C-2 + dependencias externas listadas.

**Status global apos v13 mid-sessao:**
- Skill 8 `faturando-odoo` 🟡 **PLANEJADA COMPLETO** (C1 + C2 + C4 ✅; 21 checkpoints ⬜; 6 decisoes RESOLVIDAS; pattern arquitetural FINAL declarado).
- 1 sub-skill nova prevista: `auditando-cadastro-fiscal-odoo` (C5 redefinido para criar — v14).
- Skill 5 `operando-picking-odoo` sera ESTENDIDA com 2 atomos novos em v15 (C6.5).
- Baseline pytest mantido: 393 verdes.
- Proximo passo: sessao v14 com mineracao C3 (script `09_executar_onda1_bulk.py` 1850 LOC) + criar sub-skill `auditando-cadastro-fiscal-odoo` (C5).

**Sessão 2026-05-25 v12 (S1+S2+S4 fechando lacunas v11 — Skill 2 ARQUITETURALMENTE COMPLETA):**
- ✅ **Pre-mortem da operacao v10+v11** identificou 3 lacunas estruturais:
  - L1: 1 un MIGRACAO em FB/Estoque do cod 4310176 ficou orfao (skill 2 modo C levantou ValueError, pulamos manual)
  - L2: 28 reserveds residuais negativos + 2 saldos negativos precisaram cleanup MANUAL apos bulk
  - L3: subagente nao sabia da regra de cleanup pos-bulk
- ✅ **S1 — Fallback automatico Modo B em `distribuir_para_indisponivel`**:
  - Quando atomo modo C levanta `ValueError('lot_id_origem == lot_id_destino')` E lote eh variante MIGRACAO (deteccao DUPLA — substring match + `is_migracao` semantica), o helper tenta automaticamente `transferir_entre_locations` (Modo B) mantendo o mesmo lote, movendo origem → Indisp.
  - Output marca `_fallback_modo_b=True` + `_fallback_motivo`.
  - Caso real 4310176 reprocessado em PROD: 1 un MIGRACAO movido com sucesso. Cobertura 100% (era 99.9%).
  - +3 testes pytest (fallback OK + fallback fail pula + filtro semantico nao-MIGRACAO).
- ✅ **S2 — Flag `--cleanup-pos-bulk` no CLI**:
  - Apos bulk, lista quants em FB exceto Indisp dos cods processados com transferencias executadas:
    - reserved_quantity<0 → Skill 2.4 `zerar_residual` (COM GUARD MO ativa via Skill 9 — pula quants com MLs vivas)
    - quantity<0 → Skill 1 `ajustar_quant --valor-absoluto 0`
  - Output em `payload.cleanup_pos_bulk`; CSV opcional `--csv-cleanup PATH`.
  - Exit code do CLI considera FALHA do cleanup (eleva para 1).
  - Smoke PROD: 3 cods, cleanup_OK_VAZIO (ja zerado em v11).
  - +6 testes pytest (vazio, classificacao 2 tipos, exclui Indisp, dry-run propagado, guard MO ativa).
- ✅ **S4 — Invariantes NOVAS no subagente `gestor-estoque-odoo`**:
  - **CLEANUP POS-BULK obrigatorio** apos `distribuir_para_indisponivel` (com flag `--cleanup-pos-bulk` como atalho)
  - **Fallback Modo B** documentado como comportamento padrao quando lote MIGRACAO origem==destino
- ✅ **Mitigacoes pre-mortem v12**:
  - **S1**: deteccao DUPLA (substring + semantica) para fallback (mitiga risco de matching errado se msg do atomo mudar)
  - **S2-A**: GUARD MO ativa via `listar_move_lines_por_quant` (cross-ref tupla G030) antes de zerar reserved<0 — quants com MLs vivas vao para `quants_pulados_mo_ativa` em vez de zerar reserva legitima
  - **S2-B**: cleanup contribui para exit code do CLI (FALHA_ODOO no zerar/ajustar eleva exit 1)
- ✅ **Baseline pytest: 388 → 390 verdes** (+2 testes mitigacao pre-mortem)
- ✅ **Skill 2 `transferindo-interno-odoo` MATURADA ARQUITETURALMENTE**:
  - 3 modos atomicos (A lote→lote / B loc→loc / C para-indisponivel)
  - Helper alto-nivel `distribuir_para_indisponivel` com fallback automatico Modo B
  - CLI alto-nivel `transferir_para_indisp_em_lote.py` com `--cleanup-pos-bulk` integrado
  - Demanda real 158 cods FB processada (v10+v11) + lacunas estruturalmente resolvidas (v12)

**Sessão 2026-05-25 v11 (FASE C bulk — 153 cods FB Indisponivel + cleanup completo):**
- ✅ **FASE C.1 — re-dry-run 153 cods**: consistente com dry-run anterior (141 OK + 9 parciais + 3 falhas), ~50s. Sem alteracao de saldo entre v10 e v11.
- ✅ **FASE C.2 — bulk REAL 153 cods**: 11min 33s, 485 transferencias executadas, 10.994.553 un movidos FB/Estoque → FB/Indisp/MIGRAÇÃO. Status: 141 EXECUTADO_TOTAL + 9 EXECUTADO_PARCIAL + 2 FALHA_PRODUTO + 1 FALHA_SEM_QUANT. Cobertura 99.68%.
- ✅ **FASE C.3 — verificacao Odoo direto**: sample 10 cods aleatorios via Skill 9 — 100% match esperado (FB/Estoque=0, FB/Indisp acrescido).
- ✅ **FASE C.4 — cleanup pendencias**:
  - **Cleanup reserveds residuais via Skill 2.4 `--zerar-residual`**: 28 quants processados (17 cods em FB/Pré-Prod), -28.265 un de reserved negativo zerados em 5.4s. Skill 2.4 modo `zerar_residual` validado em PROD.
  - **Cleanup saldos negativos via Skill 1 `--valor-absoluto 0`**: 2 quants com qty<0 ajustados para qty=0 (260624 SAL SEM IODO -877.175 → 0; 260626 ACIDO CITRICO -34.795 → 0). +911.97 un de Physical Inventory.
- ✅ **FASE C.5 — Estado final FB**:
  - 0 quants com qty<0 em FB exc Indisp ✓
  - 0 quants com qty=0 + reserved<0 ✓
  - 9 quants com qty>0 + reserved>0 (saldo legitimo MOs ativas — cod 104000031 SACARINA SODICA — NAO MEXER).
- 🟢 **Pendencias REAIS finais (12 cods, 35.313 un — 0.32% da demanda)**:
  - 2 FALHA_PRODUTO (45121452 + 501 — cods inexistentes em product.product)
  - 1 FALHA_SEM_QUANT (104000011 HIPOCLORITO — sem saldo em FB/CD/LF)
  - 1 SALMOURA 1969 un — saldo Odoo de fato menor que pedido
  - 8 cods < 1 un — arredondamento (saldo residual em LF/CD/Pre-Prod fora escopo)
  - 1 caso 4310176 — 1 un MIGRAÇÃO em FB/Estoque == MIGRAÇÃO destino (skipped corretamente).
- ✅ **Artefatos persistidos**: `docs/inventario-2026-05/v10-skill2-indisp-em-lote/fase-c-bulk/` (README + JSONs + CSVs detalhados de toda jornada PROD).

**Totalizacao jornada v10+v11**:
- 5 cods canary/sub-piloto v10 + 153 cods bulk v11 = **158 cods FB demanda completa processada**
- **11.009.776 un movidos FB/Estoque → FB/Indisp/MIGRAÇÃO** + 28 reserveds zerados (-28.265 un) + 2 saldos negativos ajustados (+912 un)
- Tempo total PROD: ~12 min
- 495+ writes Odoo executados (8 canary/sub-piloto + 485 bulk + 28 zerar + 2 ajustar)

**Status global apos v11:**
- Skill 2 `transferindo-interno-odoo` ✅ **MATURADA** — 3 modos atomicos + helper alto-nivel `distribuir_para_indisponivel` validado em demanda real PROD.
- Skill 2.4 `operando-reservas-odoo` ✅ — modo `--zerar-residual` validado em batch (28 quants).
- Skill 1 `ajustando-quant-odoo` ✅ — modo `--valor-absoluto 0` validado para cleanup de saldos negativos.
- **Baseline pytest: 381 verdes** (sem mudanca apos v11 — sem novo codigo).

**Sessão 2026-05-25 v10 (Skill 2 alto-nível — helper `distribuir_para_indisponivel` + canary 5 cods REAL):**
- ✅ **Verificação main**: avancou apenas `fb494608` cosmético (mesmo de v8/v9) — sem rebase.
- ✅ **FASE A — avaliacao demanda real (158 cods FB)**: planilha simples (cod, qty, nome). Skill 9 cross-ref ao vivo: 552 quants em FB exceto Indisp, 155 dos 158 cods com saldo. Distribuição: 44 single-lote OK + 74 multi-lote + 28 com reserva ativa + 9 saldo insuficiente + 3 sem quant. Politica definida com Rafael: origem = todas locs FB exceto Indisp; selecao MIGRACAO_FIRST_FIFO; reserva via `--resetar-reserva-origem` (defensivo).
- ✅ **FASE B — capinagem**:
  - **Helper alto-nível** `distribuir_para_indisponivel` em `app/odoo/estoque/scripts/transfer.py` (+~250 LOC): _listar_quants_origem (read enriquecido + N+1 evitado), _ordenar_quants_origem (3 politicas), greedy distribute com ValueError-handling (pula quant em pre-cond do atomo — caso 4310176 lote MIGRACAO origem==destino).
  - **CLI thin wrapper** `.claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py` (~370 LOC): --planilha CSV ou --cods inline, --dry-run default, --csv-out, --csv-pendencias, exit codes 0/1/2/4.
  - **17 testes pytest novos** em `tests/odoo/services/test_distribuir_para_indisponivel.py` cobrindo: distribuicao greedy, 3 politicas (MIGRACAO_FIRST_FIFO/FIFO/MAIOR_SALDO), reserva (resetar vs respeitar), pre-cond invalidas, ValueError do atomo capturado, FALHA_AUMENTO em meio continua tentando outros.
  - **Baseline pytest estoque 364 → 381** verdes.
  - **SKILL.md atualizado** com nova receita (8 exemplos + secao "orquestrador alto-nivel" + gotchas).
  - **Fluxo 2.2.j** criado: `app/odoo/estoque/fluxos/2.2.j-para-indisponivel-em-lote.md` com sequencia composta + gotchas + receita.
- ✅ **FASE C parcial — canary + sub-piloto REAL PROD**:
  - **Canary 1 cod** `210844125` (2 lotes 13203+13757, 2536 un): EXECUTADO_TOTAL em 8s. Verificacao Odoo direta: FB/Estoque ambos zerados, FB/Indisp MIGRACAO subiu de 5500→8036 (delta exato 2536).
  - **Sub-piloto 4 cods**: 3800005 BATELADA INGLES (3093.72), 210881114 ROTULO BARBECUE (2988), 209751213 ROTULO OLEO (3047), 210030214 CAIXA PAPELAO (3559). EXECUTADO_TOTAL 4/4 em 10.5s. Verificacao Odoo 100% match.
  - **Total PROD nesta sessao**: 5 cods, 8 transferencias internas, 15.224 un movidas FB/Estoque → FB/Indisp/MIGRACAO.
- ✅ **Artefatos pos-sessao** em `docs/inventario-2026-05/v10-skill2-indisp-em-lote/`: README com plano FASE C bulk + demanda_completa_158.csv + demanda_restantes_153.csv (sem 5 ja exec) + pendencias_dry_run.csv (12 cods) + audit_dry_run.csv + canary1.json + sub_piloto.json.
- 🟡 **FASE C bulk (153 cods restantes)** para sessao seguinte: comando documentado no README v10. Estimativa 5-10 min real.

**Status global apos v10:**
- Skill 2 `transferindo-interno-odoo` 🟡 **mín viável + 3 modos + helper alto-nivel `distribuir_para_indisponivel`** — 1 canary + 4 sub-piloto PROD validados.
- **Baseline pytest: 381 verdes** (364 anterior + 17 v10 distribuir).
- 5/158 cods da demanda v10 executados em PROD; **153 cods restantes** prontos para bulk em sessao seguinte.

**Sessão 2026-05-25 v9 (09b capinado → orchestrator C3 macro Skill 6 — ciclo completo):**
- ✅ **Verificação main**: avancou apenas `fb494608` (D8 SKIP cosmetico) — sem rebase.
- ✅ **C1 mineracao**: 09b_executar_pre_etapa.py (746 LOC) lido integral + 4 services minerados (quant.py, transfer.py linhas 395-630+1018-1073 v2 API, pre_etapa.py constantes/helpers, _cli_utils.py).
- ✅ **C2 capinar**: novo `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (~580 LOC). Refatoracoes-chave:
  - POS/NEG: `transferir_quantidade_para_lote` v1 -> `transferir_quantidade_para_lote_v2` (Skill 2 v2 — guard delta_esperado propagado em ambos passos `-origem`/`+destino`).
  - PURO: `odoo.create('stock.quant')` + `action_apply_inventory` DIRETO -> `quant_svc.ajustar_quant(criar_se_faltar=True, delta_esperado=qty)` (Skill 1 com guard CICLAMATO).
  - Output: print/banner orientado a humano -> dict JSON estruturado (regra v7).
  - Mantem: auditoria via OperacaoOdooAuditoria, paralelizacao ThreadPoolExecutor.
- ✅ **C2 testes**: 21 testes pytest novos verdes em `tests/odoo/services/test_pre_etapa_executor_orchestrator.py` (helpers + execucao individual dry-run + entry-point FALHA_USO/FALHA_NENHUM_APROVADO + constantes). **Baseline pytest estoque 230 -> 251** verdes.
- ✅ **C3-C5 CLI**: novo modo `--modo executar-onda` em `.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py` (5 modos total). Args novos: `--limite`, `--cod-produto`, `--max-workers`. Status: `EXECUTADO_ONDA`, `DRY_RUN_OK_EXECUTADO`, `FALHA_NENHUM_APROVADO`.
- ✅ **C6 validacao dry-run vs Odoo PROD**: 3 smokes verdes (`/tmp/log_skill6_C6_validacao_executar_onda.json`):
  - company_id=999 → argparse error (exit 2)
  - ciclo inexistente → FALHA_NENHUM_APROVADO (exit 1)
  - dry-run real ciclo INVENTARIO_2026_05 cid=4 → DRY_RUN_OK_EXECUTADO (exit 4) — encontrou 1 ajuste APROVADO real (id=163696 NEG 835k un) e dispatch correto via Skill 2 v2 (lot_id_destino=56779 MIGRAÇÃO resolvido em 1.9s).
- ✅ **C7 cross-refs**: subagente `gestor-estoque-odoo.md` (header v7→v9 + description com executor + galho 4.1 atualizado), tool_skill_mapper (sem mudanca — skill ja mapeada), SKILL.md (5 modos + receitas executar-onda + sub-fluxo 4.1.e + armadilhas + 5 exemplos novos), fluxo 4.1 (passo F atualizado + G-PRE-10 reescrito + sub-caso 4.1.e + Cross-skill v9).
- ✅ **C9 scripts SUPERADOS**: 09b movido para `_validados/planejando-pre-etapa-odoo/` via `git mv` + sys.path corrigido (parents[2]→parents[4]) + header de ARQUIVADO. Smoke import museum vivo verde para 03b+04b+09b.
- ✅ **C10 docs**: MAPA_SCRIPTS atualizado (seção pre_etapa.py renomeada para incluir orchestrator + 09b status SUPERADO), VALIDACAO Skill 6 atualizada (09b nas SUPERADOS + cobertura testes 22→48), ROADMAP HANDOFF v9 + Skill 6 C9 ✅.

**Status global apos v9:**
- Skill 6 `planejando-pre-etapa-odoo` 🟡 **mín viável completa (5 modos)** — ciclo planejar→propor→listar→aprovar→**executar** fechado.
- **16 scripts SUPERADOS** (em `_validados/`); ~89 scripts ad-hoc continuam VIVOS.
- **Baseline pytest: 251 verdes** (230 v8 + 21 v9 orchestrator).

**Sessão 2026-05-25 v8 (Caso 71 cods 100% FECHADO):**
- ✅ Auditoria 71 cods identificou estado real: 54 OK + 8 PARCIAL + 5 MIGRACAO bloqueado + 4 SKIP planejado.
- ✅ Batch v8 (20 chamadas: 14 MODO C + 6 Skill 1): 11 cods PARCIAIS/MIGRAÇÃO resolvidos via caminho D (outros lotes alternativos livres em FB/Estoque).
- ✅ Cirurgia FB/OUT/01046 (caminho E inédito): 3 MLs bloqueantes unlinked + 3 quants zerados (reserved residual) + 3 MODO C destravando 890 un. Picking preservado com 20 MLs válidas (devoluções legítimas).
- ✅ **Caso 71 cods 100% CONCLUÍDO**: 67/67 executáveis OK + 4 SKIP planejados.
- ✅ Pattern v8 NOVO atomico: `cirurgia (Skill 2.4) → zerar_residual (Skill 2.4) → MODO C (Skill 2)`. Codificado no fluxo 2.6 caminho E.
- ✅ Regra inviolável NOVA #26+#27 no `gestor-estoque-odoo.md`: CIRURGIA (E) PREFERIDA sobre CANCELAR (A) quando picking tem MIX MLs válidas + bloqueantes.
- ✅ Documentação completa atualizada: VALIDACAO §14 + fluxo 2.6 (caminho E refinado + caso real exemplo 2) + SKILL.md 2.4 (tabela 5-caminhos refinada + armadilhas v8) + gestor-estoque-odoo.md (invariantes v8) + memórias `[[caso_real_tratar_reservas_pre_transferencia]]` (100% RESOLVIDO) + `[[fluxo_2_6_pattern]]` (pattern v8).
- ✅ Total jornada v7+v7-extras+v8+cirurgia: ~115 writes PROD, ~22.500 un transferidas para FB/Indisponivel.



**Sessão 2026-05-24 v7 (Gap reservas pre-transferencia — 4 átomos novos + fluxo 2.6 + validacao caso real):**
- ✅ **Verificação main**: nenhum commit novo desde v6 (`fb494608` ja conhecido) — sem rebase.
- ✅ **Fase A — Pesquisa AO VIVO** (probe `/tmp/investigar_unreserve_skill24.py`):
  - **Descoberta G030**: `stock.move.line.quant_id` em Odoo CIEL IT é COMPUTED `store: False` (campo UI "Pick From"). Filtro `('quant_id', 'in', [...])` é IGNORADO pelo Odoo (retorna lixo). Cross-ref ML→quant DEVE ser via tupla `(product_id, lot_id, location_id, company_id)`.
  - `stock.picking.do_unreserve` é XML-RPC público, retorna None em state=cancel (NOOP silencioso).
  - `stock.picking._action_unreserve` NÃO EXISTE (Fault method does not exist).
  - Casos reais identificados: lote 13206 em FB/INT/08022 (3 MLs, 1035.083 un); MIGRAÇÃO em 3 pickings (FB/FB/EMB/11673+11674 MO ativa + FB/OUT/01046 DEVOLUÇÃO LA FAMIGLIA).
- ✅ **Fase B — Skill 9 extensão**: 2 átomos NOVOS em `app/odoo/estoque/scripts/consulta_quant.py`:
  - `listar_move_lines_por_quant(quant_ids, states)`: cross-ref reverso via tupla G030 (read stock.quant → domain compound OR de AND → search stock.move.line).
  - `listar_pickings_por_quant(quant_ids, states)`: agrupa MLs por picking + enriquece metadados (picking_type, origin, partner, scheduled_date, create_date). Ordena por state-priority. Inclui `mls_sem_picking` para MOs.
  - CLI estendida com 2 modos novos: `--modo move-lines` + `--modo pickings`. `--states` configurável (default assigned+partial; `todos` = sem filtro).
  - **19 pytest novos** em `tests/odoo/services/test_stock_quant_query_service.py` cobrindo: vazio, default states, custom states, sem filtro, domain compound OR de N quants, resolve quant_id via tupla, picking_state batch unico, ML sem picking, incluir_move/picking flags, quantity None defensive, lot_id=False, agrupa 3MLs em 1 picking, separa mls_sem_picking, ordem assigned-antes-done, enriquece partner/origin/picking_type, zero MLs. **2 smokes PROD: 1035.083 un caso 13206 + 6 MLs MIGRAÇÃO FB/Estoque caso real.**
- ✅ **Fase C — Skill 2.4 extensão**: 2 átomos NOVOS em `app/odoo/estoque/scripts/reserva.py`:
  - `unreserve_picking(picking_id, dry_run)`: wrapper sobre `stock.picking.do_unreserve` + guard pre-state (NÃO done/cancel) + NOOP se sem MLs + aviso G_UNRESERVE_TRAVA se state pós == assigned.
  - `find_orphan_mls(quant_ids, states)`: READ-only — lista MLs apontando para quants com qty=0 (TOL 1e-4). Reaproveita Skill 9 internamente (G030 cross-ref). Retorna `mls_orfas` + `quants_zerados_com_mls` + `quants_com_saldo`.
  - CLI estendida com 2 modos novos: `--unreserve-picking` + `--find-orphan`. 5 modos totais (cirurgia + cancelar + unreserve + find-orphan + zerar-residual).
  - **14 pytest novos** em `tests/odoo/services/test_stock_reserva_service.py` cobrindo: dry-run default, picking inexistente, state done/cancel recusado, sem MLs NOOP, --confirmar releitura, aviso G_UNRESERVE_TRAVA, exceção Odoo, quant_ids vazio, classifica zerado vs saldo, sem MLs retorna vazio, states default/customizado, TOL 1e-4.
- ✅ **Fase D — Fluxo 2.6**: `app/odoo/estoque/fluxos/2.6-tratar-reserva-bloqueia-transferencia.md` criado com 5 caminhos seguros (A=cancel/B=devolver/C=unreserve/D=outro lote/E=cirurgia órfã). Regra de seleção D→E→A→B→C. Composição Skills 9+2.4+5+2. README dos fluxos atualizado com galho 2.6.
- ✅ **Fase E — Regra inviolavel + tabela**:
  - Subagente `gestor-estoque-odoo`: regra inviolável NOVA "PRÉ-CHECK reserva ANTES de Skill 2" + invariante G030 + atualização da árvore com galho 2.6 + 2 novos átomos Skill 2.4 + 2 novos modos Skill 9 no header v6→v7.
  - SKILL.md Skill 2.4 estendida com tabela "5 caminhos seguros para desreservar" + contratos de 5 átomos + armadilhas G_UNRESERVE_TRAVA + G030.
  - SKILL.md Skill 9 estendida com 3 contratos (quants + move-lines + pickings) + receitas + armadilha G030.
  - Gotcha G030 documentado em `docs/inventario-2026-05/02-gotchas/G030-quant-id-em-stock-move-line-eh-computed.md`.
- ✅ **Fase F — Validação com caso real 71 cods**:
  - Auditoria pos-implementação confirmou estado idêntico ao v6.1: 4 pickings bloqueantes (FB/INT/08022 13206 + FB/FB/EMB/11673+11674 MO + FB/OUT/01046 DEVOLUÇÃO).
  - Rafael escolheu estratégia β (cancelar FB/INT/08022, PULAR os 3 MIGRAÇÃO).
  - **PROD: FB/INT/08022 (id=320753) cancelado** via Skill 5 `--modo cancelar --confirmar` em 1.43s. Verificado via Skill 9 modo pickings: 0 pickings reservando os 3 quants 13206. reserved_quantity=0 nos 3 quants confirmado.
  - Batch dry-run iniciado: 84 chamadas Skill 2 modo C (95 plano A - 11 chamadas dos 5 cods MIGRAÇÃO pulados). Amostra (4 chamadas dos cods desbloqueados): 3 DRY_RUN_OK + 1 FALHA_LOTE_DESTINO_INEXISTENTE (esperado — MIGRAÇÃO não existe ainda; em --confirmar `criar_se_nao_existe` cria).
- 🟡 **Fase G — pendente**: cross-refs ROUTING_SKILLS + commit consolidado (in progress).

**Sessão 2026-05-24 v6 (Skill 6 `planejando-pre-etapa-odoo` — capinada do zero):**
- ✅ **Verificação main**: avançou 1 commit cosmético (`fb494608` skip D8 sem código) — sem rebase necessário.
- ✅ **C1 mineração**: 3 scripts-fonte lidos integral (`03b_planejar_pre_etapa_cd` planner READ, `04b_propor_pre_etapa_cd` WRITE banco local com workflow hash, `09b_executar_pre_etapa` executor C3 — DELEGADO para Skills 1+2, NÃO entra na Skill 6) + service existente `PreEtapaEstoqueService` (340 LOC, 4 dataclasses, algoritmo 10-passos D007) + 13 testes pytest existentes.
- ✅ **C2 capinar + estender** `app/odoo/services/pre_etapa_estoque_service.py` → `app/odoo/estoque/scripts/pre_etapa.py` + shim em `services/`. Estendido com 7 funções helper top-level (`enriquecer_quants_para_planejar`, `_serializar_plano_em_dicts`, `gerar_excel_plano_pre_etapa`, `planejar_pre_etapa_batch_company`, `_calcular_hash_onda`, `_fazer_backup_pg_dump`, `propor_ajustes_pre_etapa`, `listar_onda_pre_etapa`, `aprovar_onda_pre_etapa`) + 4 constantes (`ACOES_INTERNAS_POR_CID`, `ONDA_NUM_POR_CID`, `ACAO_RESIDUAL_FB_CD`, `COMPANY_LOCATIONS_PRE_ETAPA`). **13 testes originais preservados via shim + 6 testes novos cobrindo helpers** (enriquecer basic+vazio, batch outliers+cods_filter, hash determinismo+sensibilidade) = **19 testes pre_etapa verdes**.
- ✅ **C3-C5 SKILL.md + CLI** `.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py` (4 modos exclusive: planejar/propor/listar-onda/aprovar-onda; `--dry-run` default em modos write; listar-onda sempre READ; exit codes 0/1/2/4).
- ✅ **C6 validação dry-run**: 3 smokes CLI passando (FALHA_INPUT_AUSENTE exit 1, FALHA_USO exit 2, DRY_RUN_OK_PLANEJADO com inputs vazios exit 4); 2 limitações documentadas (listar-onda em SQLite local — tabela só existe em PG; batch real com Odoo — scripts 01+02 não rodaram nesta worktree). Cobertura completa via 6 pytest novos (helpers I/O com mocks). Log `/tmp/log_skill6_C6_validacao_dry_run.json`.
- ✅ **C7 cross-refs**: subagente `gestor-estoque-odoo` (description + skills lista + header v5→v6 + árvore galho 4 NOVO); ROUTING_SKILLS (47→48 invocaveis + 15→16 Skills Odoo + galho 6 ESTOQUE WRITE); tool_skill_mapper (`'planejando-pre-etapa-odoo': 'Estoque Odoo (Write)'`); CLAUDE.md raiz + app/odoo/estoque/CLAUDE.md §6 catálogo + header status.
- ✅ **C8 folha de fluxo** `app/odoo/estoque/fluxos/4.1-pre-etapa-cd-d007.md` com 4 sub-casos a/b/c/d cobrindo preview antes de regenerar, re-aprovar pos-correcao, Onda 6 FB futura, debug subset cods. README atualizado com galho 4 NOVO.
- ✅ **C9-C10**: 2 scripts SUPERADOS em `_validados/planejando-pre-etapa-odoo/`: `03b_planejar_pre_etapa_cd.py` + `04b_propor_pre_etapa_cd.py` (sys.path corrigido parents[2]→parents[4]; museum vivo via shim). `09b_executar_pre_etapa.py` permanece VIVO (C3 macro pendente capinagem). VALIDACAO.md criada. MAPA_SCRIPTS atualizado seção `pre_etapa.py`.
- **Pattern reaproveitável**: Skill 6 segue pattern Skill 5 (capinagem retroativa) MAS com extensão pesada (4 helpers I/O + 4 modos CLI — diferente de Skill 5 com 3 átomos puros). Demanda-driven: planejar+propor são os modos COM demanda comprovada (03b+04b rodaram em PROD em sessão anterior); listar+aprovar são workflow auxiliar incluído para completude.

**Sessão 2026-05-24 v5 (Skill 4 `operando-mo-odoo` — NOVA, 1ª skill criada do zero do orquestrador):**

**Sessão 2026-05-24 v5 (Skill 4 `operando-mo-odoo` — NOVA, 1ª skill criada do zero do orquestrador):**
- ✅ **Verificação main**: avançou 1 commit (`fb494608 skip D8 sem código`) — sem rebase necessário (skip-only).
- ✅ **C1 mineração** dos 2 scripts-fonte (`cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py`) + **investigação AO VIVO** via `/tmp/investigar_mos_skill4.py`. Revelou: FB tem 10.000 MOs (limite atingido — mais cumulativas), CD apenas 17 (quase inativo, 15 cancel + 2 draft), LF 3.367. **Idempotência `action_cancel` em state=cancel** confirmada via probe em FB/OP/BALDE/00009 id=4192 (retorna `True` sem erro, state continua 'cancel'). **`qty_produced` ≠ consumo** validado (MOs com qty_produced=0 e consumo_total>0 são comuns).
- ✅ **C2 service `app/odoo/estoque/scripts/mo.py`** (NOVO — criado do zero, sem service legado em `services/`). Shim preventivo em `app/odoo/services/stock_mo_service.py`. 2 átomos: `cancelar_mo` (com guard G-MO-01 + G019-like re-le state) e `cancelar_mos_em_massa` (composição com filtros). Helper `medir_consumo_mo` (soma `stock.move.quantity` raw materials != cancel, chunks 200, TOL=0.0001). **29 testes pytest verdes** (26 baseline + 3 cobrindo code-review fixes).
- ✅ **C3-C5 SKILL.md + CLI** `.claude/skills/operando-mo-odoo/scripts/operar_mo.py` (single OU batch, `--dry-run` default, exit codes 0/1/2/4).
- ✅ **C6 validação dry-run vs Odoo PROD**: 4 casos (NOOP idempotente id=4192, DRY_RUN_OK id=19985 sem consumo, FALHA_FURO_CONTABIL id=19984 consumo=1410.05, batch FB ate 2025-06 consumo zero). Log `/tmp/log_skill4_C6_validacao_dry_run.json`. **0 execuções `--confirmar` em PROD** (demanda-driven — pattern já validado em PROD em sessão 2026-05-20 via scripts-fonte: 120 MOs zumbi canceladas).
- ✅ **C7 cross-refs**: subagente + ROUTING_SKILLS (46→47 invocaveis + 14→15 Skills Odoo + galho 6 ESTOQUE WRITE listando skill) + tool_skill_mapper + CLAUDE.md raiz + app/odoo/CLAUDE.md + app/odoo/estoque/CLAUDE.md §6 catálogo.
- ✅ **C8 folha de fluxo** `app/odoo/estoque/fluxos/3.1-cancelar-mo.md` com 3 sub-casos (a single, b batch, c MO COM consumo DELEGADO para `mrp.unbuild` cross-skill). README atualizado.
- ✅ **C9-C10**: 2 scripts SUPERADOS em `_validados/operando-mo-odoo/`: `cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` + VALIDACAO.md (sys.path corrigido parents[2]→parents[4]; museum vivo validado via import). MAPA_SCRIPTS atualizado seção `scripts/mo.py`.
- ✅ **Code-review paralelo (2 reviewers)**: 9 findings reais (4 HIGH + 4 MED + 1 LOW). Fixes aplicados:
  - **CR1-H1** (code): `cancelar_mos_em_massa` `search_read` sem `order` → `order='create_date asc'` server-side (FB tem 10k+ MOs).
  - **CR1-M1** (code): `_ler_mo` retorna `None` pós-`action_cancel` → tratar como `EXECUTADO` com `state_apos='cancel_deleted'` + warning.
  - **CR1-M3** (code): `consumo='qualquer'` sem `forcar_consumo=True` silenciosamente bloqueia todas → warning logado entry-point.
  - **CR2-H1** (docs): `fluxos/README.md` mostrava `2.5`/`3.1` como ⬜ → 🟡 com link folha.
  - **CR2-H2** (docs): ROUTING_SKILLS galho 6 não listava `operando-mo-odoo` → adicionado.
  - **CR2-M1** (docs): SKILL.md "C6: 2-3 casos" → "4 casos" (alinhado com VALIDACAO.md).
  - **CR2-M2** (docs): fluxo 3.1 cross-skill Skill 2 como "pré-condição de 3.1.c" → refinado (3.1.c é DELEGADO; Skill 2 apenas contexto relacionado).
- ✅ **Status novo `cancel_deleted`** introduzido para skills futuras que cancelam objetos Odoo com cascade customizado.
- ✅ **VALIDACAO_FINAL_SESSAO §10** com pre-mortem 4 dimensões + code-review consolidado.
- ✅ **Memória `[[skill4_mo_pattern]]`** criada + MEMORY.md atualizado.
- ✅ **Commit consolidado** `b8ed3b5c` em `feat/estoque-odoo` (3 sessões: v3 + v4 + v5; 36 arquivos; 175 pytest verdes totais).

**Sessão 2026-05-24 v4 (Skill 2 modo C `transferir_para_indisponivel` — NOVA + incidente G031):**
- ✅ **Demanda real** de Rafael: "Transfere esses 16 produtos pra Indisponivel" (planilha FB). Resolveu para modo composto cross loc+lote.
- ✅ **C1 mineração**: investigação ao vivo de 16 quants em FB; padrão descoberto (14 triviais 1 lote em FB/Estoque + 1 NOOP 4529301 já em Indisp + 1 split 104000033 com 2 lotes em FB/Estoque com diff -0,028).
- ✅ **C2 service `transferir_para_indisponivel`**: método novo em `app/odoo/estoque/scripts/transfer.py:797` codificando invariante "destino = (LOCAIS_INDISPONIVEL[cid], MIGRAÇÃO POR PRODUTO)". **Decomposição refatorada (CR-dry-run)**: 1 passo direto via `ajustar_quant` 2x (reduzir origem + aumentar destino com criar_se_faltar=True) — não mais composição A+B encadeada que falhava em dry-run.
- ✅ **C3-C5 CLI modo C**: `.claude/skills/transferindo-interno-odoo/scripts/transferir.py` extendido com `--para-indisponivel` flag + validação mutex com modos A/B. Status novos (pós-refactor 1-passo): `FALHA_REDUCAO`, `FALHA_AUMENTO`, `FALHA_PRE_COND`, `FALHA_LOTE_DESTINO_INEXISTENTE`. (Versão intermediária usava `FALHA_PASSO_1/2` da composição A+B encadeada — removida no refactor.)
- ⚠️ **INCIDENTE 2026-05-24 v4** (G031): 1ª `--confirmar` em PROD falhou 16/16 com erro Odoo *"O número de lote/série (MIGRAÇÃO) está vinculado a outro produto."*. Causa: usei `LOTES_MIGRACAO_POR_COMPANY[1]=30482` como FK universal, mas `stock.lot` tem `product_id` (cada produto tem seu próprio MIGRAÇÃO). Estado parcial: 4.319,4019 un reduzidas em FB/Estoque sem chegar em FB/Indisp.
- ✅ **Rollback 100%** via Skill 1 `ajustar_quant +qty criar_se_faltar=True` em cada lote origem. 16/16 EXECUTADO. Estado integral restaurado em ~10s. Log `log_2.1_ROLLBACK_para_indisp_falha_20260524_105219.json`.
- ✅ **Fix arquitetural**: `transferir_para_indisponivel` agora aceita `nome_lote_destino='MIGRAÇÃO'` (str) e resolve POR PRODUTO via `lot_svc.criar_se_nao_existe`. Constants `LOTES_MIGRACAO_POR_COMPANY` documentadas como HISTÓRICO/EXEMPLO em `constants/locations.py`. Nova constant `NOME_LOTE_MIGRACAO_POR_COMPANY` introduzida.
- ✅ **Re-execução PROD pós-fix**: 16/16 EXECUTADO em 23s; 4.319,4019 un transferidas; 15 lotes MIGRAÇÃO já existiam, 1 criado on-demand (4829012, lot_id=59829). Verificado direto no Odoo: 16/16 origem zerada + MIGRAÇÃO somando exato (ex.: 210843125 MIGR 895→1118 = +223 ✓). Log `log_2.2_para_indisp_FIX_20260524_110128.json`.
- ✅ **15 testes pytest novos** (143 verdes totais — quant 30 + transfer 52 + lot 19 + picking 42; transfer subiu de 37→52 com 15 testes novos cobrindo modo C `transferir_para_indisponivel`).
- ✅ **Gotcha G031 documentado**: `docs/inventario-2026-05/02-gotchas/G031-lot-migracao-por-produto.md`.
- ✅ **C7-C10 atualizados**: SKILL.md (contrato MODO C + receitas + exemplos + armadilha G031 + composição 2.2.i), fluxo 2.2 (nova seção MODO C), ROADMAP, memória `[[skill2_transfer_interno_pattern]]` (a atualizar).

**Sessão 2026-05-24 v3 (Skill 5 maturando — `operando-picking-odoo` C1-C10 + FECHA ONDA 0.4):**
- ✅ **Verificação main**: main NÃO avançou desde último commit (merge-base = b4f7b24c = origin/main HEAD). Sem rebase necessário.
- ✅ **Achado crítico**: G019/G020/G011/G023 já tinham FIX no service (`app/odoo/services/stock_picking_service.py`) desde 2026-05-18, mas docs/CLAUDE.md/ROADMAP marcavam ABERTO/PROPOSTO. Validei com Rafael: foco = Skill 5 + pytest baseline ANTES do C1.
- ✅ **Fase 0 — Pytest baseline G019/G020/G011/G023**: 19 testes pré-existentes em `test_stock_picking_service.py` cobriam G019/G020/G011 (4+3+2). ADICIONEI 16 novos cobrindo G023 (8: noop, match perfeito, qty divergente, duplicata, lote não esperado, sem match, qty negativa/zero, sem linhas), `ajustar_qty_done_pelo_disponivel` (6: bate, reduz+pendência, qty_done acima, state cancel, demand zero, sem ML), `validar(linhas_esperadas=)` (2: chama consolidar antes, falha consolidar não bloqueia). **35 verdes pós-Fase 0.**
- ✅ **Fase 1.5 — Adicionar `devolver_picking()` ao service**: novo método derivado de `fat_lf_cleanup.reverter_picking` (PROD 2026-05-20). Cria wizard `stock.return.picking` + write({}, context) + create_returns + popula qty_done + button_validate + invariante state=done. Idempotente via `origin ilike "Devolução de NAME"`. **+7 testes (42 verdes).**
- ✅ **Fase 2 — Capinagem**: `git mv app/odoo/services/stock_picking_service.py → app/odoo/estoque/scripts/picking.py`. Shim criado em `services/` re-exportando. 7 consumidores ativos intactos (`inventario_pipeline_service`, scripts 09/16/teste_210030325/fat_lf_05, testes). **128 verdes totais (30+37+19+42).**
- ✅ **Fase 3 — SKILL.md + CLI**: `.claude/skills/operando-picking-odoo/SKILL.md` com contrato 3 átomos + 6 receitas + 3 fluxos compostos (2.5.a/b/c) + armadilhas. `scripts/operar_picking.py` com `--modo cancelar/validar/devolver`, `--dry-run` default, exit codes 0/1/2/4.
- ✅ **Fase 4 — C6 validação dry-run PROD**: 6 casos vs Odoo PROD (pid 321147 assigned, 321146 assigned, 321150 done, 321107 cancel — combinados com 3 modos): 100% bate plano vs estado real. Log em `/tmp/log_skill5_C6_validacao_dry_run.json`. **0 execuções `--confirmar` em PROD** (demanda-driven).
- ✅ **Fase 5 — C7-C10**: subagente `gestor-estoque-odoo` lista skill + galho 2.5 com [folha 2.5]; ROUTING_SKILLS 46 invocaveis + 14 Skills Odoo + triggers picking (valida pendurado, devolve NF errada, 854 fantasmas); tool_skill_mapper `'operando-picking-odoo': 'Estoque Odoo (Write)'`; fluxo 2.5 escrito; 1 script SUPERADO movido (`16_cancelar_pickings_fantasmas`) + VALIDACAO.md; MAPA_SCRIPTS + este ROADMAP atualizados. **Docs G019/G020 PROPOSTO→IMPLEMENTADO; CLAUDE.md §8 atualizado removendo "G019/G020 ABERTOS"; ONDA 0.4 marcada ✅.**
- **Limitação documentada**: átomos `criar_picking_interno` e `alterar_lote_no_picking` previstos mas sem demanda — `criar_transferencia` existe no service (usar via Python direto); `alterar_lote` é fluxo cross-skill (Skill 2.4 unreserve + Skill 2 transfer + reassign), não átomo.

**Sessão 2026-05-24 v2 (Skill 2 maturando — `transferindo-interno-odoo` C1-C10):**
- ✅ **Fast-forward main → worktree** (origem 8d755573, agora b4f7b24c — 5 commits trazidos sem conflito; 2 docs antigos `docs/inventario-2026-05/consolidacao/ROADMAP_SKILLS.md` + `ARQUITETURA_ORQUESTRADOR_ODOO.md` convertidos em ponteiros para `app/odoo/estoque/`).
- ✅ **C1 mineração de 18 scripts** (9 lidos por mim integral + 7 por subagente Explore + 2 do main: `consolidar_lote_104000015_sal_fb`, `recuperar_aumentos_falhos`). Síntese em `/tmp/skill2-mineracao-sintese.md`.
- ✅ **C2 service `transfer.py`** movido para `app/odoo/estoque/scripts/` + shim em `app/odoo/services/`. **Estendido com:** constantes `LOTES_MIGRACAO_VARIANTES/LOTE_MIGRACAO_CANONICO/TOL_ARREDONDAMENTO`, helpers `is_migracao`/`_lotes_migracao_ids`/`_melhor_lote_migracao_na_loc`, públicos `resolver_lote_origem/destino`, e 3 novos métodos: `transferir_entre_lotes_v2` (delega `ajustar_quant`×2 com `delta_esperado` propagado), `transferir_entre_locations` (mesmo lote, 2 locs), `transferir_quantidade_para_lote_v2` (wrapper). **33 testes pytest verdes** (14 originais preservados + 19 novos cobrindo v2 + helpers + gotchas).
- ✅ **C3-C5 contrato + SKILL.md + CLI**: `.claude/skills/transferindo-interno-odoo/` com SKILL.md (~270 linhas) e `scripts/transferir.py` (CLI 2 modos exclusive: A lote→lote, B loc→loc; `--dry-run` default; suporta `--resetar-reserva-origem`, `--tolerancia-delta`).
- ✅ **C6 validação dry-run vs Odoo PROD**: 3 casos validados (10 emergenciais E01 confirma estado pós-execução de 18/05; padronizar_migracao detectado bug semântico = limitação documentada; loc→loc com saldo real = DRY_RUN_OK plano completo em 47ms). Log em `/tmp/log_skill2_C6_validacao_dry_run.json`.
- ✅ **C7 cross-refs**: subagente `gestor-estoque-odoo.md` (skills + árvore 2.2), ROUTING_SKILLS (45 invocaveis), tool_skill_mapper (`Estoque Odoo (Write)`), CLAUDE.md raiz (status skill 2).
- ✅ **C8 folha 2.2**: `app/odoo/estoque/fluxos/2.2-realocar-saldo.md` com 8 sub-casos cobertos e gotchas-invariante detalhados.
- ✅ **C9-C10**: 2 scripts movidos para `_validados/transferindo-interno-odoo/`: `10_executar_emergenciais_fb.py` + `padronizar_migracao.py` (sys.path `parents[2]→parents[4]`, header `arquivado`). Outros 16+ orquestradores PERMANECEM VIVOS. MAPA_SCRIPTS + ROADMAP atualizados. [VALIDACAO.md](../../scripts/inventario_2026_05/_validados/transferindo-interno-odoo/VALIDACAO.md).
- **Limitação documentada**: CLI não cobre caso `padronizar_migracao` (consolidar 2 grafias literais ESPECÍFICAS de MIGRAÇÃO) — adicionar `--lot-id-origem`/`--lot-id-destino` quando houver demanda real.

**Sessão 2026-05-24 v1 (cleanup das pendências bloqueantes + guard anti-bug — manhã):**
- ✅ Reversão `104000037 CICLAMATO DE SODIO FB` — `+33.7319` no quant 229937 (lote `MI074-177/25` FB/Estoque): qty `5.0136 → 38.7455`. Verificado direto no Odoo. Log: [`log_2.1_reversao_ciclamato_20260524_000000.json`](../../scripts/inventario_2026_05/auditoria/log_2.1_reversao_ciclamato_20260524_000000.json).
- ✅ Quant órfão `104000039 AROMA NATURAL - ALHO FB/Pré-Produção/Linha Manual` — quant 260657 `reserved=-0.6 → 0`. Verificado. Log: [`log_2.4_zerar_residual_orfao_aroma_20260524_000001.json`](../../scripts/inventario_2026_05/auditoria/log_2.4_zerar_residual_orfao_aroma_20260524_000001.json).
- ✅ Comunicado dos 6 pickings tocados — gerado em [`/tmp/comunicado_pickings_20260524.md`](file:///tmp/comunicado_pickings_20260524.md), entregue ao usuário.
- ✅ **GUARD `delta_esperado` implementado no service `quant.py`** — 3 novos params (`delta_esperado`, `tolerancia_delta`, `corrigir_para_esperado`); 2 novos status (`FALHA_DELTA_DIVERGENTE`, `EXECUTADO_AUTO_CORRIGIDO`); CLI atualizada; 7 testes pytest novos (29 total). Protege contra repetição do bug CICLAMATO em retomadas de FALHA. Detalhes em [VALIDACAO_FINAL_SESSAO §6](VALIDACAO_FINAL_SESSAO.md#6-sessão-2026-05-24-guard-delta_esperado--validação-cancelamentos-gaps-12-fechados).
- ✅ **Cancelamentos OUT/01053 + INT/07950 validados** — todos os 6 moves cancelados com `move_dest_ids=[]`. Self-contained, sem picking espelho LF pendente. Detalhes em [VALIDACAO_FINAL_SESSAO §6](VALIDACAO_FINAL_SESSAO.md).
- Aprendizado novo (atualizar [[feedback_ajuste_positivo_criar_saldo]]): usuário preferiu **lote real menor** (MI074-177/25 qty 5 → 38) ao **lote consolidador P-15/05** (40 → 74). Default da memória pode mudar.

**Feito até 2026-05-23 (3 skills nasceram/maturaram em 2 sessões consecutivas):**
- ONDA 0 ✅ — pacote `app/odoo/estoque/` + subagente `.claude/agents/gestor-estoque-odoo.md`.
- **Skill 1 (`ajustando-quant-odoo`) ✅ MATURADA** — 100 ajustes em produção (104 linhas → 84 EXEC + 15 reservados retomados c/ --resetar-reserva + 1 NOOP + 4 descartes). 4 políticas de premissa cristalizadas (MIGRA → 1-quant-cobre → zerar-insuficiente → PEPS multi-quant). 5 scripts em `_validados/ajustando-quant-odoo/`. **Volume efetivo: 79,65% (4.774/5.994 un); 53 COMPLETA + 45 PARCIAL + 1 OVER (104000037 CICLAMATO bug operacional, excesso 33.73 un reversível) + 1 ZERO + 4 DESCARTE.** Bug documentado em VALIDACAO.md §"Bug operacional".
- **Skill 3 (`operando-reservas-odoo`) 🟡 mín viável** — 3 átomos (`cancelar_moves_orfaos`, `cancelar_picking_inteiro`, `zerar_reserved_residual`). Caso real: 6 pickings/15 MLs órfãs limpas + 15 quants residuais zerados em ~4s. 3 scripts em `_validados/operando-reservas-odoo/`. **Gotcha descoberto:** `--resetar-reserva` (skill 1) + unlink ML (skill 3) gera `reserved < 0` → exige `zerar_reserved_residual` ao final do fluxo. Documentado em [fluxo 2.4](fluxos/2.4-cancelar-reserva-orfa.md).
- **Skill 9 (`consultando-quant-odoo`) 🟡 mín viável (ANCILLARY READ)** — 2 átomos (`listar_quants` 8-param + `auditar_pares`). Nasceu sob demanda (auditoria pós-WRITE). Dogfood: investigação 4856125 + classificação correta de 104 pares (17+46+39+2=104 ✓). [Fluxo 2.9](fluxos/2.9-consulta-quant-ao-vivo.md).
- **C7-C10 nas 3 skills:** subagente `gestor-estoque-odoo.md` lista as 5 skills (3 escopadas + 2 utils), ROUTING_SKILLS Odoo 12 entries, tool_skill_mapper 3 entradas (`Estoque Odoo (Write)/(Read)`), fluxos 2.1/2.4/2.9 escritos, MAPA_SCRIPTS 2 seções novas (`scripts/reserva.py` + `scripts/consulta_quant.py`), 8 scripts movidos para `_validados/`.

**Status global do esforço de migração (atualizado 2026-05-24 v7):**
- **1/8 skills WRITE MATURADA** (skill 1 `ajustando-quant-odoo`)
- **5/8 skills WRITE mín viável** (skill 2 `transferindo-interno-odoo` 🟡 + skill 2.4 `operando-reservas-odoo` 🟡 **+2 átomos v7** + skill 5 `operando-picking-odoo` 🟡 + skill 4 `operando-mo-odoo` 🟡 + skill 6 `planejando-pre-etapa-odoo` 🟡)
- **1 skill READ ancillary mín viável** (skill 9 `consultando-quant-odoo` 🟡 **+2 átomos v7 — cross-ref reverso ML→quant via tupla G030**)
- **2/8 skills WRITE não iniciadas** (escriturando, faturando — este último DESBLOQUEADO pela ONDA 0.4 fechada em v3)
- **ONDA 0.4 ✅ FECHADA** em 2026-05-24 v3 (G019/G020 codificadas no `picking.py` + 8 testes; destrava Skill 8 faturando)
- **NOVO Fluxo 2.6** (v7): cobre gap arquitetural "tratar reserva ATIVA pré-transferência" — composição Skills 9+2.4+5+2 com 5 caminhos seguros (A=cancel/B=devolver/C=unreserve/D=outro lote/E=cirurgia órfã); regra inviolável no prompt do subagente.
- **NOVO Gotcha G030** (v7): `stock.move.line.quant_id` é COMPUTED `store: False` — filtro IGNORADO pelo Odoo; cross-ref via tupla `(product_id, lot_id, location_id, company_id)`.
- **15 scripts SUPERADOS** (em `_validados/`); ~90 scripts ad-hoc continuam VIVOS.
- **Baseline pytest: 229 verdes** (194 anterior + 19 Skill 9 query novos + 14 Skill 2.4 reserva novos + 2 a mais nos existing aleatórios).

**Próximo passo (escolha do usuário em sessão futura, pós-2026-05-24 v6):**
1. **Skill 8 (`faturando-odoo`)** — **DESBLOQUEADA** pela ONDA 0.4 fechada (G019/G020 codificadas + 8 testes). É a skill MACRO (NF→SEFAZ); requer cuidado especial — irreversível. Service `InventarioPipelineService` existe; falta capinagem + SKILL.md + CLI. ~6-8h.
2. **Skill 7 (`escriturando-odoo`)** — entrada IC + DFe. Depende de contrato estável de transfer (Skill 2 ✅) e picking (Skill 5 ✅). Caminho para fluxos 1.x (inter-company).
3. **Skill 6 extensões** (sessão futura): C9 do `09b_executar_pre_etapa.py` (capina para `orchestrators/pre_etapa_executor.py` macro C3) quando padrão for usado novamente; smoke `--confirmar` real em PROD do `--modo planejar` (com inputs reais dos scripts 01+02); validação `listar-onda`/`aprovar-onda` em PG local com tabela migrada.
4. **Fluxos compostos da Skill 2** — escrever folhas filhas (`2.2.D010`, `2.2.D012`, `2.2.D013`) para cobrir orquestradores de planilha. Implementar somente se padrão se repetir com 2+ casos reais cada.
5. **Auditoria G031** (pendência §9.7 v4): `grep -rn "LOTES_MIGRACAO_POR_COMPANY\[" app/ scripts/` em sessão futura — confirmar zero callers reais (já confirmado em CR3 via grep, reauditar periodicamente).
6. **Skill 5 — extensões**: `criar_picking_interno` ou `alterar_lote_no_picking` se surgir demanda real ad-hoc.
7. **Skill 4 — extensões**: `mrp_unbuild` (skill futura `mrp-unbuild-odoo` se padrão 3.1.c repetir 2+ casos); `alterar_mo` como fluxo cross-skill 3.2 se padrão repetir.
8. **Skill 2 — extensões**: arg `--lot-id-origem`/`--lot-id-destino` na CLI (cobre `padronizar_migracao` sem ambiguidade).
9. **Skill 3 / Skill 9 — completar átomos previstos** conforme demanda real (não especulativo).
10. **Demandas reais** do dia-a-dia continuam orientando — cada caso real revela novos átomos necessários (provado em 5 sessões consecutivas: skills 1/2.4/9/2/5/4 nasceram/maturaram).

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
| 2 | `transferindo-interno-odoo` 🟡 (mín viável + MODO C PROD) | **NOVA 2026-05-24 v2 / MODO C v4** — 52 pytest verdes, 3 modos (lote→lote / loc→loc / **para-indisponivel atômico**), delega `ajustar_quant`×2 com `delta_esperado` propagado; 2 scripts SUPERADOS, 14+ orquestradores VIVOS; **1 execução `--confirmar` PROD validada (4.319 un em 23s pós-incidente G031 + fix)** |
| 3 | `operando-reservas-odoo` 🟡 (mín viável) · `operando-mo-odoo` 🟡 (mín viável NOVA 2026-05-24 v5 — 29 pytest, guard G-MO-01 furo contábil, idempotência action_cancel) · `operando-picking-odoo` 🟡 (mín viável NOVA 2026-05-24 v3) | cancelamentos/limpeza (gaps); skill 3 ANTECIPADA por demanda real 2026-05-23; skill 5 capina StockPickingService + atomo NOVO `devolver` (idempotente); FECHA invariante G019/G020 (pre-req ONDA 0.4); skill 4 criada do zero (sem service legado) |
| 4 | `planejando-pre-etapa-odoo` 🟡 (mín viável NOVA 2026-05-24 v6 — 19 pytest verdes, 4 modos planejar/propor/listar/aprovar; capina 03b+04b; 09b executor mantém VIVO como C3 macro pendente) | planner D007 (READ Odoo + WRITE banco local); isolado |
| 5 | `escriturando-odoo` ⬜ | entrada IC + DFe; depende de contrato estável de transfer |
| 6 | `faturando-odoo` ⬜ | **ÚLTIMO** — macro perigoso (SEFAZ); ~~exige ONDA 0.4 (G019/G020) fechada~~ ONDA 0.4 ✅ fechada 2026-05-24 v3 |
| ANCILLARY | `consultando-quant-odoo` 🟡 | READ-only AO VIVO; nasceu sob demanda (auditoria pós-WRITE) — não bloqueia outras |

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

## SKILL 2 — `transferindo-interno-odoo`  🟡 (mín viável + MODO C PROD + 52 pytest verdes)
- **Objeto:** transferência interna intra-empresa | **Camada:** C2 | **Service:** [`app/odoo/estoque/scripts/transfer.py`](scripts/transfer.py) (StockInternalTransferService — API v1 preservada + API v2 que delega a `ajustar_quant` 2x + helpers MIGRAÇÃO + `transferir_entre_locations`)
- **Scripts-fonte:** 10 (SUPERADO 2026-05-24), padronizar_migracao (SUPERADO 2026-05-24 com limitação 2-grafias), 13_transferencia_migracao_fb, 15_transferencia_para_migracao, 15r, 15_transferir_preprod, 17_transferir_preprod_lf, substituir_lote_205030410, transferir_lote, transferir_local_pasta22, recuperar_aumentos_falhos, mover_migracao_para_indisponivel, ajuste_fb_cd_indisponivel, transferir_indisp_para_estoque_p15_cd, relotar_migracao_para_lotes_fb, transferir_fluxo_c (COM-BUG G-TRANSFER-01), executar_fluxo_b_vivas (COM-BUG), consolidar_lote_104000015_sal_fb.
- **Semânticas (explícitas via arg, nunca inferir):** D010 sinal diff_qtd · D012 delta · D013 De-Para+wildcard (vivem nos orquestradores externos; a skill cobre o ÁTOMO).
- **Gotchas-invariante codificados (10):** G021 (lot_id empresa errada — filtro company_id em TODA busca de lote), G022 (2 lotes MIGRACAO/produto — wildcard 3 grafias + maior saldo na loc), G027 (reserved_quantity stale — `--resetar-reserva-origem` opcional), G028 (consolidar_move_lines — herdado), G002 (lot.name `=` instável — herdado), G_proxy_vazio (P-15/05 = literal + sem lote), G-TRANSFER-01 (criar_se_nao_existe retorna tuple), action_apply_inventory infla quant negativo (herdado), delta_esperado propagado a CADA passo (regra inviolável 11), G_clamp_arred (TOL=0.001).
- **Átomos implementados (4):** `transferir_entre_lotes` (v1 preservada — 12 testes originais), `transferir_entre_lotes_v2` (v2 nova, delega `ajustar_quant`×2 com `delta_esperado` propagado), `transferir_entre_locations` (mesmo lote, 2 locs), `transferir_quantidade_para_lote_v2` (wrapper v2 com criar destino).
- **Helpers (4):** `is_migracao` (3 variantes), `_lotes_migracao_ids` (G021), `_melhor_lote_migracao_na_loc` (G022), `resolver_lote_origem/destino` (públicos).
- **Checkpoints:** C1 ✅ (18 scripts lidos integral — 9 por mim + 7 por subagente Explore + 2 do main) · C2 ✅ (service `transfer.py` movido + estendido; 33 testes pytest verdes) · C3 ✅ (contrato em SKILL.md) · C4 ✅ ([`SKILL.md`](../../.claude/skills/transferindo-interno-odoo/SKILL.md)) · C5 ✅ ([`transferir.py`](../../.claude/skills/transferindo-interno-odoo/scripts/transferir.py)) · **C6 ✅** (3 casos dry-run PROD: lote→lote OK; padronizar OK com limitação; loc→loc OK detalhado) · C7 ✅ (subagente + ROUTING_SKILLS + tool_skill_mapper `Estoque Odoo (Write)` + CLAUDE.md raiz) · C8 ✅ ([fluxo 2.2](fluxos/2.2-realocar-saldo.md) com 8 sub-casos) · C9 ✅ (2 scripts movidos: 10_emergenciais + padronizar_migracao; sys.path corrigido parents[2]→parents[4]; outros 16+ permanecem VIVOS — operação viva) · C10 ✅ (MAPA_SCRIPTS + este ROADMAP atualizados)
- **Status global da skill 2: 🟡 mín viável** (2026-05-24 — átomo composto pronto; 0 execuções `--confirmar` em PROD; fluxos compostos para orquestradores de planilha pendentes; limitação `--lot-id` documentada). [VALIDACAO.md](../../scripts/inventario_2026_05/_validados/transferindo-interno-odoo/VALIDACAO.md).

## SKILL 3 — `operando-reservas-odoo`  🟡 (mínimo viável + write real validado)
- **Objeto:** stock.move.line + stock.picking + stock.quant (residual) | **Camada:** C1/C2 | **Service:** [`reserva.py`](scripts/reserva.py) (StockReservaService — 3 átomos)
- **Scripts-fonte (MAPA_SCRIPTS):** SUPERADOS → remover_reservas_saida, cancelar_reservas_migracao, limpar_reservas_fantasma (movidos para `_validados/operando-reservas-odoo/` em 2026-05-23).
- **Gotchas-invariante codificados (5):** G024 (`reserved_uom_qty` inexistente Odoo 16/17), G025 (Odoo CIEL IT: `stock.move._action_cancel` é PRIVADO via XML-RPC), G026 (MO `to_close/done` tem `picked=True` — não mexer), G027 (`reserved_quantity` interno SEMPRE vem de saída — zerar residual stale é seguro), G028 (batch 50 com fallback individual).
- **Átomos implementados (3):** `cancelar_moves_orfaos(picking_id, ml_ids, moves_writes)` (cirurgia), `cancelar_picking_inteiro(picking_id)` (action_cancel cascade), `zerar_reserved_residual(quant_ids)` (cleanup pós-unlink — descoberta 2026-05-23).
- **Átomos previstos:** `unreserve_picking`, `unreserve_mo(reassign=)`, `find_orphan_mls` — implementar conforme demanda.
- **Checkpoints:** C1 ✅ (4 scripts-fonte lidos integral + probes Odoo 17) · C2 ✅ ([`reserva.py`](scripts/reserva.py)) · C3 ✅ (contrato em SKILL.md) · C4 ✅ (`SKILL.md`) · C5 ✅ ([`operar_reserva.py`](../../.claude/skills/operando-reservas-odoo/scripts/operar_reserva.py)) · **C6 ✅** (write real 2026-05-23 — 6 pickings/15 quants em 3,6s + 15 quants `zerar_reserved_residual` em 62ms) · C7 ✅ (subagente + ROUTING_SKILLS + tool_skill_mapper) · C8 ✅ ([fluxo 2.4](fluxos/2.4-cancelar-reserva-orfa.md)) · C9 ✅ (3 scripts movidos `parents[2]→parents[4]`) · C10 ✅ (MAPA_SCRIPTS seção `scripts/reserva.py`)
- **Status global da skill 3: 🟡 — mínimo viável maturado, demais átomos previstos** (2026-05-23 — caso real "15 MLs órfãs em 6 pickings pós-`--resetar-reserva`" resolvido ponta-a-ponta; gotcha descoberto: `--resetar-reserva` + unlink ML gera `reserved` negativo, exige `zerar_reserved_residual` após; documentado em SKILL.md e [`VALIDACAO.md`](../../scripts/inventario_2026_05/_validados/operando-reservas-odoo/VALIDACAO.md)).

## SKILL 4 — `operando-mo-odoo`  🟡 (mín viável + 29 pytest verdes + 4 dry-run PROD)
- **Objeto:** mrp.production | **Camada:** C2 | **Service:** [`app/odoo/estoque/scripts/mo.py`](scripts/mo.py) (StockMOService — criado do zero 2026-05-24 v5; shim preventivo em `services/stock_mo_service.py`)
- **Scripts-fonte:** cancelar_mos (SUPERADO 2026-05-24 v5), 14_cancelar_mos_antigas_fb (SUPERADO 2026-05-24 v5).
- **Gotchas-invariante codificados (4):** G-MO-01 (consumo>0=furo contábil — bloqueia cancelamento default; CLI V1 NÃO expõe forcar_consumo; operador deve usar mrp.unbuild via fluxo cross-skill), G-MO-02 (manual_consumption não reserva via action_assign — NÃO relevante para cancelar, relevante p/ criar/alterar não cobertos V1), G-MO-03 (componente em local errado — não relevante para cancelar), G-MO-04 (picked=True em to_close/done herdado de Skill 2.4 G026 — action_cancel é seguro). G019-like (re-le state pós action_cancel; FALHA_STATE_INESPERADO se state != cancel).
- **Átomos implementados (2):** `cancelar_mo(mo_id, motivo, forcar_consumo, consumo_total, dry_run)` — wrapper sobre `mrp.production.action_cancel` + guard G-MO-01 + G019-like re-le state + idempotência state=cancel = NOOP; `cancelar_mos_em_massa(criterio, max_n, motivo, dry_run)` — composição com filtros (create_de/ate, states, empresas, consumo) + medir_consumo batch (perf) + FIFO por create_date.
- **Helper:** `medir_consumo_mo(mo_ids)` — soma `stock.move.quantity` (state != 'cancel') por raw_material_production_id (chunks 200, TOL=0.0001).
- **Átomos previstos (sem demanda):** `criar_mo` (sem demanda real isolada — pipeline cria via Odoo); `alterar_mo` (caso real existe — ver [[mo_componente_local_consumo]] — mas é fluxo cross-skill Skill 2 + write stock.move, NÃO átomo). `mrp_unbuild` (procedimento manual documentado em [[reaproveitar-semiacabado-orfao-mo-cancelada]] §3; skill futura se padrão repetir).
- **Checkpoints:** C1 ✅ (2 scripts-fonte lidos integral + investigação AO VIVO via `/tmp/investigar_mos_skill4.py`: 10.000 MOs FB / 17 CD / 3367 LF; estrutura mrp.production validada; idempotência action_cancel confirmada em FB/OP/BALDE/00009 id=4192) · C2 ✅ ([`scripts/mo.py`](scripts/mo.py) novo; **29 testes pytest verdes** cobrindo todos os cenários — caminho feliz, NOOP idempotente, guard G-MO-01 default + bypass, state='done', state inesperado, exceção, dry-run, helpers, batch com filtros/limite/FIFO) · C3 ✅ (contrato 1 átomo único + composição em SKILL.md) · C4 ✅ ([`SKILL.md`](../../.claude/skills/operando-mo-odoo/SKILL.md)) · C5 ✅ ([`operar_mo.py`](../../.claude/skills/operando-mo-odoo/scripts/operar_mo.py) — CLI single OU batch, --dry-run default, exit codes 0/1/2/4) · **C6 ✅** (4 casos dry-run PROD 2026-05-24 v5: NOOP idempotente, DRY_RUN_OK sem consumo, FALHA_FURO_CONTABIL bloqueia consumo=1410.05, batch FB ate 2025-06 com filtro consumo zero; log em `/tmp/log_skill4_C6_validacao_dry_run.json`) · C7 ✅ (subagente `gestor-estoque-odoo` adicionou skill + galho 3.1 com [folha 3.1]; ROUTING_SKILLS 47 invocaveis + 15 Skills Odoo + triggers MO; tool_skill_mapper `'operando-mo-odoo': 'Estoque Odoo (Write)'`; CLAUDE.md raiz + app/odoo/CLAUDE.md atualizados) · C8 ✅ ([fluxo 3.1](fluxos/3.1-cancelar-mo.md) com 3 sub-casos a/b/c; 3.1.c DELEGADO para mrp.unbuild cross-skill) · C9 ✅ (2 scripts SUPERADOS em `_validados/operando-mo-odoo/`: `cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` + VALIDACAO.md; sys.path corrigido parents[2]→parents[4]; museum vivo validado via import) · C10 ✅ (MAPA_SCRIPTS atualizado seção `scripts/mo.py` + README fluxos atualizado).
- **Status global da skill 4: 🟡 mín viável** (2026-05-24 v5 — átomos prontos; 0 execuções `--confirmar` em PROD nesta sessão; pattern validado em PROD em sessão anterior 2026-05-20 via scripts-fonte: 120 MOs zumbi canceladas).

## SKILL 5 — `operando-picking-odoo`  🟡 (mín viável + 42 pytest verdes + 6 dry-run PROD)
- **Objeto:** stock.picking | **Camada:** C2 | **Service:** [`app/odoo/estoque/scripts/picking.py`](scripts/picking.py) (StockPickingService — capinado de `services/` em 2026-05-24 v3, shim preservado)
- **Scripts-fonte:** 16_cancelar_pickings_fantasmas (SUPERADO 2026-05-24 v3); pipeline-only e cross-skill permanecem VIVOS (executar_fluxo_b_vivas, teste_210030325_lf, fat_lf_05_executar_clean, 09_executar_onda1_bulk, fat_lf_cleanup, substituir_lote_205030410_fb).
- **Gotchas-invariante codificados (4):** G019 (validar() re-le state pós-button_validate; raise se != 'done'; trata marshal None), G020 (liberar_faturamento valida pre-cond state=done — usado por Skill 8 pipeline, NÃO exposto na CLI da Skill 5), G023 (consolidar_move_lines opcional em validar(linhas_esperadas=)), G011 (preencher_qty_done existe mas é PRÉ-REQUISITO de caller — pipeline preenche antes).
- **Átomos implementados (3):** `cancelar(picking_id, motivo)` — wrapper sobre `action_cancel`; `validar(picking_id, linhas_esperadas=None)` — `button_validate` + G019 invariante + G023 opcional; `devolver(picking_id)` — NOVO (wizard `stock.return.picking` + `create_returns` + valida; idempotente via `origin ilike "Devolução de NAME"`).
- **Átomos previstos (sem demanda):** `alterar_lote_no_picking` (caso `substituir_lote_205030410` é fluxo cross-skill, não átomo); `criar_picking_interno` (sem demanda ad-hoc isolada — pipeline cria via `svc.criar_transferencia` existente).
- **Checkpoints:** C1 ✅ (4 scripts-fonte minerados integral: 16_cancelar_pickings_fantasmas, fat_lf_cleanup, substituir_lote_205030410, picking_service.py existente; + 4 docs gotchas G011/G019/G020/G023) · C2 ✅ ([`app/odoo/estoque/scripts/picking.py`](scripts/picking.py) capinado + método novo `devolver`; **42 testes pytest verdes** — 19 originais + 16 novos cobrindo G023/ajustar_qty_done/validar-com-linhas + 7 cobrindo `devolver`) · C3 ✅ (contrato 3 átomos em SKILL.md) · C4 ✅ ([`SKILL.md`](../../.claude/skills/operando-picking-odoo/SKILL.md)) · C5 ✅ ([`operar_picking.py`](../../.claude/skills/operando-picking-odoo/scripts/operar_picking.py) — 3 modos `--modo cancelar/validar/devolver`, `--dry-run` default, exit codes 0/1/2/4) · **C6 ✅** (6 casos dry-run PROD 2026-05-24 v3: cancelar/assigned ✅, validar/assigned ✅, devolver/done ✅, cancelar/done=FALHA_STATE_DONE ✅, cancelar/cancel=NOOP ✅, devolver/assigned=FALHA_STATE_NAO_DONE ✅; 100% bate) · C7 ✅ (subagente `gestor-estoque-odoo` adicionou skill + árvore 2.5; ROUTING_SKILLS 46 invocaveis + 14 Skills Odoo; tool_skill_mapper `'operando-picking-odoo': 'Estoque Odoo (Write)'`) · C8 ✅ ([fluxo 2.5](fluxos/2.5-cancelar-validar-devolver-picking.md) com 3 sub-casos a/b/c) · C9 ✅ (1 script SUPERADO em `_validados/operando-picking-odoo/`: `16_cancelar_pickings_fantasmas.py` + VALIDACAO.md; sys.path corrigido parents[2]→parents[4]) · C10 ✅ (MAPA_SCRIPTS atualizado).
- **Status global da skill 5: 🟡 mín viável** (2026-05-24 v3 — átomos prontos; 0 execuções `--confirmar` em PROD nesta sessão; **FECHOU ONDA 0.4** — invariante G019/G020 codificada no service + 8 testes pytest validando comportamento defensivo; destrava Skill 8 `faturando-odoo` que confiava na ABERTURA do gotcha).

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

## SKILL 8 — `faturando-odoo`  (SÓ SAÍDA — ÚLTIMO)  ⬜
- **Objeto:** NF saída→robô CIEL IT→SEFAZ | **Camada:** C3 (macro + etapas B→D) | **Service:** `InventarioPipelineService` 🟡 (macro, ~20 gotchas, falta manual)
- **PRÉ-REQUISITO:** ONDA 0.4 (G019/G020 fechados).
- **Scripts-fonte:** 09_executar_onda1_bulk (A-F), 09c_executar_onda2_fb_cd (transfer_only 19-37), fat_lf_02_carregar (TIPO→ação), fat_lf_04_executar (driver B-F), fat_lf_05_executar_clean (G028 reserva multi-lote), fat_lf_cleanup (return+cancel+reset), fat_lf_resume.sh (loop B→D SSL-resiliente), teste_210030325 (→ exemplo no fluxo).
- **Gotchas-invariante:** G004, G011, G016 (SSL), G019/G020 (fechar antes), quarteto fiscal G035/G017/G007/G018 (pré-flight cstat 225), G028.
- **Checkpoints:** C1–C10 ⬜

## SKILL 9 — `consultando-quant-odoo`  (READ ANCILLARY)  🟡
- **Objeto:** stock.quant (READ-only) ao vivo via XML-RPC | **Camada:** READ (sem WRITE) | **Service:** [`consulta_quant.py`](scripts/consulta_quant.py) (StockQuantQueryService — 2 átomos)
- **Origem:** nasceu da demanda de auditoria pós-WRITE (2026-05-23: "sobrou saldo em loc !=Indisponivel para os 104 produtos ajustados?"). NÃO faz parte da ordem bottom-up das skills WRITE — é skill ANCILLARY (suporte às outras).
- **Scripts-fonte minerados (parcial):** `monitor/1_baixar_estoques.py` (pattern de search batch), `auditoria/levantar_estoque_fora_principal.py` (classificação por usage+parent_path). Os ~35 outros READ legados (monitor/*, auditoria/comparar_sot_*, diff_*, relatorio_*, investiga_*) continuam VIVOS — átomos previstos cobrem subconjunto, demais permanecem ad-hoc.
- **Átomos implementados (2):** `listar_quants(cods, pids, empresas, pares_cod_empresa, locations_excluir, com_lote, only_principal, agregar)` (query versátil — 8 parâmetros) + `auditar_pares(pares_cod_empresa)` (helper de alto nível — classifica em zerado/so_indisp/com_saldo/sem_produto).
- **Átomos previstos:** `listar_move_lines`, `listar_pickings`, `find_orphan_mls(quant_ids)`, `snapshot_estoque_por_lote(empresa)`, `saldo_fora_principal(empresa)` — implementar conforme demanda.
- **Checkpoints:** C1 🟡 (mineração parcial — 2 scripts-fonte essenciais lidos; ~33 outros READ permanecem como referência) · C2 ✅ ([`consulta_quant.py`](scripts/consulta_quant.py)) · C3 ✅ (contrato em SKILL.md) · C4 ✅ (`SKILL.md`) · C5 ✅ ([`consultar_quants.py`](../../.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py)) · **C6 ✅** (dogfood 2026-05-23 — investigação 4856125 + auditoria 104 pares: `auditar_pares` retornou 17+46+39+2=104 ✓) · C7 ✅ (subagente READ direto + ROUTING_SKILLS + tool_skill_mapper `Estoque Odoo (Read)`/`Odoo`) · C8 ✅ ([fluxo 2.9](fluxos/2.9-consulta-quant-ao-vivo.md)) · C9 ⏸️ (decisão: NÃO mover scripts READ ainda — skill mínima cobre subconjunto; átomos previstos cobrirão mais cenários, scripts ad-hoc continuam VIVOS) · C10 ✅ (MAPA_SCRIPTS seção `scripts/consulta_quant.py`)
- **Status global da skill 9: 🟡 — READ-only mínimo viável, ancillary** (2026-05-23 — pattern de "auditar saldo restante" cristalizado em `auditar_pares`; corrige erro de produto-cartesiano (cods × empresas) presente na 1ª query inline; case real "sobrou saldo dos 104 produtos?" → 17 zerados + 46 só_indisp + 39 com_saldo + 2 sem_produto = 104 ✓).

---

## NÃO VIRAM SKILL (registro)
- **Leitura/diff/SOT batch** (~33 scripts restantes: `monitor/2,3,4`, `01_extrair_estoque_odoo`, `08_extrair_pos_execucao`, `comparar_sot_*`, `confronto_4_fontes`, `diff_*`, `relatorio_*`, `investiga_*`, etc.) → continuam como scripts ad-hoc operação viva. A skill 9 cobre o pattern essencial de busca `stock.quant`; casos específicos (snapshot CSV batch, classificação por usage, cross-source com Render local) são átomos PREVISTOS na skill 9 — implementar conforme demanda. **Justificativa do C9 ⏸️ da skill 9:** mover scripts READ sem cobertura completa quebra fluxos que dependem deles (operação viva).
- **JÁ-MORTO** (discovery F0: 00-00e, auditoria/investiga_*, baixar_xml_preview_626032, debug_sefaz_608607) → arquivar em `_historico/`.
- **`operando-lote`** (stock.lot) = **utils** em `app/odoo/estoque/_utils.py` (chamado por skills 1/2).

---

## LEGENDA
⬜ não iniciado · 🟡 parcial · ✅ concluído · C# = checkpoint do checklist fixo.
Atualizar status do checkpoint e da skill A CADA avanço (este arquivo é o progresso vivo).
