# app/odoo/estoque — Operações de Escrita de Estoque no Odoo

**Status:** EM CONSTRUÇÃO (ONDA 0 concluída 2026-05-22; ONDA 0.4 ✅ fechada 2026-05-24 v3 — G019/G020 codificadas no service; **Skill 2 `transferindo-interno-odoo` ✅ MATURADA**; **Skill 5 `operando-picking-odoo` 🟡 ESTENDIDA v15a + F1 IDEMPOTENCIA v15c** — 3 atomos inter-company; **Skill 6 `planejando-pre-etapa-odoo` 🟡 mín viável COMPLETA v9**; **Skill 7 `escriturando-odoo` 🟡 mín viável V1 LIVE v17.5** — antipadrao V1 STRICT documentado para refator v19+; **Skill 8 `faturando-odoo` 🟡 PIPELINE COMPLETO A-F LIVE + RECOVERY v18** — `app/odoo/estoque/orchestrators/faturamento_pipeline.py` compoe Skill 5 + Skill 2 v2 + Playwright SEFAZ + atomo Skill 7 + atomo Skill 5 entrada destino. **v18 (2026-05-26): RECOVERY `executar_pipeline_resume` + SKILL.md Skill 8 + G037 NOVO**. Recovery substitui scripts shell `fat_lf_resume.sh` + `fat_lf_resume_entrada.sh` por modo CLI `--modo resume --apenas-etapa B/C/D/E/F` (loop iterativo + detector_stagnation + max_iter; 8 pytest mockados novos). SKILL.md `.claude/skills/faturando-odoo/SKILL.md` criada com 4 receitas + secao ANTIPADROES DETECTADOS V17.5 + checklist expansao v19+. G037 (NOVO em `docs/inventario-2026-05/02-gotchas/G037-operacao-nao-cadastrada-exige-cfop-explicito.md`): MATRIZ_INTERCOMPANY[acao]['cfop_esperado'] tem USO PRATICO (nao apenas log). 1 code-reviewer paralelo (4 findings — 1 CRIT + 3 HIGH aplicados: F1 contador inclui F5x_FALHA, F3 `--timeout-iter` lying parameter clarificado, F2+F4 doc adicional SKILL.md). **521 pytest verdes** (513 baseline v17.5 + 8 net v18). Smokes dry-run PROD: resume B/D/E/F + FALHA_USO log em `/tmp/log_skill8_smokes_v18_*.json`. | **Atualizado:** 2026-05-26 v18
**Audiência:** Claude Code (dev) + agente web. Doc **machine-first** — contratos e regras.

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
| `transferindo-interno-odoo` | transferência interna intra-empresa — **4 modos atômicos** (v21+): A lote→lote mesma loc / B loc→loc mesmo lote / C MIGRAÇÃO↔Indisp / **D loc+lote em 1 chamada (NOVO v21+)** | `scripts/transfer.py` (delega `ajustar_quant`×2 com `delta_esperado` propagado; G021/G022/G027) | C2 | 🟡 **44 pytest verdes** (33 v20+ + 11 net v21+ Skill 2 átomo NOVO `transferir_loc_e_lote`); 2 scripts SUPERADOS 2026-05-24; átomo D validado em PROD ETAPA 0 v21+ (250.330 SLEEVE + 1,8 CORANTE Indisp/MIGRAÇÃO → Estoque/P-15/05) |
| `operando-mo-odoo` | mrp.production (cancelar — V1; criar/alterar sem demanda) | [`scripts/mo.py`](scripts/mo.py) (StockMOService — guard G-MO-01 furo contabil) | C2 | 🟡 **mín viável** (26 pytest verdes; 4 dry-run PROD validados) |
| `operando-reservas-odoo` | stock.move.line + stock.quant (residual) — opera reservas órfãs do picking | [`scripts/reserva.py`](scripts/reserva.py) (StockReservaService) | C1/C2 | 🟡 **mín viável** (3 átomos · 6 pickings/15 quants em prod) |
| `operando-picking-odoo` | stock.picking (cancelar/validar/devolver + 3 átomos inter-company v15a + 1 átomo NOVO v19+ `preencher_lotes_picking`; `criar_picking_entrada_destino_manual` 🛑 DEPRECATED v19+ AP2) | [`scripts/picking.py`](scripts/picking.py) (StockPickingService) | C2 | 🟡 **7 átomos LIVE v19+ + G-AUDIT-3 fix v22+** (70 pytest = 68 + 2 net v22+ idempotência cancel; G019/G020 fechada + G-AUDIT-3 codificada) |
| `escriturando-odoo` ✅ ABRANGENTE v19+ + G039 v23+ + B-V23-1/2 v23.5+ | account.move + DFe (entrada — escritura NF SEFAZ-OK no destino) | [`scripts/escrituracao.py`](scripts/escrituracao.py) (EscrituracaoLfService) | **HÍBRIDO** — V1 STRICT `criar_recebimento_orchestrado` (wrapper deprecado v20+) + **9 átomos ABRANGENTES**: 7 v19+ (`buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida` ⚡com fix B-V23-1 v23.5+ batch write dfe.line.company_id pós-poll⚡, `escriturar_dfe`, `gerar_po_from_dfe` ⚡com hook B-V23-2 v23.5+ batch write PO.line.account_id por company⚡, `preencher_po`, `confirmar_po`, `criar_invoice_from_po`) + 2 v23+/v23.5+ (`garantir_purchase_team` G039 idempotente por user+company, `resolver_account_id_por_company` helper B-V23-2). Compostos via FLUXO L3 1.2.1/1.2.2 (caminho A/B) | 🟡 **ABRANGENTE LIVE** (45 pytest = 11 V1 + 22 v19+ + 7 G039 + 3 B-V23-1 + 5 B-V23-2 átomo + 4 B-V23-2 hook gerar_po; PROD canary v23+: invoice ENTIN/2026/05/0055 posted; AP1+AP4 ✅; G039+B-V23-1+B-V23-2 ✅ |
| `faturando-odoo` ✅ ATÔMICA v24+ (NOVA — AP6 refator) | account.move (NF SAIDA inter-company) | [`scripts/faturamento.py`](scripts/faturamento.py) (FaturamentoInvoiceService) | **ATÔMICA L2** — **5 átomos** espelhando Skill 7 ABRANGENTE v19+: `validar_invoice_constants` (READ pre-cond) · `liberar_faturamento` (delega Skill 5 LEGACY) · `polling_invoice` (delega Skill 5 LEGACY `aguardar_invoice_do_robo`) · `validar_invoice_pos_robo` (G029+G007+G034 via `_invoice_helpers`) · `transmitir_sefaz` (Playwright IRREVERSIVEL + D7 HARD_FAIL + D8.3 idempotência + CRITICAL-1 commit pós-SEFAZ + MED C-1/C-2 cstat). Composição via FLUXO L3 1.1.x (saida pura ⬜) ou via orchestrator C3 LEGACY `inventario_pipeline` (migração v25+) | 🟡 **ATÔMICA LIVE v24+** (28 pytest verdes; ~750 LOC; AP6 RESOLVIDO PARCIAL — orchestrator C3 LEGACY ainda usa lógica inline em paralelo; migração para usar os 5 átomos planejada v25+ via opt-in `--usar-skill8-atomica-v25`) |

> **Nota Tabela 1**: estas são as únicas skills WRITE atômicas L2. Cada uma tem `.claude/skills/<nome>/SKILL.md` + scripts/. O subagente as conhece pela árvore de decisão.

### Tabela 2 — Skills READ ancillary L2 (sob demanda — complementam as WRITE)

| Skill | Objeto Odoo | Service base (L1) | Camada | Status |
|-------|-------------|-------------------|--------|--------|
| `consultando-quant-odoo` | stock.quant (read ao vivo via XML-RPC) — 3 modos: quants / move-lines / pickings | [`scripts/consulta_quant.py`](scripts/consulta_quant.py) (StockQuantQueryService) | READ | 🟡 **mín viável** (3 átomos · cross-ref ML→quant via tupla G030) |

### Tabela 3 — Orchestrators C3 macros (L1 — NÃO são skills L2)

> Compõem skills L2 para casos de negócio complexos (SEFAZ irreversível, recovery iterativo, multi-step com checkpoint). **NÃO aparecem no catálogo de skills do subagente**; ficam acessíveis via FACHADA SKILL.md ou diretamente em Python. Aceita `--dry-run` + `--confirmar` como qualquer átomo.

| Orchestrator | Composição | Service (L1) | Status | SKILL.md fachada |
|--------------|-----------|--------------|--------|------------------|
| `faturando-odoo` (Skill 8 nomenclatura confusa — ver AP6) | Skill 2 v2 (ETAPA A) + Skill 5 átomos inter-company (ETAPA B) + Playwright SEFAZ (ETAPA D) + Skill 7 atomo V1 STRICT (ETAPA E legacy) + Skill 5 v15a deprecated (ETAPA F legacy) + **NOVO v19+ `executar_fluxo_l3_1_2_x`** (compõe Skill 7 ABRANGENTE 7 átomos + Skill 5 `preencher_lotes_picking` + Skill 5 `validar` via FLUXO L3 1.2.1/1.2.2) | [`orchestrators/faturamento_pipeline.py`](orchestrators/faturamento_pipeline.py) (~4400 LOC com pipeline A-F + recovery + método v19+) | 🟡 **PIPELINE A-F + RECOVERY + FLUXO L3 1.2.x LIVE v19+** (76 pytest verdes = 72 + 4 dispatch fluxo L3; AP2 reclassificado; ETAPAS E+F legacy preservadas até v20+ canary) | `.claude/skills/faturando-odoo/SKILL.md` (FACHADA — 4 receitas v17.5 + roadmap v19+) |
| `planejando-pre-etapa-odoo` (Skill 6) | Skills 1+2 via `executar_onda_pre_etapa` (READ Odoo + WRITE banco local + WRITE Odoo C3 macro) | [`scripts/pre_etapa.py`](scripts/pre_etapa.py) (planner) + [`orchestrators/pre_etapa_executor.py`](orchestrators/pre_etapa_executor.py) (executor) | 🟡 **mín viável COMPLETA v9** (42 pytest verdes; 5 modos: planejar/propor/listar/aprovar/executar-onda) | (sem fachada externa; CLI direto) |

> **Sinais de orchestrator C3 (vs skill L2 atômica)**: toca 2+ objetos Odoo · invoca service externo + faz agregação · multi-step com checkpoint · usa Playwright/RecebimentoLf/RecLf etc. Se ≥1 sinal, é C3, vai para Tabela 2; NÃO entra na Tabela 1.

### Tabela 4 — Sub-skills PRE-FLIGHT (auditoria fiscal antes de SEFAZ)

| Sub-skill | Objeto Odoo | Service (L1) | Camada | Status |
|-----------|-------------|--------------|--------|--------|
| `auditando-cadastro-fiscal-odoo` | product.product + l10n_br_ncm + stock.lot (G014) + AjusteEstoqueInventario (D-OPS-2) | [`scripts/cadastro_fiscal_audit.py`](scripts/cadastro_fiscal_audit.py) (CadastroFiscalAuditService) | READ-only + WRITE opcional G035 | 🟡 **V1 'inventario'** (cobre G017+G018+G035+G014 + D-OPS-2/3; 14 pytest; delegada pela Skill 8 v15+) |

### Tabela 5 — Fluxos L3 (Markdown — compõem múltiplos átomos)

> Folhas em `app/odoo/estoque/fluxos/`. Carregadas SOB DEMANDA pelo subagente.

**Escritas (✅)**: 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, **1.2.1 (v19+)** (escriturar DFe caminho A), **1.2.2 (v19+)** (criar DFe a partir do XML da SAÍDA — caminho B).
**Pendentes (⬜)**: 1.1.1.1, 1.1.1.2, 1.1.1.3, 1.1.2, 1.1.3, 1.3 (transferência completa), 2.3 (transferir saldo entre códigos).

> Galho 1 NF inter-company **parcialmente destravado v19+**: 1.2.1 + 1.2.2 escritos + Skill 7 ABRANGENTE 7 átomos LIVE + Skill 5 `preencher_lotes_picking` LIVE. Galho 1.1 (saída) e 1.3 (saída+entrada compostos) permanecem ⬜ até refator v20+ que extrai Skill 8 ATÔMICA L2 do orchestrator (AP6).

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
  - **`inventario_pipeline` C3** (atual `faturamento_pipeline.py` orchestrator — rename pendente v25+): pipeline A-F + recovery + opt-in `--usar-fluxo-l3-v19` que compõe Skill 2 + Skill 5 + Skill 7 ABRANGENTE via FLUXO L3 1.2.x. ETAPAS C+D ainda têm lógica inline em paralelo (refator v25+).
- **RESOLUÇÃO PARCIAL v24+ (2026-05-27)**:
  1. ✅ Criada Skill 8 ATÔMICA L2 em `app/odoo/estoque/scripts/faturamento.py` (~750 LOC) com 5 átomos espelhando padrão Skill 7 ABRANGENTE: `validar_invoice_constants` · `liberar_faturamento` · `polling_invoice` · `validar_invoice_pos_robo` · `transmitir_sefaz`. Cada átomo dry-run-first + idempotente + invariantes G016/G019/G020/G029/G007/G034/D7/D8.3/D9/CRITICAL-1/MED C-1/MED C-2 codificados intra-átomo.
  2. ✅ 28 pytest verdes em `tests/odoo/services/test_faturamento_invoice_service.py` (baseline 622 → 650).
  3. ✅ SKILL.md fachada reescrita: frontmatter aponta para "Skill 8 ATÔMICA L2 v24+" + corpo adiciona seção "5 ÁTOMOS L2" com tabela contratos + exemplo composição típica.
  4. ✅ Tabela 1 §6 adicionada entry `faturando-odoo` ATÔMICA L2.
- **PENDENTE v25+ (refator profundo + canary)**:
  1. ⬜ Opt-in `--usar-skill8-atomica-v25` no `executar_pipeline_bulk` (similar ao `--usar-fluxo-l3-v19`): ETAPAS C+D delegam à nova Skill 8 ATÔMICA em vez de lógica inline.
  2. ⬜ Renomear `faturamento_pipeline.py` → `inventario_pipeline.py` + alias compat.
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
  orchestrators/                       orchestrators C3 macros L1 (pre_etapa_executor ✅, faturamento_pipeline ✅ v18 — pipeline A-F + recovery)
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
  - Renomear `faturamento_pipeline.py` → `inventario_pipeline.py` + alias compat (preserva 8 imports atuais).
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
