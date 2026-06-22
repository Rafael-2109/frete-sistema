# app/odoo/estoque — Operações de Escrita de Estoque no Odoo

**Status:** EM CONSTRUÇÃO (ONDA 0 concluída 2026-05-22; ONDA 0.4 ✅ fechada 2026-05-24 v3 — G019/G020 codificadas no service; **Skill 2 `transferindo-interno-odoo` ✅ MATURADA**; **Skill 5 `operando-picking-odoo` 🟡 ESTENDIDA v15a + F1 IDEMPOTENCIA v15c** — 3 atomos inter-company; **Skill 6 `planejando-pre-etapa-odoo` 🟡 mín viável COMPLETA v9**; **Skill 7 `escriturando-odoo` 🟡 mín viável V1 LIVE v17.5** — antipadrao V1 STRICT documentado para refator v19+; **Skill 8 `faturando-odoo` 🟡 PIPELINE COMPLETO A-F LIVE + RECOVERY v18** — `app/odoo/estoque/orchestrators/inventario_pipeline.py` (renomeado de `faturamento_pipeline.py` em v27+; stub removido v28+) compoe Skill 5 + Skill 2 v2 + Playwright SEFAZ + atomo Skill 7 + atomo Skill 5 entrada destino. **v18 (2026-05-26): RECOVERY `executar_pipeline_resume` + SKILL.md Skill 8 + G037 NOVO**. Recovery substitui scripts shell `fat_lf_resume.sh` + `fat_lf_resume_entrada.sh` por modo CLI `--modo resume --apenas-etapa B/C/D/E/F` (loop iterativo + detector_stagnation + max_iter; 8 pytest mockados novos). SKILL.md `.claude/skills/faturando-odoo/SKILL.md` criada com 4 receitas + secao ANTIPADROES DETECTADOS V17.5 + checklist expansao v19+. G037 (NOVO em `docs/inventario-2026-05/02-gotchas/G037-operacao-nao-cadastrada-exige-cfop-explicito.md`): MATRIZ_INTERCOMPANY[acao]['cfop_esperado'] tem USO PRATICO (nao apenas log). 1 code-reviewer paralelo (4 findings — 1 CRIT + 3 HIGH aplicados: F1 contador inclui F5x_FALHA, F3 `--timeout-iter` lying parameter clarificado, F2+F4 doc adicional SKILL.md). **521 pytest verdes** (513 baseline v17.5 + 8 net v18). Smokes dry-run PROD: resume B/D/E/F + FALHA_USO log em `/tmp/log_skill8_smokes_v18_*.json`. | **Snapshot deste header:** v18 (2026-05-26) — ESTADO VIVO nas tabelas §6 (catalogo de skills) + changelog por versao abaixo; o corpo evoluiu ate ~v30 / D-V30-1 (2026-06-02). NAO tratar este header como estado atual.
**Audiência:** Claude Code (dev) + agente web. Doc **machine-first** — contratos e regras.

> **Rename histórico:** `faturamento_pipeline.py` → `inventario_pipeline.py` (v27+ S3; stub removido v28+ S6.b). Menções a `faturamento_pipeline.py` em entradas de changelog datadas abaixo referem-se ao MESMO arquivo (nome da época) — hoje é `orchestrators/inventario_pipeline.py`. Exceção: o arquivo de teste `test_faturamento_pipeline_orchestrator.py` mantém o nome original.

Pacote-destino da consolidação dos ~105 scripts ad-hoc de inventário (`scripts/inventario_2026_05/`) em **átomos versáteis e auto-seguros** (services), consumidos por **skills** (`.claude/skills/`) + o subagente **`gestor-estoque-odoo`** (`.claude/agents/`). Este CLAUDE.md é a **constituição** da arquitetura.

> Roadmap da migração (transitório): `app/odoo/estoque/ROADMAP_SKILLS.md`.
> Mineração dos 105 scripts (transitória, some quando a migração fechar): `docs/inventario-2026-05/consolidacao/{MAPA_ASSUNTOS,MAPA_SCRIPTS,PLANO_MIGRACAO}.md`.

---

## 0. Por que existe

Os 105 scripts ad-hoc nasceram de "não procurar → recriar" sob pressão. Objetivo: **nunca mais criar script ad-hoc** para operar o Odoo. Toda escrita passa a ser disparada via **skills-átomos** compostas em **fluxos**, orquestradas pelo `gestor-estoque-odoo`. Executor = **Claude Code E agente web**.

## 1. PRINCÍPIO FUNDADOR (inviolável)

> Toda operação de escrita no Odoo é um **átomo versátil e auto-seguro**:
> - **versátil** — serve N fluxos variando args; nunca assume um fluxo específico;
> - **auto-seguro** — gotchas do seu objeto codificados DENTRO como invariante (validador/guard/retry), não na memória do agente;
> - **2 modos** — `--dry-run` (default seguro: calcula e mostra o plano, não escreve) → `--confirmar` (executa).
>
> Os **fluxos** que compõem átomos vivem em **referências navegáveis** (`fluxos/`, árvore progressive disclosure), não em código nem no prompt.
>
> O subagente **pesquisa premissas → navega a árvore → compõe átomos → confirma**. NUNCA recompõe lógica perigosa do zero, NUNCA inventa SQL/XML-RPC, NUNCA cria script ad-hoc.

### 1.1 INVARIANTE: 1 SKILL = 1 OBJETO ODOO. SEM EXCEÇÃO. (reforçado v18 Fase 0)

> Uma skill L2 atômica tem **EXATAMENTE 1 OBJETO Odoo principal**. Quando o caso de negócio precisa de 2+ objetos, é **FLUXO L3** (Markdown em `fluxos/`), NÃO uma skill nova.
>
> **Exemplos corretos**:
> - `ajustando-quant-odoo` = stock.quant (1 objeto) ✓
> - `operando-picking-odoo` = stock.picking (1 objeto) ✓
> - `escriturando-odoo` = account.move + DFe **APENAS PARA ENTRADA** (objeto principal: account.move da entrada; DFe é meio para chegar nele) ✓
>
> **Exemplo correto de COMPOSIÇÃO** (NÃO é skill nova):
> - "Faturar + escriturar uma transferência completa" = compõe Skill 8 SAÍDA + Skill 7 ENTRADA = **FLUXO L3 1.3-transferencia-completa.md**.
>
> **Sinais de alerta**: se você está prestes a criar skill que toca `account.move` + `stock.picking` + Playwright SEFAZ + `RecebimentoLf` — PARE. Isso é orchestrator C3 (L1 macro), não skill L2. Vai para `orchestrators/`, NÃO entra no catálogo §6 de skills L2.

## 2. AS 5 CAMADAS

```
[L4] gestor-estoque-odoo (subagente WRITE)  → .claude/agents/gestor-estoque-odoo.md
        pesquisa premissas · navega árvore · compõe · mostra plano · confirma
[L3] REFERÊNCIAS de fluxo  → app/odoo/estoque/fluxos/ (árvore 1/2/3…)
        cada FOLHA = premissas + sequência de átomos + args + exemplo + gotchas
[L2] SKILLS = átomos versáteis por objeto  → .claude/skills/<skill>/
        SKILL.md (contrato + receitas) + scripts/ (--dry-run + --confirmar)
[L1] SERVICES / primitivas  → app/odoo/estoque/scripts/ (C1/C2) e orchestrators/ (C3)
        gotchas codificados, testados (pytest)
[L0] CONSTANTS  → app/odoo/constants/  (locations · operacoes_fiscais · picking_types · ids_diversos)
```
Dependência: cada camada só conhece a de baixo. L4 nunca pula direto para L1 sem passar por uma skill (L2).

## 3. CONTRATO DE ÁTOMO COMPONÍVEL (o coração)

Para muitos fluxos comporem poucos átomos, cada skill DECLARA um contrato (bloco obrigatório na `SKILL.md`):
```
## Contrato
- objeto:        <model Odoo principal> (ex: stock.quant)
- input:         <args nomeados>
- output:        <dict estruturado p/ encadear>
- pré-condições: <estado exigido do Odoo>
- pós-condições: <estado garantido>
- gotchas-invariante: <lista que o átomo trata sozinho>
- modos:         --dry-run (default) → --confirmar
```
**Composição (pipe):** o `output` de um átomo alimenta o `input` do próximo. **Regra de ouro:** o átomo NUNCA embute outro fluxo. `faturando-odoo` SÓ fatura (saída); `escriturando-odoo` SÓ escritura (entrada). Quem une é o FLUXO (L3).

### 3.1 ORCHESTRATOR C3 NÃO É SKILL (reforçado v18 Fase 0)

> Skills L2 são átomos com **1 objeto Odoo**. Quando um caso de negócio exige composição (SEFAZ irreversível, recovery iterativo, multi-step com checkpoint), surge um **orchestrator C3 macro** em `orchestrators/`. **Orchestrator C3 NÃO É skill L2**:
>
> - Mora em `app/odoo/estoque/orchestrators/`, NÃO em `.claude/skills/`
> - Aparece na **Tabela 2 do catálogo §6** (Orchestrators C3), NÃO na **Tabela 1** (Skills L2 atômicas)
> - O entry-point externo via SKILL.md pode existir (ex.: `.claude/skills/faturando-odoo/SKILL.md`) — mas isso é **FACHADA** apontando para o orchestrator; o orchestrator continua sendo C3 macro, não skill atômica.
> - O orchestrator macro **COMPÕE skills L2 chamando-as** — mas a composição correta passa por **FLUXOS L3** quando 2+ skills L2 estão envolvidas em sequência inteligente (não loop trivial).
>
> **Anti-padrão histórico (v17→v17.5→v18)**: catálogo §6 antigo listou orchestrators C3 (faturando-odoo, escriturando-odoo, planejando-pre-etapa-odoo) na MESMA tabela das skills L2 atômicas. Isso legitimou que orchestrators chamassem outras skills INLINE (violação §6 antipadrão 3). Corrigido v18 Fase 0 com **3 tabelas distintas** no §6.

### 🚨 ARMADILHA SUPERADA v17.5 — "atomo NUNCA embute outro fluxo" foi violado em v17 (custou 1 sessão para corrigir)

**O que aconteceu**: v17 implementou `executar_etapa_e` do orchestrator `faturando-odoo` (Skill 8) **inline** com ~420 LOC criando `RecebimentoLf` + agregação de lotes + invocação do service externo `RecebimentoLfOdooService`. Isso é **logicamente uma operação de ENTRADA** (escriturando) embutida dentro do orchestrator de SAÍDA (faturando). Constituição §6 violada.

**Por que aconteceu**: o orchestrator "podia" tecnicamente fazer (acesso ao DB + Odoo). A logica era complexa (~420 LOC). Foi mais rápido escrever inline do que criar uma skill nova. **MAS** isso acoplou Skill 8 ao service externo `RecebimentoLfOdooService` (4562 LOC, 37 etapas, NÃO MEXER), tornou o orchestrator inflado, dificultou teste isolado, e violou o invariante "atomo = 1 objeto + 1 responsabilidade".

**O que custou**: sessão v17.5 inteira para:
1. Criar Skill 7 `escriturando-odoo` dedicada (~500 LOC service + SKILL.md + 11 pytest)
2. REVERT 420 LOC do orchestrator → ~180 LOC delegando atomo
3. Migrar 4 testes inline + adicionar 2 novos
4. Aplicar 3 fixes de code-review pós-revert

**Como evitar (regra inviolável)**: ao implementar qualquer composição no orchestrator Skill 8 que envolva **criar registros locais + invocar service externo + agregar dados**, PARE e PERGUNTE:
- "Esta lógica deveria ser atomo de outra skill?" (cria + invoca svc externo = SIM, provavelmente é C3 macro)
- "Que skill seria responsável por isso?" (escriturando-odoo? recebimento-fisico-odoo? operando-mo-odoo?)
- "A skill existe?" Se SIM, usar. Se NÃO, AVISAR Rafael ANTES de implementar inline.

**Padrão correto do orchestrator** (Skill 8 pos-v17.5): orchestrator faz apenas
1. **Filtro** (filtrar ajustes elegíveis por ETAPA)
2. **Agrupamento** (por invoice_id ou direção)
3. **Loop** (sequencial ou paralelo)
4. **Invocação de atomo** (Skill 5 / Skill 7 / Skill 2)
5. **Mapeamento de status** (atomo retorna `CRIADO|RETOMADO|PARCIAL|FALHA` → orchestrator agrega contadores)

**NUNCA** orchestrator faz: `db.session.add(NovoModelo(...))`, `svc_externo = ServiceLF()`, `for ajuste in ajs: agg[(pid, lote)] += qty`. Isso é trabalho de atomo.

## 4. PILAR: fluxos >> skills

Poucos átomos (~8, estáveis) ⟷ MUITOS fluxos (dezenas, crescem). Regras:
1. **Átomo genérico e estável.** Caso de negócio novo = nova folha de fluxo, NÃO skill nova. Caso "não cabe" nos args → avaliar arg faltante (estender retrocompatível) antes de criar átomo.
2. **Inteligência de negócio vive nos fluxos (L3)**, não nas skills (L2) nem no prompt (L4).
3. **Proibido** 1-skill-por-fluxo (explosão combinatória).

## 5. ÁRVORE DE FLUXOS vs PROMPT ENXUTO (progressive disclosure)

O prompt do subagente (L4) carrega só a **árvore de DECISÃO** (galhos), sem citar skills. Ao descer num ramo, carrega a **folha sob demanda** (`fluxos/<id>-<slug>.md`). Convenção e formato da folha: `app/odoo/estoque/fluxos/README.md`.

## 6. CATÁLOGO (3 TABELAS — Skills L2 atômicas · Orchestrators C3 · Fluxos L3)

> Reorganizado v18 Fase 0 (era 1 tabela só "Skills WRITE 8" misturando átomos L2 com orchestrators C3 macro — origem dos antipadrões §6.5).

### Tabela 1 — Skills L2 ATÔMICAS (1 objeto Odoo cada — entram no catálogo de skills do agente)

| Skill | Objeto Odoo | Service base (L1) | Camada | Status |
|-------|-------------|-------------------|--------|--------|
| `ajustando-quant-odoo` | stock.quant | `scripts/quant.py` (StockQuantAdjustmentService) | C1 | ✅ **MATURADA** (100 ajustes em prod 2026-05-23) |
| `transferindo-interno-odoo` | transferência interna intra-empresa — **4 modos atômicos** (v21+): A lote→lote mesma loc / B loc→loc mesmo lote / C MIGRAÇÃO↔Indisp / **D loc+lote em 1 chamada (NOVO v21+)** | `scripts/transfer.py` (delega `ajustar_quant`×2 com `delta_esperado` propagado; G021/G022/G027) | C2 | 🟡 **44 pytest verdes** (33 v20+ + 11 net v21+ Skill 2 átomo NOVO `transferir_loc_e_lote`); 2 scripts SUPERADOS 2026-05-24; átomo D validado em PROD ETAPA 0 v21+ (250.330 SLEEVE + 1,8 CORANTE Indisp/MIGRAÇÃO → Estoque/P-15/05); **fix G040 v26+ (2026-05-29)** — `resolver_lote_*` consulta `product.tracking`: `P-15/05` é `stock.lot` REAL em produto `tracking='lot'` (antes virava proxy-vazio e evaporava saldo no MODO D); testes `*_p15_tracking_*` |
| `operando-mo-odoo` | mrp.production (cancelar V6 + concluir V7 2026-06-12; criar/alterar sem demanda) | [`scripts/mo.py`](scripts/mo.py) (StockMOService — guards G-MO-01 furo contabil + G-MO-05/06 anti-producao-fantasma no concluir) | C2 | 🟡 **57 pytest verdes** (concluir: dry-run PROD validado 2026-06-12; canary `--confirmar` pendente demanda natural) |
| `operando-reservas-odoo` | stock.move.line + stock.quant (residual) — opera reservas órfãs do picking | [`scripts/reserva.py`](scripts/reserva.py) (StockReservaService) | C1/C2 | 🟡 **mín viável** (3 átomos · 6 pickings/15 quants em prod) |
| `operando-picking-odoo` | stock.picking (cancelar/validar/devolver + 3 átomos inter-company v15a + 1 átomo NOVO v19+ `preencher_lotes_picking`; `criar_picking_entrada_destino_manual` 🛑 DEPRECATED v19+ AP2) | [`scripts/picking.py`](scripts/picking.py) (StockPickingService) | C2 | 🟡 **7 átomos LIVE v19+ + G-AUDIT-3 fix v22+** (70 pytest = 68 + 2 net v22+ idempotência cancel; G019/G020 fechada + G-AUDIT-3 codificada) |
| `escriturando-odoo` ✅ ABRANGENTE v19+ + G039 v23+ + B-V23-1/2 v23.5+ + F2a/F3c v25+ | account.move + DFe (entrada — escritura NF SEFAZ-OK no destino) | [`scripts/escrituracao.py`](scripts/escrituracao.py) (EscrituracaoLfService) | **HÍBRIDO** — V1 STRICT `criar_recebimento_orchestrado` (wrapper deprecado v20+) + **10 átomos ABRANGENTES**: 7 v19+ (`buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida` ⚡com fix B-V23-1 v23.5+ batch write dfe.line.company_id pós-poll⚡, `escriturar_dfe`, `gerar_po_from_dfe` ⚡com hook B-V23-2 v23.5+ batch write PO.line.account_id por company⚡, `preencher_po` ⚡com F3c v25+ aceita `l10n_br_tipo_pedido`⚡, `confirmar_po`, `criar_invoice_from_po`) + 2 v23+/v23.5+ (`garantir_purchase_team` G039 idempotente por user+company, `resolver_account_id_por_company` helper B-V23-2) + **1 v25+ NOVO `alinhar_dfe_lines_company`** (F2a — generaliza B-V23-1 p/ caminho A onde DFe vem via SEFAZ). Compostos via FLUXO L3 1.2.1/1.2.2 (caminho A/B) | 🟡 **ABRANGENTE LIVE v25+** (53 pytest = 11 V1 + 22 v19+ + 7 G039 + 3 B-V23-1 + 5 B-V23-2 átomo + 4 B-V23-2 hook + 4 F2a + 3 F3c v25+; PROD canary v23+: invoice ENTIN/2026/05/0055 posted; AP1+AP4 ✅; G039+B-V23-1+B-V23-2 ✅; F1-F4 v25+ aplicados pipeline) |
| `faturando-odoo` ✅ ATÔMICA v24+ (NOVA — AP6 refator) | account.move (NF SAIDA inter-company) | [`scripts/faturamento.py`](scripts/faturamento.py) (FaturamentoInvoiceService) | **ATÔMICA L2** — **5 átomos** espelhando Skill 7 ABRANGENTE v19+: `validar_invoice_constants` (READ pre-cond) · `liberar_faturamento` (delega Skill 5 LEGACY) · `polling_invoice` (delega Skill 5 LEGACY `aguardar_invoice_do_robo`) · `validar_invoice_pos_robo` (G029+G007+G034 via `_invoice_helpers`) · `transmitir_sefaz` (Playwright IRREVERSIVEL + D7 HARD_FAIL + D8.3 idempotência + CRITICAL-1 commit pós-SEFAZ + MED C-1/C-2 cstat). Composição via FLUXO L3 1.1.x (saida pura ⬜) ou via orchestrator C3 LEGACY `inventario_pipeline` (migração v25+) | 🟡 **ATÔMICA LIVE v24+** (28 pytest verdes; ~1345 LOC; AP6 RESOLVIDO PARCIAL — orchestrator C3 LEGACY ainda usa lógica inline em paralelo; migração para usar os 5 átomos planejada v25+ via opt-in `--usar-skill8-atomica-v25`) |
| `reclassificando-amls-odoo` (NOVA F2 #3 D8 2026-06-21) | account.move.line (reclassificação contábil em lote conta_origem→destino) | [`scripts/reclassificacao.py`](scripts/reclassificacao.py) (ReclassificacaoService) | **ATÔMICA L2** — `coletar_amls`/`agrupar_por_move`/`planejar`/`executar`/`validar_pos_write`. Irmã WRITE da READ `auditando-reclassificacao-odoo` (reusa `_dominio_saldo` + CONTADOR REAL `validar_lote`, não reimplementa). GUARD SEFAZ (l10n_br_situacao_nf in autorizado/excecao_autorizado/enviado → SKIP, espelha `_invoice_helpers.py`); ciclo button_draft→write account_id→action_post por move; INVARIANTE pós-post state==posted senão PARA batch; SÓ linhas da conta_origem; --user-id obrigatório | 🟡 **mín viável** (13 pytest service + 9 pytest CLI = 22 verdes FakeOdoo; **canary REAL PROD pendente** — validar 1 move da conta 26784 company 4 ANTES de --confirmar em prod) |

> **Nota Tabela 1**: estas são as únicas skills WRITE atômicas L2. Cada uma tem `.claude/skills/<nome>/SKILL.md` + scripts/. O subagente as conhece pela árvore de decisão.

### Tabela 2 — Skills READ ancillary L2 (sob demanda — complementam as WRITE)

| Skill | Objeto Odoo | Service base (L1) | Camada | Status |
|-------|-------------|-------------------|--------|--------|
| `consultando-quant-odoo` | stock.quant (read ao vivo via XML-RPC) — 3 modos: quants / move-lines / pickings | [`scripts/consulta_quant.py`](scripts/consulta_quant.py) (StockQuantQueryService) | READ | 🟡 **mín viável** (3 átomos · cross-ref ML→quant via tupla G030) |

### Tabela 3 — Orchestrators C3 macros (L1 — NÃO são skills L2)

> Compõem skills L2 para casos de negócio complexos (SEFAZ irreversível, recovery iterativo, multi-step com checkpoint). **NÃO aparecem no catálogo de skills do subagente**; ficam acessíveis via FACHADA SKILL.md ou diretamente em Python. Aceita `--dry-run` + `--confirmar` como qualquer átomo.

| Orchestrator | Composição | Service (L1) | Status | SKILL.md fachada |
|--------------|-----------|--------------|--------|------------------|
| `inventario_pipeline` (renomeado de `faturamento_pipeline` em v27+ S3 — stub alias REMOVIDO v28+ S6.b + cleanup DEPRECATED v16/v17.5 v28+ post-S7; AP6 RESOLVIDO PARCIAL v24+ + S1 opt-in v27+ + ETAPA E via FLUXO L3 v28+ S7) | Skill 2 v2 (ETAPA A) + Skill 5 átomos inter-company (ETAPA B) + Playwright SEFAZ (ETAPA D) + Skill 7 atomo V1 STRICT (ETAPA E legacy) + Skill 5 v15a deprecated (ETAPA F legacy) + **v19+ `executar_fluxo_l3_1_2_x`** + **F1-F4 v25+** + **v27+ S1 opt-in `--usar-skill8-atomica-v25`** (helpers `_executar_etapa_c_via_skill8_atomica` + `_executar_etapa_d_via_skill8_atomica` delegam aos atomos 3, 4 e 5 da Skill 8 ATOMICA L2) + **v28+ S7 helper `_executar_etapa_e_via_fluxo_l3`** (espelha helper F filtrando ACOES_ENTRADA_FB — destrava 4 ações X→FB/X→LF: PERDA_LF_FB + TRANSFERIR_CD_FB + DEV_LF_FB destino=FB; DEV_CD_LF destino=LF) | [`orchestrators/inventario_pipeline.py`](orchestrators/inventario_pipeline.py) (~6230 LOC) | 🟡 **PIPELINE A-F + RECOVERY + FLUXO L3 1.2.x LIVE v19+ + F1-F4 v25+ + S1 opt-in v27+ + S7 helper E v28+ + F1+F3 v29+ (agregado detecta PARCIAL + audit trail usuario via _passo)** (100 pytest = 96 v28+ + 4 F1 v29+; canary REAL PROD do opt-in pendente próxima INDUSTRIALIZACAO_FB_LF natural OU PERDA_LF_FB/TRANSFERIR_CD_FB/DEV_LF_FB/DEV_CD_LF para validar S7) | `.claude/skills/faturando-odoo/SKILL.md` (FACHADA atualizada v27+ S3 — paths apontam para inventario_pipeline) |
| `planejando-pre-etapa-odoo` (Skill 6) | Skills 1+2 via `executar_onda_pre_etapa` (READ Odoo + WRITE banco local + WRITE Odoo C3 macro) | [`scripts/pre_etapa.py`](scripts/pre_etapa.py) (planner) + [`orchestrators/pre_etapa_executor.py`](orchestrators/pre_etapa_executor.py) (executor) | 🟡 **mín viável COMPLETA v9** (42 pytest verdes; 5 modos: planejar/propor/listar/aprovar/executar-onda) | (sem fachada externa; CLI direto) |

> **Sinais de orchestrator C3 (vs skill L2 atômica)**: toca 2+ objetos Odoo · invoca service externo + faz agregação · multi-step com checkpoint · usa Playwright/RecebimentoLf/RecLf etc. Se ≥1 sinal, é C3, vai para Tabela 2; NÃO entra na Tabela 1.

### Tabela 4 — Sub-skills PRE-FLIGHT (auditoria fiscal antes de SEFAZ)

| Sub-skill | Objeto Odoo | Service (L1) | Camada | Status |
|-----------|-------------|--------------|--------|--------|
| `auditando-cadastro-fiscal-odoo` | product.product + l10n_br_ncm + stock.lot (G014) + AjusteEstoqueInventario (D-OPS-2) | [`scripts/cadastro_fiscal_audit.py`](scripts/cadastro_fiscal_audit.py) (CadastroFiscalAuditService) | READ-only + WRITE opcional G035 | 🟡 **V1 'inventario'** (cobre G017+G018+G035+G014 + D-OPS-2/3; 14 pytest; delegada pela Skill 8 v15+) |

### Tabela 5 — Fluxos L3 (Markdown — compõem múltiplos átomos)

> Folhas em `app/odoo/estoque/fluxos/`. Carregadas SOB DEMANDA pelo subagente.

**Escritas (✅)**: 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, **1.2.1 (v19+)** (escriturar DFe caminho A), **1.2.2 (v19+)** (criar DFe a partir do XML da SAÍDA — caminho B), **1.1.1 (v27+ S5)** (faturamento saída pura — composição Skill 8 ATÔMICA L2 5 átomos), **1.3 (v27+ S5)** (transferência completa — composição 1.1.1 + 1.2.x end-to-end).
**Pendentes (⬜)**: 1.1.1.1, 1.1.1.2, 1.1.1.3, 1.1.2, 1.1.3, 2.3 (transferir saldo entre códigos).

> Galho 1 NF inter-company **destravado v27+ S5**: galhos 1.1, 1.2 e 1.3 escritos como folhas L3 — 1.2.x v19+ (caminho A/B) + 1.1.1 v27+ S5 (saída pura via Skill 8 ATÔMICA L2 — opt-in `--usar-skill8-atomica-v25` LIVE) + 1.3 v27+ S5 (transferência completa compondo 1.1.1 + 1.2.x). Sub-galhos 1.1.1.x e 1.1.2/1.1.3 documentariam variantes específicas — não modeladas (folha 1.1.1 cobre todas via constants v27+ S4).

---

Não-skills: `lot` (stock.lot) = **utils** em `_utils.py`. Leitura/diff/SOT batch (~33 scripts) = continuam ad-hoc operação viva.
Mapeamento script-fonte→átomo: `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Checkpoints: `app/odoo/estoque/ROADMAP_SKILLS.md`.

### 6.b MODOS READ EM SKILLS WRITE (pattern compartilhado — 2026-05-27)

Cada skill WRITE PODE expor `--modo {listar, detalhar}` do **seu objeto principal**, em adição aos verbos operacionais. Pattern uniforme para o orquestrador investigar o objeto antes/depois de operar — sem trocar de skill.

**NÃO confundir com §1.1 (1 skill = 1 objeto)**: continua valendo. Os modos READ operam sobre o **MESMO objeto Odoo principal** da skill — apenas adicionam leitura ao verbos WRITE. Não há violação do invariante.

**Quando criar:**
- Demanda concreta de investigação repetida do objeto (ex.: caso `operando-mo-odoo` v6 2026-05-27 — 343 MOs zumbi pré-2026-05-15 exigiram scripts ad-hoc de listar/detalhar para classificar antes de cancelar).
- NÃO preventivo: skill ganha modos READ quando o gap aparecer (`skills-demanda-driven`).

**Contrato compartilhado:**

```
--modo listar    (READ)
  input:   filtros do objeto (idem filtros do verbo WRITE; ex.: create_de/states/empresas)
  output:  {criterio, total, classificacao:{<status_read>:N}, itens:[{id,name,state,company,classificacao,...}]}
  WRITE:   NUNCA — CLI bloqueia --confirmar em modo listar
  invariante: rótulo `classificacao` por item indica risco de operar (ex.: SEGURO|RESERVA_FANTASMA|FURO_REAL)

--modo detalhar  (READ)
  input:   --<obj>-id N (single, sem filtros)
  output:  {<campos comuns: id,name,state,company>, details:{<específico do objeto>}}
  WRITE:   NUNCA — CLI bloqueia --confirmar
  invariante: campos comuns (id,name,state,company) em raiz; detalhes específicos em `details`
```

**Fronteira com Tabela 2 (`consultando-quant-odoo` ancillary):**
- `--modo listar/detalhar` em skill WRITE = leitura do **objeto principal** dela (MOs em operando-mo, pickings em operando-picking, quants em ajustando-quant).
- `consultando-quant-odoo` (Tabela 2) = leituras **cross-objeto** centradas em quant (ML→quant, picking→quants reservando), que não cabem em uma única skill WRITE.

**Mitigação anti-WRITE-acidental:**
- CLI: `--modo {listar, detalhar}` + `--confirmar` → exit 2 (uso inválido).
- Service: métodos `listar_*`/`detalhar_*` não recebem `dry_run` (sempre READ); pytest valida que não chamam `write`/`create`/`action_*`.

**Implementações atuais:** `operando-mo-odoo` v6 (2026-05-27) — primeira skill a adotar; serve de referência.

## 6.5 ANTIPADRÕES DETECTADOS — CAUSA RAIZ + CONSEQUÊNCIA + COMO EVITAR

> Reescrito v18 Fase 0. Atualizado v19+ (2026-05-26): AP1, AP3, AP4 ✅ RESOLVIDOS; AP2 RECLASSIFICADO com causa real; AP5 ✅ (v18); AP6 NOVO.

### AP1 ✅ RESOLVIDO v19+ — Skill 7 V1 STRICT (`raise NotImplementedError` em pre-cond)

- **CAUSA RAIZ**: V1 escopo restrito a LF→FB para destravar Skill 8 ETAPA E. Limite implementado via `raise` no átomo (em `escrituracao.py:208-218`) em vez de via FLUXOS L3 + CONSTANTS + PRE-FLIGHT.
- **CONSEQUÊNCIA**: skill atômica L2 deveria ser **versátil** (§1) servindo N fluxos variando args. V1 STRICT a fixou em 1 direção.
- **COMO EVITAR**: ao criar nova skill, garantir **ABRANGÊNCIA desde o início**. Pre-cond bloqueia em REAL-RUN, não em DRY-RUN. Limites legítimos vivem em FLUXOS L3 + CONSTANTS + PRE-FLIGHT.
- **RESOLUÇÃO v19+ (2026-05-26)**: criados 7 átomos ABRANGENTES em `escrituracao.py` (`buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida`, `escriturar_dfe`, `gerar_po_from_dfe`, `preencher_po`, `confirmar_po`, `criar_invoice_from_po`). Cada átomo é dry-run-first e versátil (qualquer direção FB↔LF↔CD). `criar_recebimento_orchestrado` V1 STRICT permanece como **wrapper temporário deprecado v20+** para preservar ETAPA E legacy. Mineração do `RecebimentoLfOdooService` (NÃO MEXER) feita via Explore subagente sem tocar o service externo. 22 pytest mockados verdes.

### AP2 ⚠️ CANARY VALIDADO v20+ / ⏳ remoção tampão pendente v21+ pós-bulk PROD — ETAPA F criava picking de ENTRADA dentro de orchestrator de SAÍDA

- **CAUSA RAIZ REAL (descoberta v19+)**: Rafael identificou — Skill 8 (`faturando-odoo`) = SAÍDA. Criar picking de ENTRADA dentro de ETAPA F viola fronteira fiscal Skill 7/Skill 8. A explicação anterior ("DFe demora paliativo") foi um **sintoma**, não a causa: a causa é **picking de entrada nunca deveria ser criado por nós** — é responsabilidade do motor Odoo via `DFe → action_gerar_po_dfe → PO confirmada → picking automático`.
- **CONSEQUÊNCIA**: 8 pickings INV-* PT 19 criados manualmente em PROD via Skill 5 v15a `criar_picking_entrada_destino_manual` (tampão). Acoplou orchestrator SAÍDA a operações de ENTRADA. Hardcodou CFOP (G037 caso degenerado). Bypass do motor fiscal Odoo.
- **COMO EVITAR**: ao implementar etapa de orchestrator que envolva ENTRADA, parar e perguntar: "isto é responsabilidade da Skill 7 (entrada/escrituração)?" Se SIM, criar FLUXO L3 que compõe Skill 7 + Skill 5 átomos GENÉRICOS (não átomos especializados em "criar entrada manual"). Picking de entrada SEMPRE vem do motor Odoo via DFe→PO→picking.
- **RESOLUÇÃO v19+ (2026-05-26)**:
  - 2 fluxos L3 escritos: `1.2.1-escriturar-dfe-industrializacao.md` (caminho A — DFe veio via SEFAZ) + `1.2.2-criar-dfe-manual-transferencia.md` (caminho B — XML da SAÍDA já existe, upload via `criar_dfe_a_partir_do_invoice_saida`).
  - Método novo `FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x` no orchestrator implementa caminho correto (compõe 7 átomos Skill 7 + Skill 5 `preencher_lotes_picking` + Skill 5 `validar`). 4 pytest mockados verdes validam dispatch caminho A vs B.
  - `criar_picking_entrada_destino_manual` (Skill 5 v15a) marcada DEPRECATED em docblock — museum vivo até v20+ canary do fluxo L3 1.2.x em PROD, então será removida.
  - ETAPAS E + F legacy do orchestrator preservadas funcionais (não quebrar 554 pytest verdes). v20+ ativa opt-in: `executar_pipeline_bulk` passa a chamar `executar_fluxo_l3_1_2_x` em vez das ETAPA E/F legacy.
- **RESOLUÇÃO PARCIAL v20+ (2026-05-26)**:
  - **Canary REAL PROD OK**: 1 caso INDUSTRIALIZACAO_FB_LF (invoice 627348, DFe 42868) processado via `executar_fluxo_l3_1_2_x` em 1190ms. Status `FLUXO_OK`. ZERO duplicações no Odoo PROD. Caminho A (DFe via SEFAZ) detectado corretamente; FIX B caminho 2 (`dfe_purchase_fiscal_id`) protegeu contra duplicação como previsto.
  - **Opt-in `--usar-fluxo-l3-v19` LIVE**: arg em `executar_pipeline_bulk` + helper `_executar_etapa_f_via_fluxo_l3` + `CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO` (atual: só LF=5 validado). Default OFF preserva 100% legacy. CD/FB destino retornam `NAO_SUPORTADA_V20` (pendente v21+ expansão constants).
  - **2 FIXES CRÍTICOS na Skill 7**: FIX A em `escriturar_dfe` (anti-sobrescrita fiscal `l10n_br_data_entrada`); FIX B em `gerar_po_from_dfe` (idempotência via 3 caminhos vínculo DFe↔PO minerados de `validacao_nf_po_service.py:530-534`). Sem FIX B, action_gerar_po_dfe DUPLICARIA PO+picking+invoice quando dfe.purchase_id=False mas PO existe via link reverso (75% dos casos).
  - **DeprecationWarning runtime** em `criar_recebimento_orchestrado` (V1 STRICT wrapper).
- **PENDENTE v21+**:
  - Bulk REAL PROD (não só 1 invoice) via opt-in. Após OK: remover tampão `criar_picking_entrada_destino_manual` + remover wrapper V1 STRICT + remover ETAPAS E/F legacy.
  - Expandir CONSTANTS para FB e CD destino.

### AP3 ✅ RESOLVIDO v18 — Orchestrator C3 chamando atomos INLINE (origem dos AP1+AP2)

- **CAUSA RAIZ**: catálogo §6 antigo (pré-v18) misturava skills L2 atômicas com orchestrators C3 macros na MESMA tabela. Quando "skill" pode ser orchestrator, virou natural que orchestrator chamasse outras skills INLINE. v17 levou ao extremo: 420 LOC de RecLF inline em `executar_etapa_e`.
- **CONSEQUÊNCIA**: orchestrator vira god-object. Acoplamento direto a services externos (RecebimentoLfOdoo, LancamentoOdoo). Teste isolado fica difícil. Refator vira impossível.
- **COMO EVITAR**: 3 tabelas distintas no §6 (Skills L2 / Orchestrators C3 / Fluxos L3) — já implementadas v18 Fase 0. Sempre que orchestrator C3 precisar invocar skill, parar e perguntar: "1 invocação só? OK. 2+? Precisa de FLUXO L3."
- **RESOLUÇÃO v18**: §6 reorganizado em 3 tabelas + §3.1 explicitando "Orchestrator C3 NÃO é skill". v19+ adiciona FLUXO L3 1.2.1/1.2.2 + método orchestrator `executar_fluxo_l3_1_2_x` que segue o pattern (orchestrator compõe via FLUXO, não inline).

### AP4 ✅ RESOLVIDO v19+ — Pre-cond raise ANTES de dry-run check

- **CAUSA RAIZ**: `escrituracao.py:206-217` (V1 STRICT) fazia pre-cond check ANTES de verificar `dry_run`. Raise matava antes do plano poder ser mostrado.
- **CONSEQUÊNCIA**: API footgun pequeno — operador rodando dry-run para PLANEJAR cenário hipotético não conseguia.
- **COMO EVITAR**: dry-run SEMPRE planeja. Pre-cond raise APENAS no caminho de WRITE (após `if dry_run: return plano`).
- **RESOLUÇÃO v19+ (2026-05-26)**: 7 átomos novos da Skill 7 ABRANGENTE seguem dry-run-first: pre-cond LEVES (validações sintáticas que retornam `{status: 'FALHA', erro: '...'}` sem raise) ANTES do dry-run check; pre-cond pesadas (que dependem de Odoo) APENAS no caminho de write. Mesmo pattern em Skill 5 `preencher_lotes_picking`.

### AP5 ✅ RESOLVIDO v18 — Criar gotcha sem ler docstrings de CONSTANTS (lição G037 v18)

- **CAUSA RAIZ**: criei G037 em v18 baseado em "intuição de uso prático do `cfop_esperado`" sem ler `operacoes_fiscais.py:17` que JÁ DIZIA "informacional/log. Real e decidido pelo Odoo".
- **CONSEQUÊNCIA**: G037 v18 documentava antipadrão com premissa errada.
- **COMO EVITAR**: ANTES de criar gotcha sobre operações fiscais, ler `operacoes_fiscais.py` + `picking_types.py` **INTEIROS** (não apenas grep). Confirmar se o gotcha proposto contradiz docstring existente.
- **CORREÇÃO v18 Fase 0**: G037 reescrito com escopo restrito ao caminho B paliativo (picking ETAPA F manual sem PO). v19+ AP2 resolvido remove o caso degenerado — `cfop_esperado` volta a ser apenas informacional/log após v20+ canary remover criar_picking_entrada_destino_manual.

### AP6 ⏳ RESOLVIDO PARCIAL v24+ — Confusão nomenclatura "Skill 8 = orchestrator C3" vs átomo L2 RESTRITA

- **CAUSA RAIZ**: catálogo §6 Tabela 2 catalogava `faturando-odoo` como orchestrator C3 pipeline A-F (~5111 LOC) + tinha fachada SKILL.md em `.claude/skills/faturando-odoo/` fingindo ser skill L2. Definição correta (Rafael v19+): **Skill 8 ATÔMICA L2** = validar constants + `action_liberar_faturamento` + polling invoice + validar fatura vs constants + SEFAZ Playwright (5 operações encapsuladas, 1 objeto Odoo = `account.move`). Orchestrator C3 que compõe pipeline A-F é coisa DIFERENTE.
- **CONSEQUÊNCIA**: durante v19+, eu (Claude) afirmei "Skill 8 = SAÍDA delega Skill 2" — frase errada porque skills L2 não delegam (composição = orchestrator C3 / FLUXO L3). Rafael corrigiu. A confusão de nomes induziu o erro.
- **COMO EVITAR**: ao referenciar "Skill 8" futuramente, especificar:
  - **Skill 8 ATÔMICA L2** (`faturando-odoo` definição correta, ✅ LIVE v24+): 5 átomos em `app/odoo/estoque/scripts/faturamento.py` sobre `account.move`. SKILL.md fachada reescrita v24+ aponta para os 5 átomos.
  - **`inventario_pipeline` C3** (orchestrator — renomeado de `faturamento_pipeline.py` em v27+, stub removido v28+): pipeline A-F + recovery + opt-in `--usar-fluxo-l3-v19` que compõe Skill 2 + Skill 5 + Skill 7 ABRANGENTE via FLUXO L3 1.2.x. ETAPAS C+D ainda têm lógica inline em paralelo (refator v25+).
- **RESOLUÇÃO PARCIAL v24+ (2026-05-27)**:
  1. ✅ Criada Skill 8 ATÔMICA L2 em `app/odoo/estoque/scripts/faturamento.py` (~750 LOC) com 5 átomos espelhando padrão Skill 7 ABRANGENTE: `validar_invoice_constants` · `liberar_faturamento` · `polling_invoice` · `validar_invoice_pos_robo` · `transmitir_sefaz`. Cada átomo dry-run-first + idempotente + invariantes G016/G019/G020/G029/G007/G034/D7/D8.3/D9/CRITICAL-1/MED C-1/MED C-2 codificados intra-átomo.
  2. ✅ 28 pytest verdes em `tests/odoo/services/test_faturamento_invoice_service.py` (baseline 622 → 650).
  3. ✅ SKILL.md fachada reescrita: frontmatter aponta para "Skill 8 ATÔMICA L2 v24+" + corpo adiciona seção "5 ÁTOMOS L2" com tabela contratos + exemplo composição típica.
  4. ✅ Tabela 1 §6 adicionada entry `faturando-odoo` ATÔMICA L2.
- **PENDENTE v25+ (refator profundo + canary)**:
  1. ⬜ Opt-in `--usar-skill8-atomica-v25` no `executar_pipeline_bulk` (similar ao `--usar-fluxo-l3-v19`): ETAPAS C+D delegam à nova Skill 8 ATÔMICA em vez de lógica inline.
  2. ✅ Renomeado `faturamento_pipeline.py` → `inventario_pipeline.py` (v27+ S3; stub alias removido v28+ S6.b).
  3. ⬜ Canary REAL PROD do opt-in em 1-5 ajustes para validar paridade vs legacy.
  4. ⬜ Após canary OK: remover ETAPAS C+D legacy (~500 LOC) + migrar 14 testes para `test_faturamento_invoice_service.py`.

---

## 7. GRANULARIDADE (fluxo perigoso = 2 níveis)

Faturamento/escrituração tocam SEFAZ (irreversível): **átomo macro** (default) **+ átomos de etapa** (recuperação). Espelha `09_bulk` + `fat_lf_resume.sh` (saída) / `fat_lf_resume_entrada.sh` (entrada).

## 8. DETERMINISMO DOS GOTCHAS (gotcha = invariante codificado)

| Classe | Exemplos | Como vira determinístico | Onde |
|--------|----------|--------------------------|------|
| estrutural | G004 (picking→robô→SEFAZ) | é a assinatura do átomo | átomo |
| pré-flight fiscal | G035/G017/G007/G018 (→SEFAZ 225) | validador checa+corrige+bloqueia antes de transmitir (`gtin_validator`) | pré-condição |
| reserva | G028, G011 | guard em `validar()` (G028=`consolidar_move_lines`) | átomo picking |
| infra | G016 SSL | retry + keepalive | conexão |
| ordem | faturar→entrada; sleep; validar→liberar | guard clause (átomo N recusa se estado de N-1 ausente) | pré-condição |

**Pré-requisito bloqueante:** ~~G019/G020 ABERTOS~~ **G019/G020 FECHADAS no service** (2026-05-24 v3 — `validar()` re-lê `state` pós-`button_validate` e raise `RuntimeError` se != 'done'; `liberar_faturamento()` valida pré-cond `state=done` antes; cobertos por 8 testes pytest em `test_stock_picking_service.py`). Docs G019/G020 atualizadas de PROPOSTO → IMPLEMENTADO. Skill 8 `faturando-odoo` agora pode invocar `svc.validar()` confiando no invariante.
**Irredutível:** tempo do robô CIEL IT (externo) — polling+timeout dá resultado determinístico, nunca tempo.

### 8.1 REGRA INVIOLÁVEL (SOT D010) — direção MIGRAÇÃO pelo sinal de `diff_qtd`

`diff_qtd = qtd_teorica − qtd_odoo_atual`. O **sinal decide SÓ a direção**; a quantidade é SEMPRE `qtd = abs(diff_qtd)`.

| `diff_qtd` | Significado | Transferência |
|---|---|---|
| `> 0` | lote PRECISA de saldo | `MIGRACAO → lote` |
| `< 0` | lote tem EXCESSO | `lote → MIGRACAO` |
| `≈ 0` | conciliado | SKIP |

Validada por Rafael 2026-05-19 após confusão que quase inverteu ~9.612 transferências. Doc SOT: `docs/inventario-2026-05/00-decisoes/D010-direcao-transferencia-migracao-por-sinal-diff_qtd.md`.

## 9. SUBAGENTE `gestor-estoque-odoo` (WRITE)

Papel: orquestrar operações de escrita + **pesquisar premissas obrigatórias**. Loop: identificar → navegar árvore → carregar folha → pesquisar/validar premissas → compor em `--dry-run` → mostrar plano → `--confirmar` → verificar no Odoo. Diferenciado de `gestor-estoque-producao` (READ-ONLY). Prompt: `.claude/agents/gestor-estoque-odoo.md`.

## 10. FRONTEIRAS (delegar, não absorver)

| Assunto | Dono |
|---------|------|
| Consultar/projetar estoque (sem alterar) | `gestor-estoque-producao` (READ-ONLY) |
| Recebimento de COMPRAS (DFe fornecedor, 4 fases) | `gestor-recebimento` (árvore 1.2.2 delega) |
| CTe (frete) / pallet | módulos `fretes` / `pallet` |
| Diagnóstico cross-area NF/PO/financeiro | `especialista-odoo` |
| Criar/alterar código de integração | `desenvolvedor-integracao-odoo` |

## 11. ESTRUTURA DO PACOTE

```
app/odoo/estoque/
  __init__.py                          fachada
  CLAUDE.md                            este doc (constituição)
  PROTECAO_PROXIMA_SESSAO.md           ⭐ LEITURA OBRIGATÓRIA — escudo contra desvios reincidentes (v18 Fase 0)
  ROADMAP_SKILLS.md                    task-list da migração — HANDOFF enxuto (estado atual + próximo passo)
  VALIDACAO_FINAL_SESSAO.md            historico consolidado das sessoes (cronológico)
  PLANEJAMENTO_SKILL8_FATURANDO.md     planejamento vivo MACRO Skill 8 (sobrevive N sessões; regra inviolável 0)
  _utils.py                            resolvers de PREMISSAS: resolver_empresa, resolver_produto, EMPRESAS (✅)
  scripts/                             átomos C1/C2 das skills L2 (quant, transfer, picking, mo, reserva, pre_etapa, consulta_quant, cadastro_fiscal_audit, escrituracao)
  orchestrators/                       orchestrators C3 macros L1 (pre_etapa_executor ✅, inventario_pipeline ✅ v27+ S3 [renomeado de faturamento_pipeline; stub alias REMOVIDO v28+ S6.b] — pipeline A-F + recovery + opt-in skill8 atomica S1 + helper ETAPA E via FLUXO L3 v28+ S7)
  fluxos/                              folhas L3 Markdown (progressive disclosure — galho 2/3/4 ✅; galho 1 ⬜ bloqueado por refator v19+)
# COMPAT: app/odoo/services/<nome>_service.py vira SHIM (re-export) — preserva 105 scripts + testes ativos
# Pattern (v13): criar `PLANEJAMENTO_SKILL<N>_<NOME>.md` quando capinagem exigir 3+ sessões (critério: SEFAZ irreversível + estado distribuído + 4+ etapas dependentes). Regra inviolável 0: LER inteiro + atualizar checkpoint ANTES de qualquer modificação em código.
```

## 12. INVARIANTES DE EXECUÇÃO (toda operação WRITE)

1. `--dry-run` sempre primeiro → mostrar plano.
2. Confirmação explícita antes de `--confirmar` (irreversível: SEFAZ).
3. Premissas pesquisadas E validadas antes de compor.
4. Verificar resultado DIRETO no Odoo (não confiar só no output).
5. Operação VIVA: 105 scripts ad-hoc intactos até o átomo maturar; arquivar SUPERADO só após checklist do ROADMAP/`PLANO_MIGRACAO §7`.

## 13. PONTEIROS

- Roadmap (capinar): `app/odoo/estoque/ROADMAP_SKILLS.md` (HANDOFF v13 atualizado)
- Historico consolidado: `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` (§1-§16)
- **Planejamento Skill 8 MACRO (sobrevive N sessoes):** `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (v13+) — **OBRIGATORIO LER ANTES de tocar Skill 8**
- Folhas de fluxo: `app/odoo/estoque/fluxos/`
- Subagente: `.claude/agents/gestor-estoque-odoo.md`
- Mineração script→átomo: `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`
- Assunto×camada×gotchas: `docs/inventario-2026-05/consolidacao/MAPA_ASSUNTOS.md`
- Estrutura/shims: `docs/inventario-2026-05/consolidacao/PLANO_MIGRACAO.md`
- IDs fixos / Gotchas Odoo: `.claude/references/odoo/IDS_FIXOS.md` · `.claude/references/odoo/GOTCHAS.md`
- Padrão skill completo: `~/.claude/projects/.../memory/feedback_skill_padrao_completo.md`
- ⭐ **Escudo contra desvios reincidentes (LEITURA OBRIGATÓRIA):** `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`

---

## 14. HISTÓRICO DE DESVIOS ARQUITETURAIS (documentado v18 Fase 0)

> Esta seção registra DESVIOS DA DOCUMENTAÇÃO ou DO PRINCÍPIO FUNDADOR que sessões anteriores cometeram. **Cada desvio listado aqui já foi corrigido**, mas permanece registrado para que sessões futuras saibam que o problema foi detectado e tratado — e não o reintroduzam acidentalmente.

### D-V30-1 — Canary REAL remessa avulsa FB→LF: DFe-resumo NÃO gera picking nativo + C7/C9/C9.1 (2026-06-02)

**Detectado em**: 2026-06-02 — canary REAL Task 5 (INDUSTRIALIZACAO_FB_LF avulsa: 105000002 30,56kg + 105000044 5,36kg, FB→LF lote P-02/06). SAÍDA NF RPI/2026/00248 (move 744869) AUTORIZADA SEFAZ (CFOP 5901); ENTRADA NF ENTIN/2026/06/0004 (move 745414) posted (CFOP 1901, fp 131); picking LF/IN/01796 done; saldo LF/Estoque/P-02/06 = 30,56 + 5,36.

**3 fixes (commitados local, NÃO pushados):**
- **C7** (`9715c8f3d`): `_registrar_auditoria` (`faturamento.py` + `_invoice_helpers.py`) pula quando `ajuste_id is None`. Caminho avulso (folha 1.3.1, `ajuste_ids=None`) batia em `registro_id` NOT NULL → `NotNullViolation` mascarada pelo try/except mas que envenenava a sessão SQLAlchemy nos commits críticos da Skill 8 (CRITICAL-1 pós-SEFAZ). Espelha guard do orchestrator (D-V29-1 nota b). Os 28 testes unitários NÃO pegaram (try/except mascara) — só o dry-run da CADEIA real expôs (mesmo padrão do GAP-1).
- **C9/C9.1** (`a8835dbff`): átomo `criar_picking_entrada_destino_manual` (Skill 5) ganhou `purchase_line_id` por move (C9) + DERIVA `warehouse_id` do picking_type + aceita `partner_id` (C9.1). Todos opcionais/retrocompatíveis.

**ACHADO ARQUITETURAL — AP2 refutado para DFe-resumo**: a premissa da deprecação do AP2 ("picking de entrada vem do motor via DFe→PO→picking nativo") NÃO vale para INDUSTRIALIZACAO_FB_LF: o DFe é resumo (`l10n_br_status='06'`) e o `button_confirm` da PO NÃO dispara o procurement (move_ids vazio) MESMO com route 133/account LF/picking_type 19/team 143 corretos (4 POs confirmaram sem picking: 42914/15/16/17). Logo o picking de entrada MANUAL VINCULADO à PO é o caminho PADRÃO (não exceção) desta operação. O picking manual precisa REPLICAR o picking NATIVO (gold standard PO 42759/picking 322616 = Vendors→LF/Estoque com `warehouse_id`/`group_id`/`partner_id`) — senão `button_validate` falha `Fault 2 'Source Location not set'`. C9.1 codifica `warehouse_id`+`partner_id`. O átomo foi **reabilitado** (docblock atualizado de DEPRECATED → REABILITADO C9).

**GOTCHA 1 (causa raiz do account errado)**: `action_gerar_po_dfe` usa a company do USUÁRIO (uid 42=FB) → PO.lines com `account_id` da FB (22611) em vez do LF (26459) → `criar_invoice_from_po` travaria 'Empresas incompatíveis'. Forçar `context={'allowed_company_ids':[dest],'company_id':dest}` resolve nativamente. **C10 ✅ (`0169e1694`)**: o átomo `gerar_po_from_dfe` (`escrituracao.py`) agora deriva a company do próprio DFe (`dfe.company_id`) e força esse context no plano + no fire (retrocompat: DFe sem company → context atual).

**LIÇÕES ATEMPORAIS**:
1. Antes de depreciar um átomo de "criação manual" assumindo que "o motor faz", validar em TODOS os caminhos do motor — DFe-resumo é um caso onde o motor NÃO faz.
2. Picking manual vinculado a PO precisa dos campos do picking NATIVO (`warehouse_id`, `partner_id`) p/ `button_validate` passar — não basta `location_id` estar setado.
3. `tipo_pedido` DFe='compra' NÃO afeta a geração do picking (POs serv-industrializacao também geram) — correlação ≠ causa.

**Onde**: `scripts/picking.py` (C9/C9.1) + `scripts/faturamento.py`/`_invoice_helpers.py` (C7) + `fluxos/1.3.1-remessa-avulsa-insumo.md` (PASSO 8 + Status) + memória `capacitacao_gestor_remessa_fb_lf`.

### D-V29-1 — Follow-up CR findings F1+F3 + achado CFOP 5902 reincidente (2026-05-29)

**Detectado em**: 2026-05-29 v29+ — follow-up dos 2 CR findings do code-reviewer v28+ (decisão Rafael) + auditoria READ-only do candidato natural de canary.

**F1 (HIGH) ✅ CORRIGIDO — `EXECUTADO_PARCIAL` escapava do agregado de `executar_pipeline_bulk`**:
- Sintoma: o agregado (`inventario_pipeline.py` ~5545) só detectava `s.startswith('FALHA') or s in STATUS_FALHA`. Os status `EXECUTADO_PARCIAL` / `DRY_RUN_PARCIAL` / `EXECUTADO_PARCIAL_TIMEOUT/_MISTO/_FALHA/_ETAPA_A` (retornados por ETAPAs A/C/D/E/F em onda mista — ex. linhas ~3634 helper F, ~3855 helper E, ~4169-4173 ETAPA C/D) NÃO davam `startswith('FALHA')` nem estavam no tuple → **escapavam** → pipeline reportava `EXECUTADO_OK` mascarando pendências. (Inconsistente: `SKIP_NAO_SUPORTADA_V20` estava no tuple e virava PARCIAL, mas a onda mista — pior caso — escapava.)
- Fix: adicionar `'PARCIAL' in s` na condição (espelha guard CR-H4 `'PARCIAL' in status_b` ~5327). `SKIP_NAO_SUPORTADA_V20` mantido no tuple (direção não-mapeada = pendência que o operador DEVE ver). 4 pytest novos.
- Decisão Rafael: "você define, só funcione corretamente os edge cases" → Opção 1 (detectar PARCIAL + manter SKIP; narrowing rejeitado pois mascararia pendência).

**F3 (MEDIUM) ✅ CORRIGIDO — `usuario` órfão nos helpers E/F do FLUXO L3**:
- Sintoma: `_executar_etapa_e/f_via_fluxo_l3` aceitavam `usuario` mas não o usavam (Pyright unused 3436/3650). O caminho L3 NÃO persistia audit trail (os átomos Skill 7/5 não auditam — retornam dict; só `out['passos']` + log).
- Fix: `executar_fluxo_l3_1_2_x` ganhou `usuario`+`ciclo`+`ajuste_id_ref`; o closure `_passo` registra `OperacaoOdooAuditoria` por passo com `executado_por=usuario` (frase exata do finding: "propagação via passos do FLUXO L3"), usando `ajuste_id_ref` como `registro_id`; helpers E/F passam `ajs[0].id`.
- **Correção pós code-review (nota b do reviewer)**: `registro_id` é NOT NULL (`operacao_odoo_auditoria.py:19`) — a 1ª versão (`ajuste_id=None`/'BATCH') violaria a constraint e a auditoria NÃO persistiria (absorvida pelo try/except; teste mockado não pegaria). Solução final: guard no `_passo` (só audita se `ajuste_id_ref` não-None — uso direto sem helper pula) + `_registrar_auditoria` mantido `ajuste_id: int` (revertido o Optional/BATCH). 3 pytest novos (inclui o do guard).
- Decisão Rafael: "Propagar usuario ao FLUXO L3".

**Baseline pytest**: 681 → **688 verdes** (+7 = 4 F1 + 3 F3).

**Achado CFOP 5902 (auditoria READ-only — ⚠️ DECISÃO FISCAL PENDENTE Rafael, NÃO corrigido)**: o candidato natural de canary revelou **6 NFs LF→FB DEV_LF_FB (produto tipo 4 acabado) com CFOP de linha 5902** (errado; correto **5949** — `operacoes_fiscais.py:124-126` já documentava como "ERRO CONHECIDO"). **Causa NÃO é bug do nosso código** (pipeline mapeou `fiscal_position 89` + `l10n_br_tipo_pedido=dev-industrializacao` corretos); a engine fiscal CIEL-IT auto-seleciona na LINHA a Operação `l10n_br_operacao_id` **2710 "Retorno de Industrialização - Devolução"** (`intra_cfop=5902`) para destino **FB (partner 1)**, enquanto destino **CD (partner 34)** usa **2719 "Retrabalhos"** (`intra_cfop=5949`). É **cadastro fiscal do destino FB no Odoo**. 2 NFs são de hoje (725475 SARET/2026/00011 + 725798 SARET/2026/00012, ainda `autorizado` sem CC-e); 4 do backlog já têm CC-e. Tratamento das NFs + correção cadastral = decisão fiscal Rafael. **Implicação no roadmap**: canary S2 destino-FB (PERDA_LF_FB/DEV_LF_FB/TRANSFERIR_CD_FB) fica **bloqueado** até a correção cadastral — senão cada novo DEV_LF_FB nasce com 5902. Backlog 2026-05-20 (21/21 invoices) já tem entrada escriturada → ETAPA E sobre ele DUPLICARIA (não serve para canary).

**Investigação CFOP-2 FB→5949 (READ-only, 2026-05-29 — causa cadastral confirmada, decisão fiscal Rafael)**: Operação `l10n_br_ciel_it_account.operacao` **2710 'Retorno de Industrialização - Devolução'** (company LF=5, tipo_pedido='dev-industrializacao', saída, `partner_ids=[]` = **GENÉRICA**) → 5902; a **2719 'Retrabalhos'** (5949) está restrita a `partner_ids=[34]` (CD). A engine CIEL-IT prioriza operação com partner específico sobre a genérica → destino FB (sem operação específica) cai na 2710. Uso total da 2710 = **83 linhas / 10 NFs, TODAS LF→FB tipo 4 do inventário** (SARET/2026/00003-12), zero uso legítimo de 5902 (o 5902 legítimo de insumo tipo 1-3 vive em outras operações: 850/81 da FB + venda-industrializacao fp 111). **Recomendação técnica: R3b — criar Operação LF→FB 5949 com `partner_ids=[1]` espelhando a 2719** (NÃO alterar o CFOP da 2710, que é o fallback GENÉRICO — alterá-la mudaria o comportamento de destinos futuros sem operação própria). R2 (forçar `l10n_br_operacao_id` no pipeline) reusa op semanticamente CD + precisa canary. Incoerência cadastral notada p/ fiscal: 2710 tem tipo_pedido='dev-industrializacao' (tipo 4) mas CFOP 5902 (de insumo tipo 1-3). **Correção cadastral = cadastro fiscal Odoo, FORA das skills-átomos do orquestrador — não executável por conta própria** (invariante: não improvisar XML-RPC fora das skills). As 10 NFs já emitidas (3 canceladas 00003-05, 4 com CC-e 00006-09, 3 autorizadas 00010-12) = pendência fiscal Rafael (NF autorizada com CFOP errado → processo formal; CC-e geralmente não corrige CFOP).

**LIÇÕES ATEMPORAIS**:
1. Status agregado de orchestrator deve detectar TODAS as variantes de "parcial" (`'PARCIAL' in s`), não só `FALHA*` + tuple — senão onda mista mascara pendências como sucesso.
2. Em inter-company que toca SEFAZ, o CFOP da linha é decidido pela `l10n_br_operacao_id` (auto-selecionada pela engine CIEL-IT por **partner/destino**), NÃO pela `fiscal_position`. Validar a Operação RESULTANTE por destino ANTES do canary real (cadastro FB tem Operação 2710 errada para produto acabado tipo 4 — gera 5902 em vez de 5949).

### D-V28-1 — ETAPA E retornava SKIP_NAO_SUPORTADA_V20_FLUXO_L3 quando flag `--usar-fluxo-l3-v19=True` (✅ DESTRAVADO v28+ S7 2026-05-28)

- **Detectado em**: 2026-05-27 v27+ S4 — CR-Finding 2 do code-reviewer holístico (88% conf). Sessão v28+ resolveu.
- **Sintoma**: `executar_etapa_e` com `usar_fluxo_l3_v19=True` retornava early `SKIP_NAO_SUPORTADA_V20_FLUXO_L3` (linhas 4281-4295 pré-v28+). Bloqueava ETAPA E via FLUXO L3 para 4 ações X→FB/X→LF (PERDA_LF_FB, TRANSFERIR_CD_FB, DEV_LF_FB destino=FB; DEV_CD_LF destino=LF). Operador rodando `--usar-fluxo-l3-v19 --etapas E,F` via Skill 7 V1 STRICT legacy (que precisa robô CIEL IT slow ~30-60min/invoice).
- **Causa raiz**: v20+ S3 implementou opt-in apenas para ETAPA F (LF destino validado canary). ETAPA E ficou pendente expansão de constants — só LF=5 mapeado. Pré-v27+ S4: FB constants ausentes. v27+ S4 mapeou FB+CD + 8 ações da MATRIZ → destravou possibilidade. v27+ Finding 2 questionou TRANSFERIR_CD_FB (ACOES_ENTRADA_DESTINO_MANUAL? não — Rafael decidiu CD→FB também precisa pattern buscar DFe / criar manual via XML saída).
- **FIX v28+ S7 (commit pendente)**:
  - Novo helper privado `FaturamentoPipelineExecutor._executar_etapa_e_via_fluxo_l3` (~190 LOC em `inventario_pipeline.py:3664-3854` — ANTES do bloco "v25+ S1"). ESPELHA `_executar_etapa_f_via_fluxo_l3` trocando filtro: `ACOES_ENTRADA_FB` em vez de `ACOES_ENTRADA_DESTINO_MANUAL`. Lógica restante 100% idêntica (build lotes_data agregando por (pid, lote_destino) com `abs(qtd_ajuste)`, transform vazio/'MIGRAÇÃO' → `INV-{cod}-{HOJE}`, filtro meta-keys '_' antes do splat, status agregado EXECUTADO_OK/PARCIAL/SKIP_NAO_SUPORTADA_V20).
  - `executar_etapa_e` modificado: linhas 4281-4295 substituídas por dispatch:
    ```python
    if usar_fluxo_l3_v19:
        return self._executar_etapa_e_via_fluxo_l3(...)
    ```
    Default `usar_fluxo_l3_v19=False` preserva 100% legacy Skill 7 V1 STRICT.
  - Help text CLI `--usar-fluxo-l3-v19` atualizado (linha 6048): menciona destravamento ETAPA E v28+ S7.
  - Comentário STATUS_FALHA (linha 5507): preserva SKIP_NAO_SUPORTADA_V20_FLUXO_L3 no tuple por compat futura (defesa genérica) mas explica que ETAPA E não retorna mais esse status v28+ S7.
  - 6 pytest novos em `test_faturamento_pipeline_orchestrator.py` (substituem `test_v20_s3_etapa_e_skip_quando_flag_v19` legado): LF dry-run + FB dry-run + PERDA_LF_FB real-run + DEV_CD_LF real-run + default OFF preserva legacy + SKIP_NENHUM_AJUSTE. Cobertura: dispatch + lotes_data resolved + constants splat + G039 dinâmico FB (mocked) + STATIC LF=143 + status agregado.
- **Pytest**: 676 → **681 verdes** (+5 net = 6 novos S7 − 1 substituído legado). Em 15.62s.
- **Decisão Rafael 2026-05-27**: "robô CIEL IT tem mesmo defeito de atraso em QUALQUER tipo — CD→FB também precisa funcionar pelo mesmo pattern de pesquisa DFe + criar manual via XML saída". Resolve CR-Finding 2 S4 sem adicionar TRANSFERIR_CD_FB em ACOES_ENTRADA_DESTINO_MANUAL — preserva fronteira `ACOES_ENTRADA_FB` = X→FB (legacy E processa via Skill 7) vs `ACOES_ENTRADA_DESTINO_MANUAL` = FB→X (legacy F processa via Skill 5).
- **Atenção G039 dinâmico FB destino**: 3 das 4 ações destinam FB (1). `_resolver_constants_fluxo_l3` faz override G039 dinâmico para `company_destino != 5`. Primeira execução real ativará `garantir_purchase_team(uid_rafael=42, company_id=1)` — átomo idempotente codificado v23+ cria team automaticamente se não existir. Fallback silencioso para STATIC do constants caso falhe.
- **PENDENTE v29+ canary REAL PROD**: validar paridade vs legacy em 1 caso natural de cada direção: PERDA_LF_FB OU TRANSFERIR_CD_FB (FB destino G039 dinâmico) + DEV_CD_LF (LF destino STATIC 143). Após canary OK: remover ETAPA E legacy (Skill 7 V1 STRICT `criar_recebimento_orchestrado` wrapper) + flip default `usar_fluxo_l3_v19=True`.
- **S6.b paralelo (mesmo commit)**: stub `app/odoo/estoque/orchestrators/faturamento_pipeline.py` REMOVIDO. Confirmado zero imports Python ativos via grep. Pytest 681 verdes SEM stub. N32 em PROTECAO marcada OBSOLETO + lição atemporal preservada (vale para qualquer stub futuro).
- **Cleanup adicional v28+ (segundo commit `chore`)**: 4 itens DEPRECATED auditados; 2 removidos seguramente (puro código, zero impacto em canary REAL pendente):
  - **Removido** flag `permitir_etapa_a_noop_real` (DEPRECATED v16, ~12 sessões sem callers reais em PROD; default OFF preservava comportamento; branch real-run + status `EXECUTADO_ETAPA_A_NOOP_DEPRECATED` + test `test_executar_etapa_a_v16_flag_deprecated_noop_funciona` removidos).
  - **Removido** 3 imports não-usados nivel topo de inventario_pipeline.py: `PAYMENT_PROVIDER_SEM_PAGAMENTO` (G029 vai via `_invoice_helpers.garantir_payment_provider`), `ACAO_PARA_CFOP_ENTRADA` (D17 já encapsulado por Skill 7 atomo legacy), `LOCATION_ORIGEM_ENTRADA_INDUSTR` (ETAPA F legacy usa `get_location_origem_entrada(acao)` que resolve por direção v17.5).
  - **MANTIDO** (precisa canary REAL S6 v29+ antes de remover):
    - Skill 5 átomo `criar_picking_entrada_destino_manual` (DEPRECATED v19+, museum vivo — ETAPA F LEGACY depende)
    - Skill 7 wrapper `criar_recebimento_orchestrado` V1 STRICT (DeprecationWarning v20+ — ETAPA E LEGACY depende)
  - **MANTIDO como museum vivo** (sem caller mas valor histórico/gotcha):
    - Alias `LOCATION_ORIGEM_ENTRADA_INDUSTR` no `picking_types.py` (alias para 26489 — backward-compat se algum script ad-hoc usar)
    - `LOTES_MIGRACAO_POR_COMPANY` no `locations.py` (DEPRECATED 2026-05-24 v4 G031 — museum vivo gotcha)
  - Pytest pós-cleanup: 682 → **681 verdes** (−1 = test do flag removido).
  - **LIÇÃO ATEMPORAL**: cleanup de deprecated tem 2 níveis:
    - **NÍVEL 1 PURO CÓDIGO** (zero risco): flags com default OFF + branches mortos + imports não-usados + tests de comportamento DEPRECATED. Pode-se remover assim que confirmado zero callers reais (grep + N sessões de evidência).
    - **NÍVEL 2 LEGACY DEPENDENTE** (precisa canary REAL): skills DEPRECATED chamadas por ETAPAs legacy do orchestrator. Só pode-se remover após canary REAL PROD validar paridade do caminho novo. NÍVEL 1 + NÍVEL 2 SEMPRE em commits separados (`chore` vs `feat` cleanup).
- **LIÇÃO ATEMPORAL**: opt-in flag introduzido em sessão N pode ficar PARCIAL por N+M sessões (ETAPA E SKIP de v20+ a v27+ = 7 sessões). Resolução é simples (~190 LOC helper + dispatch + 6 pytest = 1 sessão) mas só quando constants/mapping da decisão estão prontos (v27+ S4 + Finding 2 resolvido). Pattern AR13 reciclado: caminho novo só destrava quando todas as premissas (constants + decisão arquitetural + lote natural ou pytest mockado adequado) estão consolidadas.
- **Onde**: `app/odoo/estoque/orchestrators/inventario_pipeline.py` (~190 LOC helper E + 17 LOC dispatch + 10 LOC docs/comments) + `tests/odoo/services/test_faturamento_pipeline_orchestrator.py` (~280 LOC = 6 pytest novos).

### D-V26-1 — `P-15/05` tratado como proxy-vazio evaporava saldo em produto `tracking='lot'` (✅ CORRIGIDO v26+ 2026-05-29 — Opção B)

- **Detectado em**: 2026-05-28 execução do inventário (17 MOVER do bloco B: `{emp}/Indisp/MIGRAÇÃO` → `{emp}/Estoque/P-15/05`) — saldo saía da origem e evaporava no destino (`qty=0`). Rollback +1.720,36 un; reexecução via 2× Skill 1.
- **Sintoma**: `transferir_loc_e_lote` (MODO D) com `nome_lote_destino='P-15/05'` retornava `EXECUTADO` mas o destino ficava sem saldo (Odoo zera quant sem lote em produto rastreado).
- **Causa raiz**: `resolver_lote_origem/destino` tratavam `'P-15/05'` como proxy de `lot_id=False` (semântica de matching D012/D013), enquanto a Skill 1 `ajustar_quant` criava o `stock.lot` REAL "P-15/05" (299 lotes no Odoo). Mesmo nome, semântica OPOSTA entre Skill 1 e Skill 2.
- **Decisão (Rafael, Opção B)**: `P-15/05` depende do `product.tracking` — `tracking='none'` → proxy-vazio (legado preservado); `tracking='lot'/'serial'` → `stock.lot` REAL. `None`/`''` continuam sempre sem lote.
- **FIX v26+ (CODIFICADO)**: helper `_tracking_produto` (cache) + branch `P-15/05` em `resolver_lote_origem/destino` (`transfer.py`); `pre_etapa_executor` usa o `nome_canonico` RETORNADO (não o input) na condição `DRY_RUN_OK_LOTE_A_CRIAR` (fidelidade dry-run↔real). 729 pytest verdes em `tests/odoo/`.
- **LIÇÃO ATEMPORAL**: identificador textual com semântica diferente por contexto (matching/leitura vs destino/escrita) deve resolver por uma dimensão objetiva do dado (`tracking`), não por lista hardcoded de "nomes proxy". 2 skills divergindo sobre o MESMO nome = armadilha.
- **Onde**: `docs/inventario-2026-05/02-gotchas/G040-*.md` + `transfer.py` (`_tracking_produto`, `resolver_lote_origem/destino`) + `pre_etapa_executor.py` (`_executar_positivo_puro`) + 2 arquivos de teste.

### D-V25-1 — Caminho novo L3 v19+ ignorava dados do `AjusteEstoqueInventario` + sem hardening de company/tipo (4 fixes F1-F4 ✅ CODIFICADOS v25+ 2026-05-27)

- **Detectado em**: 2026-05-27 v25+ cirurgia AVULSO_FRASCO (37688un cod 210030009 FB→LF) — Rafael identificou 4 fixes diretos pós-validar análise root cause do subagente.
- **Sintoma 1 (F1)**: `_executar_etapa_f_via_fluxo_l3` chamava `executar_fluxo_l3_1_2_x` SEM `lotes_data` → default `lote_default='MIGRAÇÃO'` literal aplicado a TODOS os MLs. Saldo final em LF/Estoque/MIGRAÇÃO em vez de lote do XML SEFAZ (ex: AJ-27-05). Legacy v17.5 da ETAPA F (`executar_etapa_f` linhas 3998-4018) FAZIA certo (lia `AjusteEstoqueInventario.lote_destino`, transformava vazio/'MIGRAÇÃO' → `INV-{cod}-{HOJE}`); caminho novo regrediu.
- **Sintoma 2 (F2a)**: B-V23-1 fix (`dfe.line.company_id=destino`) só estava codificado em `criar_dfe_a_partir_do_invoice_saida` (caminho B). Caminho A (DFe via SEFAZ — `buscar_dfe` retorna `encontrado=True`) não tinha fix equivalente. Em INDUSTRIALIZACAO_FB_LF os DFes vêm via SEFAZ (4 de 4 do canary v20+ — empiricamente provado em `fluxos/1.2.2-criar-dfe-manual-transferencia.md:24`).
- **Sintoma 3 (F2b)**: `executar_fluxo_l3_1_2_x` deixava picking nativo (gerado via `action_gerar_po_dfe`) sem G023 force `company_id`. XML-RPC não herda automaticamente em todos os cenários. Átomo legacy `criar_picking_entrada_destino_manual` já codificava G023 (`picking.py:1391-1399`) mas o caminho novo regrediu.
- **Sintoma 4 (F3)** ⚠️ **SUPERSEDED por D-V30-1 (2026-06-02) — conclusão `dfe='compra'` REVERTIDA por C6**: `escriturar_dfe` escrevia `l10n_br_tipo_pedido='serv-industrializacao'` no DFe via `L10N_BR_TIPO_PEDIDO_POR_ACAO['INDUSTRIALIZACAO_FB_LF']='serv-industrializacao'`. À época concluiu-se (erroneamente) que o tipo correto no DFe seria `'compra'`; só na PO+Fatura é que viraria `'serv-industrializacao'`. Evidência da época: linha 20 do `CIRURGIA_AVULSO_FRASCO_2026_05_27.md` (Rafael alterou manualmente PO 42543 'compra'→'serv-industrializacao' via UI). **CORREÇÃO C6 (D-V30-1)**: o `escriturar_dfe` **REJEITA** `'compra'` (whitelist `escrituracao.py:1390-1394`); o canary REAL escriturou `serv-industrializacao` em DFe+PO+fatura. Código atual: `{'dfe': 'serv-industrializacao', 'po': 'serv-industrializacao'}` (`inventario_pipeline.py:3316-3319`). A correção `dfe='compra'` abaixo (F3a/F3b) vale apenas como registro histórico para INDUSTRIALIZACAO_FB_LF.
- **Sintoma 5 (F4)**: G039 hook resolvia `team_id` dinamicamente do user de execução. Para Rafael uid=42 retornava team 143 corretamente. Mas para outros users retornaria team diferente. Padrão operacional desta skill: 143 SEMPRE, independente de quem dispara.
- **Causa raiz comum**: caminho novo L3 v19+ (`executar_fluxo_l3_1_2_x` + `_executar_etapa_f_via_fluxo_l3`) foi escrito v19+ mockado/canary com 1 invoice apenas. Não passou pela bateria de hardenings do legacy v17.5 (que tinha histórico PROD em 317306/317316). Cirurgia AVULSO_FRASCO revelou os 4 gaps.
- **FIX v25+ (CODIFICADO commit `ea505c0e`)**:
  - **F1** — `_executar_etapa_f_via_fluxo_l3` resolve `lotes_data` por invoice via `_resolver_pids_em_batch` + agrega `(product_id, lote_destino)` com `abs(qtd_ajuste)`. Vazio/'MIGRAÇÃO' → `INV-{cod}-{HOJE}` (espelha legacy v17.5 + consistente com 317306, 317316).
  - **F1b** — `executar_fluxo_l3_1_2_x` default `lote_default='MIGRAÇÃO'` → `None` (forca caller a fornecer). Caller passa `INV-FALLBACK-{HOJE}` apenas como último recurso.
  - **F2a** — Novo átomo público `EscrituracaoLfService.alinhar_dfe_lines_company(dfe_id, company_destino)` em `escrituracao.py:835` (~120 LOC) generaliza B-V23-1 do caminho B. Invocado no passo 1.5 do `executar_fluxo_l3_1_2_x` quando caminho A.
  - **F2b** — Passo 6.5 do `executar_fluxo_l3_1_2_x` força `stock.picking.company_id` + `stock.move.company_id = company_destino` após localizar picking ativo. Não-fatal: erro vira log warning.
  - **F3a** — `L10N_BR_TIPO_PEDIDO_POR_ACAO` refatorado `Dict[str, str]` → `Dict[str, Dict[str, str]]` com keys `'dfe'`/`'po'`. INDUSTRIALIZACAO_FB_LF → `{'dfe': 'compra', 'po': 'serv-industrializacao'}`. **⚠️ `dfe` REVERTIDO por C6 (D-V30-1, 2026-06-02): INDUSTRIALIZACAO_FB_LF agora é `{'dfe': 'serv-industrializacao', 'po': 'serv-industrializacao'}` (`inventario_pipeline.py:3316`). As outras 7 ações permanecem `dfe='compra'` (CANDIDATE) = BUG LATENTE — ver follow-up §2.** A estrutura `Dict[str,Dict[str,str]]` (keys `'dfe'`/`'po'`) permanece válida.
  - **F3b** — Passo 3 `escriturar_dfe(l10n_br_tipo_pedido=l10n_br_tipo_pedido_dfe)` (assinatura renomeada).
  - **F3c** — `preencher_po` aceita parâmetro opcional `l10n_br_tipo_pedido: Optional[str]`. Quando fornecido, inclui no write da PO (whitelist espelha `escriturar_dfe`).
  - **F3d** — Passo 5 `preencher_po(l10n_br_tipo_pedido=l10n_br_tipo_pedido_po)`. Fatura herda da PO sem intervenção adicional no passo 9.
  - **F4** — `CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[5]['team_id']` 41 → **143** STATIC FIXO. `_resolver_constants_fluxo_l3` desliga override G039 dinâmico quando `company_destino=5`. Demais destinos (FB=1, CD=4) mantêm G039 quando forem mapeados v26+.
- **Pytest**: 655 → **662 verdes** (+7 net = 8 testes novos F2a/F3c - 1 teste removido por reescrita F4) em 17s tests/odoo/.
- **Hipóteses descartadas pelo Rafael**:
  - ❌ G-PO-NATIVA-SEM-PICKING (criar picking manual se PO sem picking_ids) — NÃO implementado, Rafael confirmou não foi necessário.
  - ❌ G-DFE-PURCHASE-FISCAL-ID-STALE (cleanup fiscal_id antes reprocessar) — só impactou cirurgia, não fluxo automático.
- **LIÇÃO ATEMPORAL**: ao criar novo "caminho" (FLUXO L3 v19+) que substitui legacy validado em PROD, OBRIGATORIAMENTE auditar TODOS os hardenings do legacy (loop de `for ajuste in legacy`: o que ele lê do DB local? o que ele força no Odoo? quais campos verifica?). Se algum não estiver no novo, é REGRESSÃO silenciosa que só aparece em PROD. Pattern provado v25+: cada gap virou fix F1-F4 com mapeamento direto ao código legacy v17.5 da ETAPA F.
- **Onde**: `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (5 hunks) + `app/odoo/estoque/scripts/escrituracao.py` (2 hunks: novo átomo `alinhar_dfe_lines_company` + `preencher_po` aceita `l10n_br_tipo_pedido`) + `app/odoo/estoque/CIRURGIA_AVULSO_FRASCO_2026_05_27.md` (seção "Implementação v25+") + 4 arquivos de tests.

### D-V18-1 — Catálogo §6 misturava skills L2 com orchestrators C3 macros

- **Detectado em**: 2026-05-26 auditoria Rafael pós-v17.5
- **Sintoma**: tabela "Skills WRITE (8)" listava `faturando-odoo` (orchestrator C3 ~4150 LOC) + `escriturando-odoo` (atomo HÍBRIDO encapsulando svc externo 4562 LOC) + `planejando-pre-etapa-odoo` (planner+executor) JUNTO com `ajustando-quant-odoo` (átomo C1 de 1 stock.quant). Misturar átomos L2 com orchestrators C3 macros legitimou os antipadrões AP2 + AP3.
- **Correção**: §6 reorganizado em 3 tabelas distintas (Skills L2 atômicas / Orchestrators C3 / Fluxos L3). §3.1 explicitou "Orchestrator C3 NÃO é skill".
- **Onde foi corrigido**: este `CLAUDE.md` §6 + §3.1 (v18 Fase 0).

### D-V18-2 — Constituição main DESATUALIZADA vs worktree

- **Detectado em**: 2026-05-26 v18 (sessão começou lendo CLAUDE.md do system-reminder = main)
- **Sintoma**: `CLAUDE.md` do main dizia Skill 7 + Skill 8 = ⬜ não iniciado; worktree (feat/estoque-odoo) tinha Skill 7 V1 LIVE v17.5 + Skill 8 PIPELINE A-F v18. Sessão nova que abrisse main acharia que precisa COMEÇAR de zero.
- **Correção**: worktree atualizado v18 Fase 0; merge em main em v19+ trará a constituição reorganizada.
- **Como evitar**: PROTECAO_PROXIMA_SESSAO.md ordem de leitura — sessão DEVE estar na worktree ANTES de ler `CLAUDE.md`.

### D-V18-3 — G037 v18 criado com premissa contraditória ao docstring

- **Detectado em**: 2026-05-26 Rafael perguntou "voce leu esses 2 arquivos?" (operacoes_fiscais.py + picking_types.py)
- **Sintoma**: G037 que criei dizia "`cfop_esperado` tem USO PRATICO (nao apenas log)" enquanto `operacoes_fiscais.py:17` dizia "informacional/log. Real e decidido pelo Odoo". Premissa contraditória.
- **Causa raiz**: criei gotcha sem ler constants inteiras (`grep` em vez de `Read` completo).
- **Correção**: G037 reescrito em v18 Fase 0 com escopo restrito ao caminho B paliativo (picking ETAPA F manual sem PO). Docstring de `operacoes_fiscais.py` clarificado para incluir o caso degenerado.
- **AP5 codificado**: novo antipadrão "criar gotcha sem ler docstrings de constants" no §6.5.

### D-V18-4 — Subagente prompt acumulava invariantes históricas ("NOVA v7", "NOVA v8"...)

- **Detectado em**: 2026-05-26 v18 análise de drift documental
- **Sintoma**: `.claude/agents/gestor-estoque-odoo.md` tinha 13 invariantes invioláveis, 7 começando com "NOVA vX — lição da sessão XYZ". Prompt cresceu sem decay.
- **Correção**: invariantes reduzidas para 8-10 atemporais em v18 Fase 0; lições históricas viram referências `[[memory-pattern]]`.
- **Como evitar**: PROTECAO_PROXIMA_SESSAO.md N6 — "NUNCA adicionar invariante histórica no prompt do subagente".

### D-V18-5 — ROADMAP_SKILLS HANDOFF crescia sem decay (807 linhas)

- **Detectado em**: 2026-05-26 v18 análise de drift documental
- **Sintoma**: cada sessão (v13 até v18) adicionava bloco "Sessao 2026-05-XX vXX" no ROADMAP HANDOFF (~50-70 linhas/sessão). Em 10 sessões = 500+ linhas só de histórico no documento de PRÓXIMO PASSO.
- **Correção**: histórico migrado para `VALIDACAO_FINAL_SESSAO.md` em v18 Fase 0; ROADMAP reduzido a ≤80 linhas (estado atual + próximo passo).
- **Como evitar**: PROTECAO_PROXIMA_SESSAO.md N7 — "NUNCA adicionar bloco Sessao XYZ no ROADMAP HANDOFF".

### D-V19-1 — "Skill 8 delega" é semanticamente errado (skills não delegam)

- **Detectado em**: 2026-05-26 v19+ Rafael corrigiu minha frase "Skill 8 = SAÍDA delega Skill 2, B Skill 5..."
- **Sintoma**: confusão nomenclatura "Skill 8 = orchestrator C3 pipeline A-F" induz pensar que skills L2 delegam. Skills L2 são átomas (1 objeto, 1 responsabilidade). Composição = orchestrator C3 ou FLUXO L3.
- **Correção**: AP6 documentado em §6.5; refator nomenclatura v20+ separa Skill 8 ATÔMICA L2 (a definir) do `inventario_pipeline` C3 (atual orchestrator).
- **Como evitar**: ao referenciar "Skill 8", especificar **ATÔMICA L2** vs **orchestrator C3 (pipeline inter-company)**. Skills L2 não compõem outras skills — quem compõe é FLUXO L3 ou orchestrator.

### D-V19-2 — `criar_dfe_manual` sem XML não é viável via XML-RPC (lição mineração)

- **Detectado em**: 2026-05-26 v19+ mineração `RecebimentoLfOdooService` via Explore
- **Sintoma**: plano inicial v19+ propunha átomo `criar_dfe_manual(dados_campo_a_campo)` para criar DFe sem XML. Realidade: service externo SEMPRE faz `create('l10n_br_ciel_it_account.dfe', {'company_id': X, 'l10n_br_xml_dfe': xml_b64})`. Odoo parseia tudo via `action_processar_arquivo_manual`. Sem XML não há caminho suportado.
- **Correção v19+**: átomo renomeado para `criar_dfe_a_partir_do_invoice_saida(invoice_id_saida, company_destino)` — extrai `account.move.l10n_br_xml_aut_nfe` (XML autorizado já existente em qualquer NF SEFAZ-OK) e usa como input. Para NF nossa (transferência interna FB↔LF↔CD), XML existe; para CTe/Compras (externos), átomo recusa.
- **Como evitar**: ANTES de propor átomo cross-skill que toca Odoo, minerar o pattern equivalente já validado em PROD (Explore READ-only — não MEXER no código-fonte se for marcado NÃO MEXER).

### D-V24-1 — AP6 nomenclatura "Skill 8 = orchestrator C3" RESOLVIDO PARCIAL via criar Skill 8 ATÔMICA L2 separada (2026-05-27)

- **Detectado em**: 2026-05-27 v24+ início — sessão pulou S1 bulk REAL PROD (ciclo INVENTARIO_2026_05 só tinha 2 ajustes museum 176013/14 F5f_ENTRADA_OK; FATURAMENTO_LF_2026_05_20 só PERDA/DEV destino=FB não-suportado pelas CONSTANTS atuais; 30 INDUSTR em F5d_BLOCKER_TX = risco SEFAZ reincide) → escolha Rafael: refator AP6 puro código.
- **Sintoma**: catálogo §6 tabela 2 catalogava `faturando-odoo` como orchestrator C3 + tinha fachada SKILL.md fingindo ser skill L2 (inerentemente inconsistente — orchestrators C3 não são skills L2). Operações C+D do orchestrator (ETAPAS C+D ~1500 LOC inline) duplicavam lógica que deveria viver em Skill 8 ATÔMICA dedicada sobre `account.move`.
- **Causa raiz histórica**: AP6 documentado v19+ como pendente v20+ → mantido pendente v20+/v21+/v22+/v23+ por priorização de outros fixes (G-AUDIT-1/2/3, G038, G039, B-V23-1/2). v24+ finalmente endereçou.
- **Correção v24+ (2026-05-27)**:
  - ✅ Criada Skill 8 ATÔMICA L2 em `app/odoo/estoque/scripts/faturamento.py` (FaturamentoInvoiceService, ~750 LOC) com 5 átomos espelhando padrão Skill 7 ABRANGENTE v19+: `validar_invoice_constants` · `liberar_faturamento` · `polling_invoice` · `validar_invoice_pos_robo` · `transmitir_sefaz`.
  - ✅ Decisão arquitetural: **5 átomos SEPARADOS** (Rafael v24+) — contradiz recomendação inicial do Explore (1 átomo macro). Justificativa: macro é DEPRECATED pattern (wrapper Skill 7 V1 STRICT) violava AP1+AP4; átomos separados permitem recovery isolado por etapa + dry-run-first natural + idempotência por átomo + composição via FLUXO L3 ou orchestrator C3.
  - ✅ 28 pytest verdes (`tests/odoo/services/test_faturamento_invoice_service.py`) cobrindo: validar_constants (4 testes — OK/divergência/invoice não existe/campo inválido); liberar_faturamento (5 testes — dry-run/bloqueado sem confirmar/picking não done/picking não existe/OK delega Skill 5); polling_invoice (4 testes — dry-run/OK/timeout/exceção); validar_invoice_pos_robo (5 testes — dry-run/bloqueado/perfil inválido/OK todas sub-etapas/OK_PARCIAL); transmitir_sefaz (8 testes — dry-run/bloqueado/ajustes vazios/OK propaga chave/idempotent skip/HARD_FAIL_CONFIG/CRITICAL-1 commit pós-SEFAZ/falha cstat) + 2 sanity constants.
  - ✅ Baseline pytest: 622 → 650 verdes (+28 net).
  - ✅ SKILL.md `.claude/skills/faturando-odoo/SKILL.md` reescrita: frontmatter aponta para "Skill 8 ATÔMICA L2 v24+" + corpo adiciona seção "5 ÁTOMOS L2" com contratos + exemplo composição.
  - ✅ §6 Tabela 1 adicionada entry `faturando-odoo` ATÔMICA L2.
- **PENDENTE v25+ (refator profundo)**:
  - Opt-in `--usar-skill8-atomica-v25` no orchestrator (pattern espelhado de `--usar-fluxo-l3-v19`): ETAPAS C+D do `executar_pipeline_bulk` delegariam à nova Skill 8 ATÔMICA em vez de lógica inline. Default OFF preserva 100% legacy = zero regressão.
  - ✅ FEITO (v27+ S3): renomeado `faturamento_pipeline.py` → `inventario_pipeline.py`; stub alias removido v28+ S6.b.
  - Canary REAL PROD do opt-in em 1-5 ajustes para validar paridade vs legacy.
  - Após canary OK: remove ETAPAS C+D legacy (~500 LOC) + migrar 14 testes para `test_faturamento_invoice_service.py`.
- **LIÇÃO ATEMPORAL**: refators arquiteturais de larga escala (4400+ LOC orchestrator) devem seguir padrão "criar novo + opt-in + canary + remove legacy" em vez de big-bang. Pattern provado v20+ (`--usar-fluxo-l3-v19`) + v24+ (atômica Skill 8 criada antes de migrar orchestrator).
- **Onde**: `app/odoo/estoque/scripts/faturamento.py` + `tests/odoo/services/test_faturamento_invoice_service.py` + `.claude/skills/faturando-odoo/SKILL.md` + §6 Tabela 1 + §6.5 AP6 atualizado.

### D-V23-3 — Skill 7 `gerar_po_from_dfe`/`preencher_po` deixa PO.line.account_id em company FONTE (B-V23-2 ✅ CODIFICADO v23.5+)

- **Detectado em**: 2026-05-27 v23+ S3 reprodução PROD passo 9 `action_create_invoice` após fix D-V23-2.
- **Sintoma**: `<Fault 2: Empresas incompatíveis nos registros: 'C2619591: [210010800] ...' pertence à empresa 'LA FAMIGLIA - LF' e 'Account' (account_id: '3202010001 CUSTOS DAS MERCADORIAS VENDIDAS') pertence a outra empresa>`. `action_gerar_po_dfe` cria PO.lines no destino (company=LF=5) mas `account_id` é resolvido para `account.account` da FB (id=22611 '3202010001') em vez do equivalente LF (id=26459). Cada code de conta existe em todas 4 companies.
- **Causa raiz**: robô CIEL IT executa `action_gerar_po_dfe` com context herdado do criador (Rafael company principal=FB). Account resolver default usa company atual do user, não company da PO.
- **Workaround v23+ aplicado (manual write)**: PO.lines 128461/62 account_id 22611 (FB) → 26459 (LF).
- **FIX v23.5+ (CODIFICADO)**:
  - Novo átomo Skill 7 `resolver_account_id_por_company(account_id_fonte, company_destino)` em `escrituracao.py:1310+`: read code do fonte + search [(code,=,code),(company_id,=,destino)]. Status: OK_EXISTE / JA_NA_DESTINO / NAO_EXISTE_DESTINO / FALHA.
  - Hook em `gerar_po_from_dfe` após status='CRIADO' (PO recém-criada): itera PO.lines + resolve account equivalente da line.company_id + batch write por account_id_destino. NAO toca status=IDEMPOTENT_EXISTE (PO já existia).
  - Account inexistente em destino: warning log + line preserva account divergente (caller detecta no passo 9 com diag claro). NON-fatal: warning preserva status=CRIADO.
  - 9 pytest (5 átomo + 4 hook).
- **Onde**: `app/odoo/estoque/scripts/escrituracao.py:1310-1421` átomo + `:1604-1701` hook.

### D-V23-2 — Skill 7 `criar_dfe_a_partir_do_invoice_saida` cria dfe.lines com `company_id` herdado do XML da SAÍDA (B-V23-1 ✅ CODIFICADO v23.5+)

- **Detectado em**: 2026-05-27 v23+ S3 reprodução PROD passo 9 `action_create_invoice`.
- **Sintoma**: `<Fault 4: 'Rafael (id=42) não tem acesso "leitura" a: Item Documento Fiscal (l10n_br_ciel_it_account.dfe.line)'>`. DFe criado no LF (company=5) MAS dfe.lines herdam company=1 (FB) do XML da saída. Método CIEL IT faz `with_company(dfe.company_id=5)` reduzindo `allowed_company_ids=[5]`; lines company=1 não passam pela ir.rule id=353 'dfe_line multi-company' nesse contexto reduzido.
- **Causa raiz**: `action_processar_arquivo_manual` parsea XML da NF de SAÍDA (que tem company=1 emitente) e propaga company_id da fonte para as filhas, em vez de forçar company_id do pai DFe.
- **Workaround v23+ aplicado (manual write)**: dfe.lines 129585/86 company_id 1 (FB) → 5 (LF).
- **FIX v23.5+ (CODIFICADO)**:
  - `criar_dfe_a_partir_do_invoice_saida` em `escrituracao.py:1066-1108`: após `_fire_and_poll`, search dfe.lines por dfe_id + read company_id de cada + identifica divergentes + batch write `company_id=company_destino`.
  - Idempotente (skip write se já alinhado). NON-fatal (warning log preserva status=CRIADO se write falhar — caller detecta erro original com diag claro).
  - 3 pytest cobrindo: corrige + idempotent + falha non-fatal.
- **Onde**: `app/odoo/estoque/scripts/escrituracao.py:1046-1108`.

### D-V23-1 — G039 purchase.team gatekeeper LF (✅ CODIFICADO v23+)

- **Detectado em**: 2026-05-27 v22+ resume F pós-G-AUDIT-3 fix.
- **Sintoma**: PO criada via FLUXO L3 1.2.x cai em `team_id=41` 'Aprovação LF - JOSEFA' (user_id=78 Edilane) default. `button_confirm` retorna True mas state fica 'to approve' permanente; `button_approve` via XML-RPC não destrava quando user de execução (Rafael uid=42) não é o user do team. Resultado: sem picking auto, `FALHA_PASSO_7_SEM_PICKING`.
- **Causa raiz**: regra CIEL IT custom de aprovação dupla por valor/regra (~PO state='to approve' permanente para non-aprovador).
- **Workaround v22+ aplicado (manual write)**: criado `purchase.team` id=143 'Aprovação LF - RAFAEL' (user_id=42, company_id=5) + write PO 42419 team_id=143.
- **FIX v23+ (CODIFICADO)**:
  - Átomo `escrituracao.garantir_purchase_team(user_id, company_id, dry_run)`: busca por (user_id, company_id, active=True); CREATE com nome template "Aprovação {sigla} - {primeiro_nome}" se não existe.
  - Hook `_resolver_team_g039` no orchestrator `faturamento_pipeline.py` com cache local `_g039_team_cache: Dict[(uid, company_id), team_id]`; lazy auth; substitui `team_id` STATIC no `_resolver_constants_fluxo_l3` pelo team correto. Fallback silencioso (warning + STATIC) se hook falhar.
  - 14 pytest (7 átomo + 7 hook).
- **Onde**: `app/odoo/estoque/scripts/escrituracao.py:674-870` (átomo) + `app/odoo/estoque/orchestrators/faturamento_pipeline.py:3120-3240` (hook).

### D-V22-3 — Caminho B FLUXO L3 1.2.x cria PO sem `fiscal_position_id` + `purchase.team` errado (G039 ✅ CODIFICADO v23+)

- **Detectado em**: 2026-05-27 v22+ resume F pós-G-AUDIT-3 fix + G038 fix. FLUXO L3 1.2.2 (caminho B — `criar_dfe_a_partir_do_invoice_saida` + `action_gerar_po_dfe` + `button_confirm`) executou com sucesso até criar **DFe 43533** (com 2 linhas populadas) + **PO 42419 'C2619591'** (order_line correta) MAS PO ficou em `state='to approve'` (não 'purchase'). Sem confirm = sem picking = `FALHA_PASSO_7_SEM_PICKING: po_sem_picking_pos_confirm`.
- **Sintoma combinado**:
  - PO sem `fiscal_position_id` (campo False)
  - PO `team_id=41` 'Aprovação LF - JOSEFA' (user_id=78 Edilane) — team default não permitia aprovação por Rafael (uid=42 user_id da PO)
  - `button_confirm` retornou True mas state manteve 'to approve'
  - `button_approve` retornou None sem mudança de state
  - `action_approve`/`approve`/`action_confirm` não existem (não há method genérico para destravar 'to approve' via XML-RPC; provavelmente regra CIEL IT custom requer UI ou group específico que Rafael não tem)
- **Causa raiz parcial conhecida**: Caminho B (criar DFe via XML da saída) não popula `fiscal_position_id` na PO + usa `purchase.team` default que pode não ter aprovador correto. Aprovação dupla (CIEL IT custom) bloqueia.
- **Workaround v22+ aplicado (manual write)**:
  - Criado `purchase.team` id=143 'Aprovação LF - RAFAEL' (user_id=42 Rafael, company_id=5 LF) via XML-RPC
  - PO 42419 movida para team 143 via write
  - Estado ainda 'to approve' (mudar team não destrava por si só)
  - Rafael aprova manualmente no UI Odoo OU investiga regra exata v23+
- **NOVA INVARIANTE v22+** (a codificar em v23+): ao criar PO no LF via FLUXO L3 1.2.x (caminho A ou B), Skill 7 (ou orchestrator) DEVE garantir:
  1. `purchase.team` existe para o user_id atual (ou Rafael uid=42) — criar via XML-RPC se não existir
  2. PO setada com `team_id` correto antes de `button_confirm`
  3. (Opcional) Validar `fiscal_position_id` populado antes de confirmar (caminho B descobriu que action_gerar_po_dfe não popula esse campo em todos casos)
- **Pendências v23+**: (a) investigar canary 627348 (caminho A SEFAZ-via-DFe que autorizou) — fiscal_position estava populada? team_id qual? (b) descobrir regra exata de 'to approve' (valor mínimo? group `purchase.group_purchase_manager`? regra CIEL IT customizada?); (c) Skill 7 codificar invariante purchase.team + fiscal_position fallback.
- **Onde**: PO 42419 + DFe 43533 + invoice 716448 + Team 143 ficam como museum vivo. Tasks 13+14 do TaskList v22+. Gotcha G039 (planejado, ainda não criado).

**v22+ CONTINUAÇÃO PASSO 9 (action_create_invoice)**: após team 143 destravar PO + gerar picking 321617, retry F falhou em PASSO 9 com: `Rafael (id=42) não tem acesso 'leitura' a: Item Documento Fiscal (l10n_br_ciel_it_account.dfe.line)`. Investigação: Rafael TEM grupos `ir.model.access` necessários (28 Accounting/Billing + 1 Internal User), mesmo que Edilane (uid=78). Causa NÃO é access — é `ir.rule` (record-level) ativa em dfe.line que filtra para Rafael apesar de ter company LF=5. Investigação exata pendente v23+ (task 15). Workaround imediato: rodar pipeline com user com permissão (Edilane uid=78).

### D-V22-2 — `product.l10n_br_origem` ausente bloqueia SEFAZ via modal Odoo silencioso (G038 RESOLVIDO via Sub-skill C5)

- **Detectado em**: 2026-05-27 v22+ retry pipeline `INVENTARIO_2026_05` — Playwright em loop 15 tentativas sem efeito; screenshots `/tmp/sefaz_debug/pos_sefaz_inv716448_t*.png` mostraram modal "Aviso do Odoo: Produtos sem Origem".
- **Sintoma**: invoice 716448 (`state=posted, situacao_nf='rascunho', show_nfe_btn=True`) com `cstat=False, xmotivo=False` após 15 cliques Playwright em "Transmitir NF-e" (~28min). Comparação com canary autorizado (627348) — config fiscal IDÊNTICA exceto que canary tinha `l10n_br_origem='0'` e nosso tinha `False`.
- **Causa raiz**: `product.product.l10n_br_origem` é OBRIGATÓRIO para NF-e (Tabela A SEFAZ). Quando vazio, Odoo CIEL IT intercepta `action_gerar_nfe` ANTES de SEFAZ com modal nativo. Playwright `_tratar_wizard_confirmacao` (`app/recebimento/services/playwright_nfe_transmissao.py:216`) só trata wizard padrão — modal específico passa silencioso.
- **Correção v22+ (2026-05-27)**:
  - Sub-skill C5 estendida com check G038 em `_check_ncm_weight_tracking` (adiciona `l10n_br_origem` no read + retorna `origem_ausente`)
  - `auditar_perfil_inventario` inclui `origem_ausente` em `bloqueios` (PRE_FLIGHT_BLOQUEADO)
  - Sem auto-fix (orquestrador não sabe a origem correta — depende cadastro). Operador seta manualmente.
  - 2 pytest novos: `test_check_ncm_weight_tracking_g038_origem_ausente_bloqueia` + `test_auditar_perfil_inventario_bloqueia_g038_origem_ausente`
  - Gotcha G038 documentado: `docs/inventario-2026-05/02-gotchas/G038-l10n-br-origem-ausente-bloqueia-sefaz.md`
  - Cross-ref atualizada: `.claude/references/odoo/GOTCHAS.md` tabela G011-G038
- **LIÇÃO ATEMPORAL (similar AP5)**: validações fiscais do Odoo CIEL IT podem ser silenciosas via MODAL UI (não exception XML-RPC). Quando Playwright detecta cstat=False persistente após click — **sempre tirar screenshot e inspecionar visualmente** se há modal interceptando. Se houver, gotcha → pre-flight check ANTES do pipeline.
- **Onde**: `PROTECAO_PROXIMA_SESSAO.md` (N24 NOVO se quiser adicionar) + Sub-skill C5 service estendido.

### D-V22-1 — Idempotência por origin reaproveitava picking state=cancel (G-AUDIT-3 RESOLVIDO)

- **Detectado em**: 2026-05-27 v22+ retry pipeline `INVENTARIO_2026_05` ajustes 176013/176014 — picking 321600 estava em state=cancel (cleanup do retry anterior) e Skill 5 `criar_picking_inter_company` reaproveitava-o erroneamente; `action_assign` na ETAPA F5b retornava `<Fault 2: 'Nada para verificar a disponibilidade.'>` (cancel não tem moves para reservar).
- **Sintoma**: pipeline crashava em F5b com mensagem genérica "Nada para verificar". Ajustes ficavam `fase_pipeline='F5b_FALHA'` + `picking_id_odoo=<cancel>` + `erro_msg=<Fault 2>`. Não progride no retry porque idempotência continua a reaproveitar o mesmo cancel.
- **Causa raiz**: bloco de idempotência em `picking.py:944-981` v15c F1 buscava `[['origin', '=', origin]]` e retornava o PRIMEIRO match SEM filtrar state. Estados válidos para reaproveitar: `draft/confirmed/assigned/done`. State=cancel = registro morto.
- **Correção v22+ (2026-05-27)**: `picking.py:944-1006` segrega cancelados; se TODOS são cancel, prossegue para create (cria NOVO); se mistura, prefere o primeiro vivo e loga skip dos cancelados. 2 pytest novos (`test_..._g_audit_3_pula_pickings_cancelados` + `test_..._g_audit_3_prefere_vivo_sobre_cancel`). Baseline 578 verdes.
- **LIÇÃO ATEMPORAL**: ao implementar idempotência por chave externa (origin, external_id, etc.), SEMPRE filtrar `state=cancel` (ou equivalente "registro morto") da busca, OU segregar e logar. Idempotência ingênua que "reaproveita o que existir" gera deadlock retry quando retries criam cancelados.
- **Onde**: `PROTECAO_PROXIMA_SESSAO.md` N23 (RESOLVIDO v22+) + `picking.py:918-931` (docstring atualizado).

### D-V18-6 — Acúmulo de `PROMPT_PROXIMA_SESSAO_*.md` no root

- **Detectado em**: 2026-05-26 v18 Fase 0 (auditoria Rafael — "Existem N prompts; sanitize")
- **Sintoma**: 8 prompts cumulativos em `app/odoo/estoque/`: 1 atual + 7 com sufixo `_EXECUTED_<data>`. Sessão nova confusa sobre qual é o "vivo"; root poluído; SHA do commit em cada prompt acumulava metadata.
- **Causa raiz**: cada sessão criava `PROMPT_PROXIMA_SESSAO.md` novo mas não havia pasta de destino para o executado; sufixo era convencionado mas sem regra clara.
- **Correção**: criada pasta `_prompts_executados/` + movidos 8 prompts antigos para lá. Convenção atemporal codificada em `PROMPT_PROXIMA_SESSAO.md §0 + §6.2`: (1) 1 só vivo no root; (2) executado renomeado para `_prompts_executados/PROMPT_..._vXX_EXECUTED_<data>.md` ANTES do commit final; (3) §0/§1/§6 atemporais (copiar literal); (4) §2-§5 por-sessão (reescrever para N+1).
- **Como evitar**: `PROTECAO_PROXIMA_SESSAO.md` N14 + N15. Ao terminar sessão, seguir `PROMPT_PROXIMA_SESSAO.md §6.2`.

---

## 15. PRINCÍPIOS QUE NÃO PODEM SER OMITIDOS (consolidado v18 Fase 0)

Lista mínima de princípios que TODA sessão precisa internalizar. Se algum não está claro, **PARAR e re-ler CLAUDE.md**:

1. **1 SKILL = 1 OBJETO ODOO** (§1.1). Sem exceção. 2+ objetos = orchestrator C3 (Tabela 2), não skill L2 (Tabela 1).
2. **Orchestrator C3 NÃO é skill** (§3.1). Mora em `orchestrators/`, não no catálogo de skills.
3. **Átomo NUNCA embute outro fluxo** (§3 regra de ouro). Composição = FLUXO L3 (Markdown).
4. **Fluxos >> skills** (§4). Caso novo = nova FOLHA L3; nunca skill nova.
5. **Dry-run antes do real** (§12). Pre-cond raise APENAS no caminho WRITE.
6. **NÃO improvise** (§9). Skill não existe = parar e avisar Rafael.
7. **Ler docstrings de CONSTANTS** antes de criar gotcha sobre operações fiscais (lição AP5/D-V18-3).
8. **Prompt do subagente = atemporal** (D-V18-4). Lições viram memories, não inline.
9. **ROADMAP HANDOFF = estado atual + próximo passo** (D-V18-5). Histórico em VALIDACAO.

> Estes 9 itens vivem em `PROTECAO_PROXIMA_SESSAO.md` como **lista negra + lista de obrigações**, navegáveis rapidamente. Esta seção §15 é o âncora canônico.
