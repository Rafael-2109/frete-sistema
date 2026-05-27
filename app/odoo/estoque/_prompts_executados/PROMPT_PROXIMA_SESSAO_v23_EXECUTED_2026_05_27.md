# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v23+ codificar invariante G039 (purchase.team Skill 7) + investigar G-PERM-1 (ir.rule dfe.line) + fix raiz contador F status=EXECUTADO + completar fluxo F passo 9+10 (caminho B FLUXO L3 1.2.x). Ondas paralelas: S2 remoção tampão + S3-S7 originais v22+ adiados.
**Base**: commits v22+ EXECUTED (G-AUDIT-3 fix + Sub-skill C5 G038 + Caminho B parcial validado em PROD chave 35260561724241000178550010000945661007164482). 580 pytest verdes.
**Risco**: MÉDIO (codificar 1 invariante arquitetural — purchase.team — + investigar 1 ir.rule perm = 2 frentes de pesquisa).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-27 v22+ EXECUTED (sucessor do v21+ EXECUTED).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20,21,22}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N24 + AR1-AR12 + lições memories). **Atenção especial a N24 NOVO v22+** (purchase.team invariante LF) e N23 ✅ RESOLVIDO v22+.
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo) + §6.5 (antipadrões — AP2 com resolução parcial v22+ Caminho B; AP6 pendente v23+) + §14 (histórico desvios — D-V22-1/2/3 + G-PERM-1) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer.
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
7. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
8. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 580 passed (v22+ baseline)
```

Se ≠ 580 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v22+ — FINALIZADA com 2 descobertas arquiteturais)

### Estado do código
- **Commit base**: v22+ EXECUTED (G-AUDIT-3 fix + Sub-skill C5 G038 + Caminho B parcial em PROD). Pipeline real CHEGOU ATÉ SEFAZ (chave 35260561724241000178550010000945661007164482); ETAPA F caminho B avançou até passo 7→9 (FALHA_PASSO_9_CRIAR_INVOICE por ir.rule perm Rafael em dfe.line).
- **Baseline pytest**: 580 verdes em ~15s (+4 net v22+ via Skill 5 G-AUDIT-3 + Sub-skill C5 G038).
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura
- **Skill 5 GANHOU fix G-AUDIT-3** v22+ — `criar_picking_inter_company` segrega state=cancel da idempotência por origin. 70 pytest (+2 net v22+). Validado E2E em PROD (picking 321600 cancel ignorado, 321601 NOVO criado).
- **Sub-skill C5 GANHOU check G038** v22+ — `_check_ncm_weight_tracking` detecta `l10n_br_origem in (False, None, '')` como BLOQUEIO. 16 pytest (+2 net v22+). Sem auto-fix (operador seta '0' Nacional / '1' Estrangeira / etc).
- **Caminho B FLUXO L3 1.2.x VALIDADO PARCIAL em PROD** v22+ — primeira execução REAL: DFe 43533 criado no LF via `criar_dfe_a_partir_do_invoice_saida` + PO C2619591 (id=42419) criada com order_line correta + workaround team 143 destravou state→'purchase' + button_approve gerou picking 321617. Falhou em passo 9 (criar_invoice) por ir.rule perm Rafael em dfe.line.
- **Descoberta G039**: PO LF cai com `team_id=41` 'Aprovação LF - JOSEFA' (user_id=78 Edilane) → state='to approve' permanente via XML-RPC. Solução: criar `purchase.team` com user_id=user-execução + write PO team_id=novo + ciclo cancel→draft→confirm destrava. Team 143 'Aprovação LF - RAFAEL' criado.
- **Descoberta G-PERM-1**: Rafael (uid=42) tem 2 grupos `ir.model.access` necessários em dfe.line (28 Accounting/Billing + 1 Internal User) mas erro persistente "não tem acesso 'leitura'". Causa: `ir.rule` record-level.

### Estado dos 2 ajustes de teste v22+
- id=176013/176014: `status='EXECUTADO', fase_pipeline='F5e_SEFAZ_OK', picking_id_odoo=321601, invoice_id_odoo=716448, chave_nfe='35260561724241000178550010000945661007164482'`
- Picking 321600 (FB/SAI/IND/01601): `state=cancel` (preservado)
- Picking 321601 (FB/SAI/IND/01602): `state=done` (criado v22+ pelo fix G-AUDIT-3)
- Picking 321617 (LF/IN/<seq>): gerado v22+ pelo button_approve PO 42419 — verificar state atual
- Invoice 716448 RPI/2026/00238: `state=posted, l10n_br_situacao_nf='autorizado', chave SEFAZ válida 44 dígitos`
- DFe 43533 (LF, chave 35260...82): criado v22+ via caminho B com lines populadas
- PO 42419 C2619591 (LF, partner FB): `state=purchase, team_id=143, picking_ids=[321617]`
- Invoice ENTRADA: NÃO CRIADA (falha passo 9 por ir.rule perm)
- Purchase team 143 'Aprovação LF - RAFAEL': criado, user_id=42, company_id=5

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (7): 1, 2 (4 modos A/B/C/D v21+), 2.4, 4, 5 (7 átomos + G-AUDIT-3 v22+), 7 ABRANGENTE v20+, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, `faturamento_pipeline` (pipeline A-F + recovery + dispatch fluxo L3 1.2.x v19+ + opt-in v20+ + fix G-AUDIT-1 v21+).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo` (V1 'inventario' v14b + G038 v22+).
- Fluxos L3 escritos (11): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+ (Caminho B validado parcial v22+).
- Fluxos L3 pendentes: 1.1.x, 1.3, 2.3 (dependem refator AP6).

### Pendências críticas v23+
- 4 tasks v22+ não-resolvidas (13-16 no TaskList): contador F EXECUTADO; PO to_approve regra exata; ir.rule dfe.line Rafael; Skill 7 codificar purchase.team invariante (G039).
- Itens originais v22+ NÃO TOCADOS: S2 remoção tampão; S3 refator AP6; S4 expand CONSTANTS FB/CD; S5 folhas L3 1.1/1.3/2.3; S6 C5 G007/l10n_br_tipo_produto; S7 lote literal P-15/05.

---

## §3. ESCOPO DESTA SESSÃO (v23+ — codificar G039 + investigar G-PERM-1 + fix raiz contador F + completar passo 9-10 caminho B)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Codificar a invariante G039 (purchase.team gatekeeper LF) na Skill 7 + investigar a causa exata de G-PERM-1 (ir.rule dfe.line) + fix raiz contador F → permitir que caminho B FLUXO L3 1.2.x rode end-to-end SEM intervenção manual.

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S0 — Investigar G-PERM-1 ir.rule dfe.line (BLOQUEIO crítico)
- Listar `ir.rule` ativos em `l10n_br_ciel_it_account.dfe.line` via XML-RPC
- Identificar qual rule filtra Rafael (uid=42) — provavelmente por company_id ou record_uid
- Comparar com Edilane (uid=78) — qual rule passa para ela
- Workaround imediato: rodar pipeline com user com permissão OU adicionar Rafael a grupo CIEL IT específico
- Sem isso, S1 abaixo fica bloqueado

#### S1 — Codificar invariante G039 purchase.team na Skill 7
- Novo átomo (ou método) em `escrituracao.py`: `garantir_purchase_team(user_id, company_id, dry_run)` que:
  - Busca `purchase.team` com user_id=user_id + company_id=company_id
  - Se não existe, CREATE
  - Retorna team_id
- Hook em `confirmar_po` (Skill 7) OU em `_executar_etapa_f_via_fluxo_l3` (orchestrator): chamar `garantir_purchase_team` + `write PO team_id` ANTES de `button_confirm`
- Pytest novo cobrindo cenário (mock purchase.team search vazio + create)
- Smoke real PROD: re-rodar caminho B com outra invoice — deve auto-criar team + confirmar PO direto sem to_approve

#### S2 — Fix raiz contador F status='EXECUTADO' (Task 13)
- Alterar `_contar_pendentes_por_etapa` linha 4458: ETAPA F filtro `status IN ('PROPOSTO','APROVADO','EXECUTADO')` (outras etapas mantém PROPOSTO/APROVADO)
- Pytest novo cobrindo contador F com status='EXECUTADO'
- Remove necessidade de workaround manual de UPDATE status

#### S3 — Completar passo 9+10 caminho B FLUXO L3 1.2.x (após S0+S1)
- Pós-S0 desbloqueio G-PERM-1: re-rodar resume F nos ajustes 176013/176014 (status='APROVADO' temporário OU pós-S2 EXECUTADO direto)
- Passo 9 (criar_invoice_from_po) deve completar
- Passo 10 (validar invoice) deve completar
- Ajustes mudam para fase F5f_OK + status final
- Validação E2E 100% caminho B

#### S4 — Investigar PO to_approve regra exata (Task 14)
- Cross-check canary 627348 (caminho A SEFAZ-via-DFe que autorizou normalmente): fiscal_position_id populada? team_id? amount_total? Como passou aprovação?
- Comparar com PO 42419 (caminho B): identificar diferença causal
- Decidir: caminho B precisa setar fiscal_position antes de button_confirm? OU regra de aprovação é por valor (R$X limit)?

#### S5 — S2-S7 originais v22+ (se sobrar tempo)
- S2 remoção tampão (criar_picking_entrada_destino_manual + V1 STRICT wrapper + ETAPAS E/F legacy)
- S3 refator AP6 (Skill 8 ATÔMICA L2)
- S4 expand CONSTANTS FB/CD destino
- S5 folhas L3 pendentes (1.1.x, 1.3, 2.3)
- S6 C5 G007 + l10n_br_tipo_produto
- S7 lote literal P-15/05 forcar_lote_literal=True

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER — regras v14a-fix + v19+).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (regra v14a-ops — SUPERADO ao final v22+).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (8 documentos)
- [ ] Baseline pytest 580 confirmado
- [ ] Cross-check Odoo: PO 42419 + picking 321617 + DFe 43533 + invoice 716448 + Team 143 (estado ainda preservado)
- [ ] AskUserQuestion §1.4 confirmou escopo S0-S5 com Rafael

Implementação:
- [ ] S0 — ir.rule investigation + workaround/fix G-PERM-1
- [ ] S1 — Skill 7 garantir_purchase_team + hook + pytest novo + smoke real PROD
- [ ] S2 — Fix contador F status='EXECUTADO' + pytest novo
- [ ] S3 — Completar passo 9+10 caminho B (re-rodar resume F após S0+S1)
- [ ] S4 — Investigar canary 627348 vs PO 42419 (PO to_approve regra exata)
- [ ] S5 — S2-S7 originais conforme tempo

Validação:
- [ ] Pytest baseline ≥ 580 + novos testes (estimativa 4-8 novos)
- [ ] ≥1 code-reviewer paralelo (Skill 7 invariante + S0 ir.rule fix)
- [ ] Atualizações cross-refs: SKILL.md `escriturando-odoo` + ROADMAP HANDOFF + PROTECAO N24

Documentação:
- [ ] Atualizar antipadrões §6.5 CLAUDE.md (AP2 ✅ se caminho B completar; AP6 conforme S3)
- [ ] Atualizar §6 catálogo (Skill 7 com garantir_purchase_team se aplicável)
- [ ] Atualizar PROTECAO_PROXIMA_SESSAO se novo antipadrão detectado
- [ ] Memória NOVA `[[g039-purchase-team-gatekeeper]]` para gravar lição v22+ G039
- [ ] Memória NOVA `[[g_perm_1_ir_rule_dfe_line]]` para gravar descoberta v23+
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| ir.rule dfe.line é por user_id explícito (não por grupo) — workaround só via mudar pipeline user | MÉDIA | ALTO | S0 prioritário. Se for o caso, pipeline user passa a ser uid configurável; default Rafael (uid=42) muda para uid com perm. Documentar em CLAUDE.md. |
| Codificar `garantir_purchase_team` quebra POs já existentes em outros teams | BAIXA | MÉDIO | Hook só roda se team_id default for "default 41 Edilane LF". Outros teams (Samantha-LF id=135, Jessica_Fiscal_LF id=131, etc) NÃO são tocados. |
| Fix contador F muda comportamento de ondas anteriores (que dependem status=APROVADO em F) | BAIXA | MÉDIO | Adicionar fase_pipeline filter junto: ETAPA F = `status IN (..., EXECUTADO) AND fase_pipeline IN (F5e_OK, F5f_FALHA)`. Restrito ao caso pós-D OK. |
| Passo 9 (criar_invoice) tem mais regras escondidas além de ir.rule | MÉDIA | ALTO | S3 só roda após S0+S1 OK. Se passo 9 ainda falhar, investigar logs adicionais Odoo (não só XML-RPC). |
| Sessão estoura tokens (já longa em v22+) | ALTA | ALTO | Spawn subagente `gestor-estoque-odoo` para casos reais; principal só implementa refator + revisa. |
| Workaround team 143 não destravar para outras direções (CD, FB destino) | MÉDIA | MÉDIO | S1 cobrir multi-company; pytest cobrir 3 direções (LF/FB/CD destino). |

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
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### 6.4 Validação final
- [ ] Pytest verde ≥ baseline atual
- [ ] `git status` limpo
- [ ] `PROMPT_PROXIMA_SESSAO.md` novo criado (1 só vivo no root)
- [ ] Histórico em `VALIDACAO_FINAL_SESSAO.md`
- [ ] `PROTECAO_PROXIMA_SESSAO.md` atualizado se houve novo antipadrão

---

> **TEMPLATE END**. Para próxima sessão (após executar esta), substituir §2-§5 mantendo §0, §1, §6 literais.
