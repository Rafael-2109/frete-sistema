# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v20+ canary REAL PROD do FLUXO L3 1.2.x + ativar opt-in no orchestrator + refator nomenclatura AP6 (Skill 8 ATÔMICA L2 vs `inventario_pipeline` C3).
**Base**: commit pendente v19+ (Skill 7 ABRANGENTE + Fluxos L3 1.2.1/1.2.2 + dispatch executar_fluxo_l3_1_2_x). 554 pytest verdes.
**Risco**: ALTO (canary REAL toca PROD; SEFAZ via fluxo L3 não foi validado real ainda).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-26 v19+ (sucessor do v19 EXECUTED).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N17 + AR1-AR8 + lições memories).
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo) + §6.5 (antipadrões CAUSA/CONSEQUÊNCIA/COMO EVITAR — AP1+AP3+AP4+AP5 ✅, AP2 reclassificado, AP6 NOVO v20+) + §14 (histórico desvios D-V19-1+D-V19-2) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer.
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
7. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
8. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 555 passed (v19+ baseline)
```

Se ≠ 555 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v19+)

### Estado do código
- **Commit base**: v19+ pendente commit (Skill 7 ABRANGENTE + Fluxos L3 1.2.1/1.2.2 + dispatch).
- **Baseline pytest**: 555 verdes em ~16s.
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura
- **Skill 7 ABRANGENTE LIVE v19+**: 7 átomos (`buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida`, `escriturar_dfe`, `gerar_po_from_dfe`, `preencher_po`, `confirmar_po`, `criar_invoice_from_po`). V1 STRICT wrapper deprecado v20+.
- **Skill 5 átomo NOVO `preencher_lotes_picking`** LIVE v19+; `criar_picking_entrada_destino_manual` DEPRECATED docblock.
- **Fluxos L3 1.2.1 + 1.2.2 escritos** (caminho A — DFe via SEFAZ + caminho B — DFe via XML da SAÍDA).
- **Método `FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x`** no orchestrator: dispatch caminho A vs B, compõe 7 átomos Skill 7 + Skill 5 `preencher_lotes_picking` + Skill 5 `validar`. ETAPAS E+F legacy preservadas (não quebrar baseline).
- **AP1+AP3+AP4+AP5 ✅ resolvidos**. AP2 reclassificado com causa real. **AP6 NOVO**: nomenclatura "Skill 8 = orchestrator C3" vs definição atômica L2 — refator v20+.

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (7): 1, 2, 2.4, 4, 5 (com 7 átomos), 7 ABRANGENTE v19+, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, `faturamento_pipeline` (pipeline A-F + recovery + dispatch fluxo L3 1.2.x v19+).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo`.
- Fluxos L3 escritos (11): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, **1.2.1 v19+**, **1.2.2 v19+**.
- Fluxos L3 pendentes: 1.1.x, 1.3, 2.3.

### Pendências (Skill 8 — pós-v19+)
- C14-C18 ✅ v18+v19+ (recovery + SKILL.md + pytest + smokes + folhas L3 1.2.x + dispatch).
- **C19 cross-refs final** ⬜ — agente web tools/skills sync, ROUTING_SKILLS, AGENT_BOILERPLATE, gestor-estoque-odoo árvore (mencionar fluxos 1.2.1+1.2.2 explicitamente).
- **C20 canary REAL PROD FLUXO L3 1.2.x** ⬜ — escolher 1 caso `INDUSTRIALIZACAO_FB_LF` ou `PERDA_LF_FB` real para validar end-to-end.
- C21 bulk REAL PROD ⬜
- C22 code-review final v19+ ⬜
- C23 commit + arquivar `criar_picking_entrada_destino_manual` + ETAPAS E/F legacy ⬜

---

## §3. ESCOPO DESTA SESSÃO (v20+ — canary REAL PROD + ativação opt-in + refator nomenclatura AP6)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Validar em PROD que `executar_fluxo_l3_1_2_x` produz o resultado correto (DFe criado/escriturado → PO confirmada → picking preenchido com lotes → invoice draft → posted) em 1 caso real, depois ativar como opt-in no `executar_pipeline_bulk` substituindo as ETAPAS E+F legacy. Em paralelo, iniciar refator nomenclatura AP6.

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S1 — C19 cross-refs final
- `.claude/agents/gestor-estoque-odoo.md`: adicionar nodos 1.2.1 e 1.2.2 explicitamente na árvore (já tem 1.2 genérico).
- `.claude/references/ROUTING_SKILLS.md`: refletir Skill 7 ABRANGENTE 7 átomos (era 1 método V1 STRICT).
- SKILL.md `faturando-odoo` fachada: adicionar receita "FLUXO L3 1.2.x via `executar_fluxo_l3_1_2_x`".

#### S2 — Canary REAL PROD do FLUXO L3 1.2.x (spawn subagente `gestor-estoque-odoo`)

Escolher o caso conforme o caminho que queremos validar:
- **Validar caminho A (fluxo 1.2.1 — DFe veio via SEFAZ)**: escolher `PERDA_LF_FB` ou `TRANSFERIR_CD_FB` ou `DEV_LF_FB` no ciclo `INVENTARIO_2026_05` em fase `F5e_SEFAZ_OK` mas ainda NÃO processado pela ETAPA E legacy. Verificar via `buscar_dfe(chave, company_destino)` que DFe está disponível com `status='pendente'` ANTES.
- **Validar caminho B (fluxo 1.2.2 — DFe upload XML SAÍDA)**: escolher `INDUSTRIALIZACAO_FB_LF` (caso PROD real onde DFe nunca vem via SEFAZ no sentido reverso). Verificar via `buscar_dfe` que retorna `encontrado=False` ANTES.

Passos:
- Spawn subagente Task `gestor-estoque-odoo` para executar `executar_fluxo_l3_1_2_x(invoice_id_saida=X, company_destino=Y, ..., dry_run=True)` primeiro → revisar plano (passos 1-9 + caminho A/B detectado) → confirmar com Rafael → `dry_run=False`.
- Verificar pós-execução direto no Odoo: DFe criado/escriturado, PO confirmada (state=`purchase`), picking done, invoice draft criada + posted.
- Logar resultado em `/tmp/log_canary_fluxo_l3_v20_<ts>.json`.

#### S3 — Ativar opt-in `--usar-fluxo-l3-v19` no `executar_pipeline_bulk`
- Adicionar flag CLI no `argparse` do orchestrator.
- Quando flag=True, etapas E+F do `executar_pipeline_bulk` invocam `executar_fluxo_l3_1_2_x` em vez das legacy.
- Quando flag=False (default), comportamento legacy preservado (zero risco de regressão default).
- 2-3 pytest mockados validando dispatch correto.

#### S4 — Refator nomenclatura AP6 (Skill 8 ATÔMICA L2 vs `inventario_pipeline` C3)
- Extrair as 5 operações C+D do orchestrator atual para método `executar_skill8_atomica(picking_ids, constants_por_acao, dry_run)` no próprio orchestrator (ainda como método; v21+ extrai para serviço L2 dedicado).
- Atualizar §6 do CLAUDE.md estoque: Tabela 1 ganha entrada `faturando-odoo` (Skill 8 ATÔMICA L2 — método novo). Tabela 2 renomeia orchestrator para `inventario_pipeline` (alias `faturando-odoo` C3 deprecado nome confuso).
- Atualizar SKILL.md `faturando-odoo` fachada: clarificar que é fachada para método ATÔMICA + opcionalmente para invocar o orchestrator C3 completo.

#### S5 — Após canary OK: deprecar wrapper V1 STRICT `criar_recebimento_orchestrado`
- Adicionar DeprecationWarning runtime na função.
- Marcar fim de vida em v21+ ou v22+ (após mais 1 ciclo de validação).
- Manter pytest V1 STRICT para regressão.

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Remover `criar_picking_entrada_destino_manual` (só após bulk REAL PROD do fluxo L3 — v21+).
- ❌ Folhas L3 pendentes 1.1.x, 1.3, 2.3 (precisam de Skill 8 ATÔMICA L2 totalmente extraída para SAÍDA — v21+).
- ❌ Refatorar `RecebimentoLfOdooService` (NÃO MEXER) ou `LancamentoOdooService` (NÃO MEXER) (regras v14a-fix + v19+).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (8 documentos)
- [ ] Baseline pytest 554 confirmado
- [ ] AskUserQuestion §1.4 confirmou escopo S1-S5 com Rafael

Implementação:
- [ ] S1 — cross-refs atualizados (gestor-estoque-odoo árvore + ROUTING_SKILLS + SKILL.md faturando-odoo)
- [ ] S2 — canary REAL PROD: subagente executou 1 caso real do FLUXO L3 1.2.x + verificação direta no Odoo OK
- [ ] S3 — flag `--usar-fluxo-l3-v19` adicionada + 2-3 pytest mockados verdes
- [ ] S4 — método `executar_skill8_atomica` extraído + Tabela 1/2 §6 atualizadas
- [ ] S5 — DeprecationWarning adicionado em `criar_recebimento_orchestrado`

Validação:
- [ ] Pytest baseline ≥ N atual confirmado em §1.3 + novos testes de S2/S3/S4 (estimativa 4-10 novos)
- [ ] Canary REAL: 1 caso end-to-end OK (escolha do caso: ver §3.S2)
- [ ] ≥1 code-reviewer paralelo (constituição §6 conformance + edge cases canary)
- [ ] Atualizações cross-refs: SKILL.md `escriturando-odoo` + SKILL.md `faturando-odoo` + ROADMAP HANDOFF + PLANEJAMENTO §0

Documentação:
- [ ] Atualizar antipadrões §6.5 CLAUDE.md (AP2 ✅ se canary validar — pode ser parcial até bulk PROD v21+)
- [ ] Atualizar §6 catálogo (Tabela 1 ganha Skill 8 ATÔMICA L2; Tabela 2 renomeada para `inventario_pipeline`)
- [ ] Atualizar PROTECAO_PROXIMA_SESSAO.md se detectou novo antipadrão (§6 abaixo)
- [ ] Memória NOVA `[[canary-fluxo-l3-pattern]]` se padrão emergir do canary
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Canary REAL falha em PROD (FLUXO L3 1.2.x quebra mid-step) | MÉDIA | MUITO ALTO (SEFAZ irreversível) | Subagente roda `dry_run=True` PRIMEIRO + revisar plano com Rafael ANTES de `dry_run=False`. Se falha mid-step, idempotência por campos Odoo permite recovery (cada átomo é idempotente). |
| Constants por company (team_id, payment_provider, picking_type) erradas para alguma direção | MÉDIA | MÉDIO | Antes do canary, validar via XML-RPC read: `team.id` válido para `company_destino`, `payment_provider.id` existe, `picking_type.id` é de ENTRADA da company correta. |
| ETAPAS E+F legacy quebradas pela flag `--usar-fluxo-l3-v19` (regressão) | MÉDIA | ALTO | Flag default=False preserva 100% comportamento legacy. Pytest novos validam dispatch flag=True. |
| Refator nomenclatura AP6 inflaciona escopo da sessão | MÉDIA | MÉDIO | S4 é último na ordem. Se sessão estourar, adia S4 para v21+ (fica documentado como pendência). |
| Sessão estoura tokens | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` via Task tool para executar canary REAL; principal só implementa S1+S3+S4+S5 + verifica. (Lição v7 ~150k tokens.) |
| Premissa errada sobre algum detalhe Odoo CIEL IT do fluxo L3 (caso G037 v18) | MÉDIA | ALTO | Antes de codar, RELER `operacoes_fiscais.py` INTEIRO + `escrituracao.py` INTEIRO (após v19+ atomos LIVE). Validar com Rafael antes de canary. |

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
