# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v21+ bulk REAL PROD do FLUXO L3 1.2.x via opt-in + remoção tampão arquitetural (`criar_picking_entrada_destino_manual` + wrapper V1 STRICT + ETAPAS E/F legacy) + expansão constants FB/CD destino + refator nomenclatura AP6 (Skill 8 ATÔMICA L2).
**Base**: commit v20+ (canary REAL OK + FIX A/B/whitelist + opt-in `--usar-fluxo-l3-v19` + DeprecationWarning V1 STRICT). 563 pytest verdes.
**Risco**: MÉDIO (bulk PROD = N invoices, mas opt-in default OFF preserva legacy; refator AP6 isolado).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-26 v20+ EXECUTED (sucessor do v19+ EXECUTED).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N20 + AR1-AR10 + lições memories). **Atenção especial a N18+N19+N20 NOVOS v20+** (whitelist orchestrator, subagente stateful, idempotência via 3 caminhos).
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo) + §6.5 (antipadrões — AP2 com resolução parcial v20+; AP6 pendente v21+) + §14 (histórico desvios) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer.
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
7. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
8. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 563 passed (v20+ baseline)
```

Se ≠ 563 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v20+)

### Estado do código
- **Commit base**: v20+ pendente commit (canary REAL OK + FIX A/B/whitelist + opt-in + DeprecationWarning).
- **Baseline pytest**: 563 verdes em ~18s.
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura
- **Skill 7 ABRANGENTE LIVE v20+**: 7 átomos + FIX A `escriturar_dfe` (idempotência 2 caminhos: `campos_ja_iguais` + `data_preservada_tipo_igual`) + FIX B `gerar_po_from_dfe` (idempotência 3 caminhos vínculo DFe↔PO: `dfe_purchase_id_direto` 14.6% + `dfe_purchase_fiscal_id` 75% + `po_dfe_id_reverso` 85.4%). 38 pytest. Wrapper V1 STRICT `criar_recebimento_orchestrado` emite DeprecationWarning runtime.
- **Skill 5 átomo `preencher_lotes_picking`** LIVE v19+; `criar_picking_entrada_destino_manual` DEPRECATED docblock (museum vivo até v21+ pós-bulk PROD).
- **Fluxos L3 1.2.1 + 1.2.2 escritos** (caminho A — DFe via SEFAZ + caminho B — DFe via XML da SAÍDA). Doc 1.2.2 linha 24 atualizada com R3 (DFe SEFAZ ATIVO em PROD 2026-05).
- **Método `executar_fluxo_l3_1_2_x`** no orchestrator + dispatch caminho A vs B. Whitelist linha 2939 aceita `IDEMPOTENT_ESCRITURADO` (fix v20+).
- **Opt-in `--usar-fluxo-l3-v19` LIVE v20+** no `executar_pipeline_bulk` + `executar_pipeline_resume`. Default OFF preserva 100% legacy. `CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO` (só LF=5 validado canary; FB=1 e CD=4 pendentes v21+). ETAPA E com flag → SKIP_NAO_SUPORTADA_V20; ETAPA F destino LF usa fluxo L3 via `_executar_etapa_f_via_fluxo_l3`.
- **Canary REAL PROD v20+**: 1 caso INDUSTRIALIZACAO_FB_LF (invoice 627348, DFe 42868) processado com `FLUXO_OK` em 1190ms. ZERO duplicações no Odoo. FIX B caminho 2 detectou IDEMPOTENT como previsto.
- **AP1+AP3+AP4+AP5 ✅ resolvidos**. AP2 ⚠️ canary validado v20+; remoção tampão pendente v21+ pós-bulk. AP6 ⏳ pendente v21+ (refator nomenclatura).

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (7): 1, 2, 2.4, 4, 5 (com 7 átomos), 7 ABRANGENTE v20+, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, `faturamento_pipeline` (pipeline A-F + recovery + dispatch fluxo L3 1.2.x v19+ + opt-in v20+).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo`.
- Fluxos L3 escritos (11): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+.
- Fluxos L3 pendentes: 1.1.x, 1.3, 2.3 (dependem refator AP6).

### Pendências (Skill 8 — pós-v20)
- C18 ✅ v19+ (folhas L3 1.2.x + dispatch).
- C19 ✅ v20+ (cross-refs final).
- C20 ✅ v20+ (canary REAL PROD 1 invoice OK).
- **C21 bulk REAL PROD** ⬜ — onda completa (não só 1 invoice). Casos disponíveis no INVENTARIO_2026_05 (4 INDUSTRIALIZACAO_FB_LF F5c_LIBERADO).
- **C22 code-review final v20+** ⬜.
- **C23 commit + arquivar tampão** ⬜ — após bulk OK: remover `criar_picking_entrada_destino_manual` + wrapper V1 STRICT + ETAPAS E/F legacy + arquivar `09_executar_onda1_bulk.py`.

---

## §3. ESCOPO DESTA SESSÃO (v21+ — bulk REAL PROD + remoção tampão + expansão constants + refator AP6)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Validar em PROD que `executar_fluxo_l3_1_2_x` via opt-in `--usar-fluxo-l3-v19` processa ONDA COMPLETA (3-4 invoices ou mais) sem duplicação fiscal. Após validação, remover tampão arquitetural (Skill 5 v15a `criar_picking_entrada_destino_manual` + wrapper V1 STRICT `criar_recebimento_orchestrado` + ETAPAS E/F legacy). Expandir constants para FB e CD destino (galho 1 do orchestrator). Executar refator nomenclatura AP6 (extrair Skill 8 ATÔMICA L2 do orchestrator).

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S1 — Bulk REAL PROD via opt-in (spawn subagente `gestor-estoque-odoo`)
- Spawn subagente Task para executar `python -m app.odoo.estoque.orchestrators.faturamento_pipeline --modo bulk --etapas E,F --usar-fluxo-l3-v19 --ciclo INVENTARIO_2026_05 --confirmar` (ou direto via Python script).
- Esperado: 3-4 INDUSTRIALIZACAO_FB_LF processados via `_executar_etapa_f_via_fluxo_l3` em ~5s totais (todos idempotentes); ETAPA E retorna SKIP_NAO_SUPORTADA_V20.
- Verificar pós-execução direto no Odoo: nenhuma PO/picking/invoice duplicada (count `('dfe_id','=',X)` ainda 1 por DFe); DFes inalterados.
- Logar `/tmp/log_bulk_fluxo_l3_v21_<ts>.json`.

#### S2 — Remoção tampão arquitetural (após bulk OK)
- Remover `criar_picking_entrada_destino_manual` (Skill 5 v15a) — escrita `app/odoo/estoque/scripts/picking.py` + ajustar pytest `test_stock_picking_service.py`.
- Remover wrapper V1 STRICT `criar_recebimento_orchestrado` (Skill 7) — `app/odoo/estoque/scripts/escrituracao.py` + ajustar 11 pytest de `test_escrituracao_lf_service.py`.
- Remover ETAPAS E/F legacy do orchestrator — `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (executar_etapa_e + executar_etapa_f); manter apenas `_executar_etapa_f_via_fluxo_l3` (renomear para `executar_etapa_f`).
- Atualizar constants `inventario_pipeline` removendo `ACOES_ENTRADA_DESTINO_MANUAL_CANARY` + `LOCATION_ORIGEM_POR_DIRECAO` (se não mais usados).
- Atualizar §6 catálogo CLAUDE.md (Tabela 1 Skills L2 — remover docblock DEPRECATED Skill 5; Tabela 3 Orchestrators C3 — atualizar).
- Pytest baseline esperado: 563 (mantém ou aumenta — remove testes V1 STRICT + adiciona regression do path novo).

#### S3 — Expandir CONSTANTS_FLUXO_L3 para FB e CD destino
- Para cada direção pendente (TRANSFERIR_FB_CD, DEV_FB_LF, DEV_FB_CD, DEV_CD_FB, PERDA_LF_FB, etc.):
  - Descobrir team_id por company (via XML-RPC `purchase.team` filtro company_id)
  - Descobrir payment_term_id (provavelmente sempre 2791 'A VISTA')
  - Descobrir picking_type_id por company destino (FB=1, CD=13/50, LF=19)
- Atualizar `CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO` mapa.
- Atualizar `L10N_BR_TIPO_PEDIDO_POR_ACAO` mapa via lookup `MATRIZ_INTERCOMPANY[acao]['entrada'][(co, cd)]['l10n_br_tipo_pedido_entrada']`.
- Canary REAL PROD para cada direção nova (1 invoice por direção).
- Pytest mockados validando dispatch correto para FB/CD destino.

#### S4 — Refator nomenclatura AP6 (Skill 8 ATÔMICA L2 vs `inventario_pipeline` C3)
- Extrair método `executar_skill8_atomica(picking_ids, constants_por_acao, dry_run)` do orchestrator. Encapsula 5 ops C+D sobre `account.move`: validar constants + `action_liberar_faturamento` + polling invoice + validar fatura vs constants + SEFAZ Playwright.
- Atualizar §6 CLAUDE.md catálogo: Tabela 1 ganha entrada `faturando-odoo` (Skill 8 ATÔMICA L2 — método novo); Tabela 2 renomeia orchestrator para `inventario_pipeline`.
- Atualizar SKILL.md `faturando-odoo` fachada: clarificar que é fachada para método ATÔMICA + opcionalmente orchestrator C3 completo.
- Renomear `faturamento_pipeline.py` → `inventario_pipeline.py` (rename + git mv + ajustar imports). OPCIONAL — pode ficar para v22+.

#### S5 — Escrever folhas L3 pendentes (após AP6)
- `fluxos/1.1-faturar-saida-pura.md` (só saída sobre Skill 8 ATÔMICA L2 + Skill 2 + Skill 5).
- `fluxos/1.3-transferencia-completa.md` (composição saída + entrada).
- `fluxos/2.3-transferir-saldo-codigo.md` (UnificacaoCodigos).

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER — regras v14a-fix + v19+).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (regra v14a-ops — SUPERADO ao final v22+).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (8 documentos)
- [ ] Baseline pytest 563 confirmado
- [ ] AskUserQuestion §1.4 confirmou escopo S1-S5 com Rafael

Implementação:
- [ ] S1 — bulk REAL PROD via opt-in: subagente executou onda completa + verificação direta no Odoo OK
- [ ] S2 — remoção tampão arquitetural: Skill 5 v15a removida + Skill 7 V1 STRICT removida + ETAPAS E/F legacy removidas + pytest atualizado
- [ ] S3 — CONSTANTS expandidas para FB e CD destino + canary por direção nova + pytest mockados
- [ ] S4 — método `executar_skill8_atomica` extraído + Tabela 1/2 §6 atualizadas
- [ ] S5 — 3 folhas L3 escritas (1.1, 1.3, 2.3)

Validação:
- [ ] Pytest baseline ≥ N atual confirmado em §1.3 + novos testes (estimativa 8-15 novos)
- [ ] Bulk REAL: onda completa OK no Odoo PROD (sem duplicação)
- [ ] ≥1 code-reviewer paralelo (constituição §6 + remoção tampão + idempotência)
- [ ] Atualizações cross-refs: SKILL.md `escriturando-odoo` + SKILL.md `faturando-odoo` + ROADMAP HANDOFF + PLANEJAMENTO §0

Documentação:
- [ ] Atualizar antipadrões §6.5 CLAUDE.md (AP2 ✅ se bulk validar; AP6 ✅ se refator OK)
- [ ] Atualizar §6 catálogo (Tabela 1 ganha Skill 8 ATÔMICA L2; Tabela 2 renomeia)
- [ ] Atualizar PROTECAO_PROXIMA_SESSAO.md se detectou novo antipadrão
- [ ] Memória NOVA `[[bulk-fluxo-l3-pattern]]` se padrão emergir do bulk
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Bulk REAL falha mid-onda (algum invoice nos 4 INDUSTR não é totalmente idempotente — caso anômalo) | BAIXA | ALTO | Idempotência via 3 caminhos do FIX B já cobre 100% dos cenários conhecidos. Subagente roda 1 caso adicional (não os mesmos 4 do canary v20+) para validar caso novo. Se falhar, abort + investigar. |
| Remoção tampão quebra pytest existentes | MÉDIA | MÉDIO | Plano: remover incrementalmente (S5 v15a → tester → V1 STRICT → tester → ETAPAS E/F → tester). Cada remoção rodar pytest tests/odoo/. Se falhar, retroceder. |
| Constants FB/CD destino erradas (canary direção nova falha) | MÉDIA | MÉDIO | Antes de bulk PROD com direção nova, dry-run + validar via XML-RPC read que team_id/payment_term_id/picking_type_id existem + pertencem à company correta. |
| Refator AP6 quebra orchestrator existente | MÉDIA | ALTO | S4 último na ordem. Extrair método `executar_skill8_atomica` como WRAPPER sobre código existente (não move código fonte ainda; v22+ extrai service L2 dedicado). Pytest cobertura antes/depois. |
| Sessão estoura tokens | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` para bulk REAL; principal só implementa S2+S3+S4+S5 + revisa. |
| Encontra problema novo no FLUXO L3 1.2.x que canary não pegou | MÉDIA | ALTO | Bulk é 3-4 invoices similares ao canary; bug novo provável só se direção mudar. Subagente DEVE verificar empiricamente comportamento (não assumir). |

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
