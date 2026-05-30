# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v30+ DESBLOQUEAR canary S2 via correção cadastral CFOP FB→5949 (R3b — decisão+execução fiscal Rafael) + canary REAL PROD ETAPA E v28+ S7 (após cadastro OK + lote natural) + canary opt-in `--usar-skill8-atomica-v25` + S6 cleanup (após canary).
**Base**: commit v29+ F1+F3 — agregado `executar_pipeline_bulk` detecta `'PARCIAL'` + audit trail `usuario` no FLUXO L3 (`ajuste_id_ref`) + 688 pytest verdes. **Canary S2 BLOQUEADO por cadastro CFOP** (ver §2).
**Risco**: ALTO (canary REAL toca SEFAZ irreversível; CFOP cadastral é fiscal; S6 remove ~2500 LOC legacy só após canary).
**Estimativa**: 1-3 sessões (depende correção cadastral CFOP + lote natural).

> **Criado em**: 2026-05-29 v29+ EXECUTED (sucessor que executou follow-up CR F1+F3 + auditoria CFOP READ; canary S2 deferido por bloqueio cadastral).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20,21,22,23,24,25_S0,26_PARTIAL,27,28,29}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

---

## §0. CONVENÇÃO DESTE ARQUIVO (atemporal — NÃO ALTERAR sem refator estrutural)

> **Regra de manutenção** (idêntica em todas as sessões):
>
> 1. **Um único `PROMPT_PROXIMA_SESSAO.md` vive no root de `app/odoo/estoque/`**. Sempre 1, nunca 2+.
> 2. Sessão executada renomeia este arquivo para `_prompts_executados/PROMPT_PROXIMA_SESSAO_v<XX>_EXECUTED_<YYYY_MM_DD>.md` ANTES do commit final.
> 3. Sessão executada CRIA um novo `PROMPT_PROXIMA_SESSAO.md` no root com o escopo da sessão N+1 (preserva §0, §1, §6 atemporais; reescreve §2, §3, §4, §5).
> 4. **NÃO MEXER** em `PROTECAO_PROXIMA_SESSAO.md` (escudo atemporal — separado deste PROMPT).
> 5. Histórico cronológico vai em `VALIDACAO_FINAL_SESSAO.md` (regra D-V18-5 do `CLAUDE.md §14`).
>
> **Estrutura padrão de TODA versão**:
> - §0 — Convenção (atemporal — copiar literal)
> - §1 — Primeiro passo (atemporal — copiar literal)
> - §2 — Contexto atual (sessão N atualiza para N+1)
> - §3 — Escopo desta sessão (sessão N decide para N+1)
> - §4 — Checklist desta sessão (sessão N detalha para N+1)
> - §5 — Riscos e mitigações (sessão N elabora para N+1)
> - §6 — Ao terminar (atemporal — copiar literal)

---

## §1. PRIMEIRO PASSO (OBRIGATÓRIO — NÃO PULAR)

> Antes de fazer QUALQUER COISA na sessão (incluindo responder ao usuário com plano detalhado), seguir esta ordem rigorosamente:

### 1.1 Setup técnico (worktree obrigatória)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git log --oneline HEAD..origin/main | head -10   # rebase se main avançou
```

### 1.2 Leitura obrigatória em ordem

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N33 + AR1-AR14 + lições memories; atenção especial a N32 marcada OBSOLETA pós-v28+ S6.b — lição atemporal preservada).
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo — `inventario_pipeline` v28+ S7 tem helper E + stub removido v28+ S6.b) + §6.5 (antipadrões) + §14 (histórico desvios — **D-V29-1 NOVO**: F1 agregado PARCIAL + F3 audit trail usuario + achado CFOP 5902 cadastral; D-V28-1 destravamento ETAPA E) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer (S7+S6.b v28+ marcados ✅; v29+ canary REAL).
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`app/odoo/estoque/CIRURGIA_AVULSO_FRASCO_2026_05_27.md`** — análise root cause + 5 falhas + 4 fixes F1-F4 ✅ CODIFICADOS v25+ (LEITURA OBRIGATÓRIA se sessão rodar canary REAL).
7. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
8. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
9. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.
10. **`app/odoo/estoque/scripts/faturamento.py`** (v24+) — 5 átomos Skill 8 ATÔMICA L2.
11. **`.claude/skills/faturando-odoo/SKILL.md`** — fachada (paths apontam para inventario_pipeline).
12. **`app/odoo/estoque/fluxos/1.1.1-faturamento-saida-pura.md`** + **`1.3-transferencia-completa.md`** — folhas L3 v27+ S5.
13. **`app/odoo/estoque/orchestrators/inventario_pipeline.py`** (v29+ F1+F3; ~6230 LOC — linhas APROXIMADAS, localizar via `grep -n "def <nome>"`):
    - `executar_fluxo_l3_1_2_x` def ~2769 (assinatura strict + `usuario`/`ciclo`/`ajuste_id_ref` F3 v29+; closure `_passo` audita por passo)
    - `_executar_etapa_f_via_fluxo_l3` def ~3465 (template — ACOES_ENTRADA_DESTINO_MANUAL)
    - `_executar_etapa_e_via_fluxo_l3` def ~3682 (v28+ S7 — ACOES_ENTRADA_FB)
    - `executar_etapa_e` def ~4460 (dispatch v28+ S7)
    - agregado de status (F1 v29+ `'PARCIAL' in s`) ~5545

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 688 passed (v29+ F1+F3 baseline)
```

Se ≠ 688 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v29+ — FINALIZADA — F1+F3 + auditoria CFOP; canary S2 BLOQUEADO por cadastro)

### Estado do código
- **Commits base**: v29+ F1+F3 (este commit) sobre v28+ S7+S6.b.
- **Baseline pytest**: **688 verdes** em ~17.3s (681 v28+ + 7 net v29+ = 4 F1 agregado PARCIAL + 3 F3 audit trail usuario).
- **Worktree**: `feat/estoque-odoo` (main NÃO rebaseado v29+ — Rafael; main avançou ~10 commits estoque/fiscal — avaliar rebase em §1.1).

### 🔴 CANARY S2 BLOQUEADO — causa cadastral CFOP (decisão+execução FISCAL Rafael — v29+ D-V29-1)
Auditoria READ (2 subagentes) confirmou: ~10 NFs LF→FB DEV tipo 4 saíram com CFOP **5902** (correto **5949**). **NÃO é bug do código** (pipeline mapeia fp 89 + tipo_pedido certos). Causa: Operação `l10n_br_ciel_it_account.operacao` **2710 'Retorno de Industrialização - Devolução'** é GENÉRICA (`partner_ids=[]`) → 5902; a **2719 'Retrabalhos'** (5949) é restrita ao CD (`partner_ids=[34]`). Engine CIEL-IT prioriza Operação com partner específico → destino FB cai na 2710. **Recomendação R3b: criar Operação LF→FB 5949 com `partner_ids=[1]` espelhando a 2719** (cadastro fiscal Odoo — FORA das skills-átomos; NÃO improvisar XML-RPC). Detalhe: `CLAUDE.md §14 D-V29-1` + PROTECAO SEMPRE-FAZER #11.
- **Enquanto o cadastro NÃO for corrigido, NÃO rodar canary S2 destino-FB** (PERDA_LF_FB/DEV_LF_FB/TRANSFERIR_CD_FB) — cada NF nasceria com 5902 (SEFAZ irreversível). Destino-LF (DEV_CD_LF) não tem esse bloqueio.
- Backlog 2026-05-20 (21/21 invoices F5e_SEFAZ_OK) já tem entrada escriturada → ETAPA E DUPLICARIA (inviável p/ canary).
- 10 NFs já emitidas (SARET/2026/00003-12; 3 cancel, 4 cce, 3 autorizadas) = pendência FISCAL Rafael.
- **F1+F3 v29+ entregues** (code-review "SHIP IT"): agregado detecta `'PARCIAL'`; `usuario` no audit trail do FLUXO L3 via `_passo`/`ajuste_id_ref` (guard registro_id NOT NULL).

### Cleanup deprecated v28+ pós-S7 (auditoria preventiva Rafael 2026-05-28)

**REMOVIDO** (NÍVEL 1 — puro código zero risco):
- Flag `permitir_etapa_a_noop_real` (DEPRECATED v16, ~12 sessões, default OFF, zero callers PROD) + branch real-run + status `EXECUTADO_ETAPA_A_NOOP_DEPRECATED` + test.
- 3 imports não-usados nivel topo de `inventario_pipeline.py` (`PAYMENT_PROVIDER_SEM_PAGAMENTO`, `ACAO_PARA_CFOP_ENTRADA`, `LOCATION_ORIGEM_ENTRADA_INDUSTR`).

**MANTIDO** (NÍVEL 2 — precisa canary REAL S6 v29+):
- Skill 5 `criar_picking_entrada_destino_manual` (DEPRECATED v19+) — ETAPA F LEGACY depende.
- Skill 7 wrapper `criar_recebimento_orchestrado` V1 STRICT (DeprecationWarning v20+) — ETAPA E LEGACY depende.

**MANTIDO** como museum vivo (sem caller direto):
- Alias `LOCATION_ORIGEM_ENTRADA_INDUSTR` em picking_types.py (backward-compat).
- `LOTES_MIGRACAO_POR_COMPANY` em locations.py (museum vivo G031).

Detalhes completos: `VALIDACAO_FINAL_SESSAO.md` bloco "Cleanup adicional v28+".

### Estado da arquitetura (v28+)

- **Orchestrator C3 LEGACY**: `app/odoo/estoque/orchestrators/inventario_pipeline.py` (~6230 LOC). **Stub `faturamento_pipeline.py` REMOVIDO v28+ S6.b** — zero imports Python ativos.
- **Skill 8 ATÔMICA L2 LIVE v24+** (`scripts/faturamento.py` 5 átomos) — inalterada v28+.
- **Skill 7 ABRANGENTE LIVE v25+** (`scripts/escrituracao.py` 10 átomos) — inalterada v28+.
- **Opt-in `--usar-skill8-atomica-v25` LIVE v27+ S1**: helpers ETAPAs C+D delegam aos átomos 3, 4, 5 da Skill 8 ATÔMICA. Default OFF preserva legacy.
- **Opt-in `--usar-fluxo-l3-v19` LIVE v20+ + v28+ S7**: ETAPAs E+F substituídas pelo FLUXO L3 1.2.x. ETAPA E v28+ S7 NOVO — helper `_executar_etapa_e_via_fluxo_l3` espelha helper F filtrando `ACOES_ENTRADA_FB` (4 ações X→FB ou X→LF: PERDA_LF_FB + TRANSFERIR_CD_FB + DEV_LF_FB destino=FB; DEV_CD_LF destino=LF). Default OFF preserva legacy.
- **CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO** v27+ S4: 3 companies (FB=1, CD=4, LF=5). FB+CD com `team_id=None` (G039 dinâmico); LF=5 com `team_id=143` STATIC FIXO (F4 v25+).
- **L10N_BR_TIPO_PEDIDO_POR_ACAO** v27+ S4: cobre 8 ações da MATRIZ_INTERCOMPANY (`{'dfe': str, 'po': str}`).
- **Folhas L3 escritas (13)**: 2.1-2.9, 3.1, 4.1, 1.2.1, 1.2.2, 1.1.1 v27+ S5, 1.3 v27+ S5.

### Estado banco local (pós-cleanup v26+ + zero mudança v27+/v28+)

- INDUSTRIALIZACAO_FB_LF F5d_BLOCKER_TX: **0** (cleanup v26+ commit `701e4885`)
- INDUSTRIALIZACAO_FB_LF F5e_SEFAZ_OK: 1 (apenas 177465 AVULSO_FRASCO — idempotente Odoo via cirurgia manual v24+)
- INDUSTRIALIZACAO_FB_LF F5f_ENTRADA_OK: 104 (concluídos)
- INDUSTRIALIZACAO_FB_LF F5f_FALHA: 0
- **DEV_LF_FB / PERDA_LF_FB em F5e_SEFAZ_OK** (backlog 2026-05-20 + lote `FATURAR_LF_FB_2026_05_29` criado por subagente): entrada já escriturada → **NÃO rodar ETAPA E sobre eles (duplica)**.

### Estado FINAL ajustes PROD (preservado v23+/v24+/v25+/v26+/v27+/v28+ — NÃO MEXIDO)

- **176013/176014**: `status='EXECUTADO', fase_pipeline='F5f_ENTRADA_OK'`. Invoice ENTRADA 717630 (ENTIN/2026/05/0055): posted LF R$ 12.525,54. PO 42419 (C2619591): purchase, team=143 RAFAEL, picking 321617 done.
- **177465 (AVULSO_FRASCO)**: `status='EXECUTADO', fase_pipeline='F5e_SEFAZ_OK'`. Invoice ENTRADA 719071 (ENTIN/2026/05/0056): posted LF R$ 7.796,58. PO 42543 (C2602695): purchase, LF, tipo=serv-industrializacao, fp=131, team=143 Rafael. Picking 321834 (LF/IN/01780): done, lote AJ-27-05. LF/Estoque/AJ-27-05: 37688un.

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)

- Skills L2 atômicas (8): 1, 2 (4 modos A/B/C/D v21+), 2.4, 4, 5 (7 átomos + G-AUDIT-3 v22+), **7 ABRANGENTE v25+ (10 átomos)**, **8 ATÔMICA v24+ (5 átomos)**, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, **`inventario_pipeline` v28+ S7** (pipeline A-F + recovery + opt-in v19+ S3 + opt-in v25+ S1 v27+ + helper ETAPA E via FLUXO L3 v28+ S7) — stub REMOVIDO.
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo` (V1 'inventario' v14b + G038 v22+ + G007+tipo_produto v24+).
- Fluxos L3 escritos (13): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+, 1.1.1 v27+ S5, 1.3 v27+ S5.

---

## §3. ESCOPO DESTA SESSÃO (v30+ — desbloquear canary via cadastro CFOP R3b + canary S2 + S6)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4). **PRIMEIRO verificar (READ) se o cadastro CFOP R3b já foi feito.**

### Objetivo macro

Desbloquear e executar o canary S2 (ETAPA E v28+ S7 + skill8 atômica v27+ S1) validando paridade vs legacy. **Pré-condição BLOQUEANTE: cadastro CFOP FB→5949 corrigido (R3b)**. Após canary OK, S6 cleanup (~2500 LOC) + flip defaults.

### Pré-requisito BLOQUEANTE — correção cadastral CFOP FB→5949 (R3b — FISCAL Rafael)
- **Quem**: Rafael / equipe fiscal (cadastro Odoo — FORA das skills-átomos; NÃO improvisar XML-RPC — PROTECAO SEMPRE-FAZER #11).
- **O quê**: criar Operação `l10n_br_ciel_it_account.operacao` na company **LF (5)**, `l10n_br_tipo_pedido='dev-industrializacao'`, saída, **`partner_ids=[1]` (FB)**, `l10n_br_intra_cfop_id`=5949 — espelhando a 2719 (LF→CD).
- **Como validar (READ — eu/subagente posso)**: após criada, confirmar numa NF DEV_LF_FB nova (dry-run) que a linha sai com `l10n_br_cfop_codigo='5949'` (engine casa a nova operação por partner FB, não a 2710 genérica).
- Detalhe técnico: `CLAUDE.md §14 D-V29-1`.

**Dependência crítica:** (1) cadastro R3b feito (fiscal) + (2) lote natural surgir. Canary destino-FB depende de AMBOS. Canary destino-LF (DEV_CD_LF) e S2.a (INDUSTRIALIZACAO_FB_LF) **não** dependem do R3b.

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S2 — Canary REAL PROD ETAPA E v28+ S7 (quando lote X→FB/X→LF surgir)

Quando próximo PERDA_LF_FB / TRANSFERIR_CD_FB / DEV_LF_FB / DEV_CD_LF natural surgir:

- Selecionar 1 ajuste natural em F5e_SEFAZ_OK (saída já transmitida SEFAZ; entrada pendente).
- Rodar pipeline com opt-in (PRIMEIRO dry-run + REVISÃO + real-run):
  ```bash
  # 1. DRY-RUN primeiro
  python -m app.odoo.estoque.orchestrators.inventario_pipeline \
    --modo resume --apenas-etapa E --usar-fluxo-l3-v19 \
    --ciclo <CICLO> --pular-pre-flight --limite 1
  # 2. REVISAR plano + confirmar com Rafael
  # 3. REAL-RUN
  python -m app.odoo.estoque.orchestrators.inventario_pipeline \
    --modo resume --apenas-etapa E --usar-fluxo-l3-v19 \
    --confirmar --ciclo <CICLO> --pular-pre-flight --limite 1
  ```
- Validar paridade vs legacy:
  - Invoice ENTRADA posted no destino correto
  - PO confirmada + picking done com lote correto
  - Saldo consolidado no destino
  - G039 FB destino: purchase.team Rafael+FB criado automaticamente

#### S2.a — Canary REAL PROD opt-in skill8 ATÔMICA v27+ S1 (quando INDUSTRIALIZACAO_FB_LF surgir)

```bash
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume --apenas-etapa C --usar-skill8-atomica-v25 \
  --confirmar --ciclo <CICLO> --pular-pre-flight --limite 1
# Se ETAPA C OK, rodar ETAPA D (SEFAZ irreversível):
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume --apenas-etapa D --usar-skill8-atomica-v25 \
  --confirmar --confirmar-sefaz --ciclo <CICLO>
```

Validar paridade vs legacy: chave SEFAZ válida + fase F5e_SEFAZ_OK + invoice posted + ajustes status=EXECUTADO.

#### S2.b — Canary REAL combinado (AMBAS flags juntas)

Se lote natural permitir, rodar pipeline INTEIRO (A→F) com AMBAS flags:

```bash
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --ciclo <CICLO> --usar-fluxo-l3-v19 --usar-skill8-atomica-v25 \
  --confirmar --confirmar-sefaz --pular-pre-flight --limite 1
```

Esta é a validação FINAL — paridade vs legacy em pipeline end-to-end inter-company.

#### S6 — Remover ETAPAS C+D+E+F legacy (NÍVEL 2 cleanup — após S2.a+S2+S2.b canary OK)

> Pré-requisito: canary REAL PROD validou paridade do caminho novo vs legacy em pelo menos 1 caso de cada direção (LF destino + FB destino + CD destino). S2/S2.a/S2.b OK.

**Etapas a remover do orchestrator** (todos com lógica inline atualmente):
- `executar_etapa_c` (~390 LOC) — renomear `_executar_etapa_c_via_skill8_atomica` → `executar_etapa_c` definitivo.
- `executar_etapa_d` (~580 LOC) — renomear `_executar_etapa_d_via_skill8_atomica` → `executar_etapa_d` definitivo.
- `executar_etapa_e` (~250 LOC) — remover ramo legacy Skill 7 V1 STRICT (`criar_recebimento_orchestrado`); renomear `_executar_etapa_e_via_fluxo_l3` → `executar_etapa_e` definitivo.
- `executar_etapa_f` (~600 LOC) — remover ramo legacy Skill 5 (`criar_picking_entrada_destino_manual` tampão AP2); renomear `_executar_etapa_f_via_fluxo_l3` → `executar_etapa_f` definitivo.

**Skills L2 DEPRECATED a remover** (NÍVEL 2 — após cleanup orchestrator):
- Skill 5 `criar_picking_entrada_destino_manual` em `picking.py:1215+` (DEPRECATED v19+ AP2 caminho B paliativo).
- Skill 7 wrapper `criar_recebimento_orchestrado` em `escrituracao.py:159+` (V1 STRICT DeprecationWarning v20+).

**Flags a flipar default** + remover em v30+:
- `usar_fluxo_l3_v19=True` por default em `executar_pipeline_bulk` + `executar_pipeline_resume`.
- `usar_skill8_atomica_v25=True` por default análogo.

**Tests a migrar** (~14 legacy):
- `tests/odoo/services/test_faturamento_pipeline_orchestrator.py` ETAPAs C+D legacy → `tests/odoo/services/test_faturamento_invoice_service.py` (Skill 8 ATÔMICA L2 direta).
- ETAPA E legacy test → `tests/odoo/services/test_escrituracao_lf_service.py` (Skill 7 V1 STRICT — futuro removido).

**Total estimado removido**: ~1500 LOC orchestrator + ~600 LOC Skill 5 atom DEPRECATED + ~400 LOC Skill 7 wrapper DEPRECATED = **~2500 LOC**.

**Pytest baseline esperado**: 688 → ~682 (testes legacy migrados sem perda de cobertura líquida).

### O que NÃO entra nesta sessão (escopo declarado fora)

- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER N11/N12).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (SUPERADO ao final v22+).
- ❌ S6 cleanup ETAPAs C+D+E sem canary natural — aguardar operador (não forçar saída sintética).
- ❌ Folha 1.5 (lançar frete CTe) ou 1.6 (despesa extra) — fora do escopo de inventário.

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (13 documentos incluindo funções-chave inventario_pipeline.py linhas exatas)
- [ ] Baseline pytest **688** confirmado
- [ ] **Verificar (READ) se cadastro CFOP R3b foi feito**: existe Operação LF dev-industrializacao 5949 com `partner_ids` contendo 1 (FB)? Se NÃO → canary destino-FB fica deferido (avisar Rafael)
- [ ] Cross-check Odoo: estado dos ajustes 176013/14 + 177465 (preservado v23+/v24+/v25+/v26+/v27+/v28+)
- [ ] Identificar candidatos canary: query `AjusteEstoqueInventario` em F5e_SEFAZ_OK com `acao_decidida in ACOES_ENTRADA_FB` OU `acao_decidida='INDUSTRIALIZACAO_FB_LF'` recém-criados (filtrar `created_at >= '2026-05-28 09:00'`)
- [ ] AskUserQuestion §1.4 confirmou escopo + ordem prioridade com Rafael

Implementação:
- [ ] **S2** — Canary REAL ETAPA E v28+ S7 (dry-run + revisão + real-run; validar G039 FB se aplicável)
- [ ] **S2.a** — Canary REAL skill8 ATÔMICA v27+ S1 (ETAPA C → ETAPA D SEFAZ)
- [ ] **S2.b** — Canary REAL combinado (pipeline A-F end-to-end com AMBAS flags)
- [ ] **S6** — Após canary OK: remover ETAPAs C+D+E legacy + migrar 14 testes + flip defaults

Validação:
- [ ] Pytest baseline ≥ 682 (688 - testes migrados + testes novos)
- [ ] ≥1 code-reviewer paralelo (S2 canary + S6 cleanup) via Task tool
- [ ] Atualizações cross-refs: CLAUDE.md §6 + ROADMAP HANDOFF + SKILL.md fachada

Documentação:
- [ ] Atualizar PROTECAO se houver novo antipadrão (esperado: nenhum se S2+S6 limpos)
- [ ] Atualizar CLAUDE.md §6 (catálogo se status mudou) + §14 (D-V29-X se novo desvio)
- [ ] Memórias `[[<slug>-pattern]]` salvas via `mcp__memory__save_memory`
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Rodar canary destino-FB ANTES do cadastro CFOP R3b → nova NF com 5902 (SEFAZ irreversível)** | MÉDIA | **ALTO** | **Verificar cadastro R3b ANTES** (PROTECAO SEMPRE-FAZER #11). Destino-FB só após confirmar Operação LF 5949 `partner_ids=[1]`. Destino-LF (DEV_CD_LF) + INDUSTRIALIZACAO_FB_LF livres. |
| Canary REAL ETAPA E S7 diverge do legacy Skill 7 V1 STRICT | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` em background para canary; compara output legacy (`criar_recebimento_orchestrado`) vs novo (helper E v28+ S7) via log JSON; rollback automático se RecebimentoLf criado divergente. |
| G039 dinâmico FB destino falha (primeira execução real) | MÉDIA | MÉDIO | Hook `garantir_purchase_team` lazy-cria team idempotente. Fallback silencioso para STATIC do constants caso falhe. Se persistir, Rafael decide STATIC FB caso-a-caso (espelha decisão F4 LF=143). |
| Canary REAL skill8 ATÔMICA v27+ S1 diverge do legacy | MÉDIA | ALTO | Mesma mitigação S2 — subagente background + log JSON diff + rollback. |
| Lote natural não surge nesta sessão | ALTA | MÉDIO | S2/S2.a/S2.b ficam para sessão N+1 (deferido); S6 NÃO executa sem canary (risco alto remover ~1500 LOC sem validar). |
| S6 remoção ETAPAs legacy quebra testes não-migrados | MÉDIA | MÉDIO | Antes de remover: mapear todos os testes que referenciam `executar_etapa_c/d/e` legacy; migrar mentalmente; rodar pytest após cada migração; rollback se >5% testes quebrarem. |
| Discovery XML-RPC FB/CD canary retorna IDs diferentes de v27+ S4 | BAIXA | MÉDIO | CONSTANTS são CANDIDATE — primeira canary REAL ajusta caso a caso; Rafael confirma valores corretos antes do flip default. |
| Sessão estoura tokens com S2+S6 | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` para S2 canary (lição v7 ~150k tokens); principal só S6 (puro código). |

---

## §6. AO TERMINAR ESTA SESSÃO (atemporal — copiar literal nas próximas)

> **OBRIGATÓRIO** antes do commit final:

### 6.1 Documentação
1. Append bloco "Sessão YYYY-MM-DD vXX" em `VALIDACAO_FINAL_SESSAO.md` (NÃO no ROADMAP HANDOFF — regra D-V18-5).
2. Atualizar `ROADMAP_SKILLS.md` HANDOFF (≤80 linhas) — estado global + próximo passo refinado.
3. Atualizar `CLAUDE.md` estoque (catálogo §6 se skill mudou status; §6.5 se antipadrão resolvido; §14 se novo desvio detectado).
4. Se detectou NOVO antipadrão reincidente → atualizar `PROTECAO_PROXIMA_SESSAO.md` (ARN + Nij + Lições).
5. Se padrão emergiu → salvar memória `[[<slug>-pattern]]` via `mcp__memory__save_memory`.

### 6.2 Sanitizar prompts (regra desta convenção — D-V18-PROMPTS)
1. Renomear este `PROMPT_PROXIMA_SESSAO.md` para `_prompts_executados/PROMPT_PROXIMA_SESSAO_v<XX>_EXECUTED_<YYYY_MM_DD>.md`.
2. Criar **novo** `PROMPT_PROXIMA_SESSAO.md` no root de `app/odoo/estoque/` com escopo da sessão N+1:
   - §0 + §1 + §6 — copiar literal deste arquivo (atemporais).
   - §2 — atualizar com commit novo + estado pós-sessão.
   - §3 — definir escopo da próxima sessão (sub-objetivos).
   - §4 — checklist concreto.
   - §5 — riscos + mitigações específicos.

### 6.3 Commit consolidado
```bash
git add <arquivos modificados>
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
export PATH="/home/rafaelnascimento/projetos/frete_sistema/.venv/bin:$PATH"
git commit -m "<tipo>(estoque): <sumário> — v<XX> (YYYY-MM-DD)
<corpo do commit detalhado>
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### 6.4 Validação final
- [ ] Pytest verde ≥ baseline atual
- [ ] `git status` limpo
- [ ] `PROMPT_PROXIMA_SESSAO.md` novo criado (1 só vivo no root)
- [ ] Histórico em `VALIDACAO_FINAL_SESSAO.md`
- [ ] `PROTECAO_PROXIMA_SESSAO.md` atualizado se houve novo antipadrão

---

> **TEMPLATE END**. Para próxima sessão (após executar esta), substituir §2-§5 mantendo §0, §1, §6 literais.
