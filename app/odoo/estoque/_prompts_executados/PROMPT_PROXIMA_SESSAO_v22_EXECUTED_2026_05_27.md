# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v22+ verificar resultado pipeline retry rodado em background (v21+) + remoção tampão arquitetural (se OK) + refator nomenclatura AP6 + folhas L3 pendentes + estender sub-skill C5.
**Base**: commits v21+ EXECUTED (8 entregas concretas em PROD + Skill 2 átomo NOVO `transferir_loc_e_lote` + fix G-AUDIT-1). 576 pytest verdes.
**Risco**: MÉDIO (depende do resultado pipeline retry; se OK refator é seguro; se FALHA pode exigir nova investigação).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-27 v21+ EXECUTED (sucessor do v20+ EXECUTED).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20,21}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N21 + AR1-AR11 + lições memories). **Atenção especial a N21+AR11 NOVOS v21+** (bug G-AUDIT-1: passar string em coluna INTEGER causa rollback cascateado).
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo — Skill 2 ganhou 4º modo D v21+) + §6.5 (antipadrões — AP2 com resolução parcial v20+; AP6 pendente v22+) + §14 (histórico desvios — D-V21-*) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer.
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
7. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
8. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 576 passed (v21+ baseline)
```

Se ≠ 576 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v21+ — FINALIZADA com 3 bugs descobertos)

### Estado do código
- **Commit base**: v21+ EXECUTED (8 entregas PROD + Skill 2 átomo NOVO + fix G-AUDIT-1 + migration G-AUDIT-2). Pipeline real NÃO chegou ao SEFAZ (3 retries, último com G-AUDIT-3 pendente).
- **Baseline pytest**: 576 verdes em ~15s (+11 net v21+ via Skill 2 átomo novo + 0 net G-AUDIT-1/2 fixes).
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura
- **Skill 2 GANHOU 4º MODO atômico** `transferir_loc_e_lote` (v21+) — loc+lote em 1 chamada. ~225 LOC service + 11 pytest + CLI `--loc-e-lote` + SKILL.md atualizada. Caso real validado em PROD: ETAPA 0 fluxo bulk (250.330 SLEEVE + 1,8 CORANTE de Indisp/MIGRAÇÃO → Estoque/P-15/05).
- **G-AUDIT-1 FIX aplicado**: linha 249-269 orchestrator — removido `etapa=fase` (string em coluna INTEGER causava `psycopg2.errors.InvalidTextRepresentation` + rollback cascateado em F5a).
- **G-AUDIT-2 MIGRATION aplicada**: `operacao_odoo_auditoria.acao` VARCHAR(20)→VARCHAR(60), `status` →30, `pipeline_etapa` →40. Modelo Python sincronizado. Arquivos .sql + .py em `scripts/migrations/v21_ampliar_operacao_odoo_auditoria.{sql,py}`.
- **G-AUDIT-3 PENDENTE v22+ (ARQUITETURAL)**: Skill 5 `criar_picking_inter_company` reaproveita picking state=cancel → `action_assign` falha em F5b com `<Fault 2: 'Nada para verificar a disponibilidade.'>`. Fix exige: `if state == 'cancel': criar novo`.
- **8 entregas concretas em PROD na v21+**: cancel 3 INT zumbi (50 MLs + 49 moves) + DELETE 23.483 linhas ciclo + lote literal P-15/05 lot_id=60033 + ETAPA 0 real (250.330 + 1,8) + WRITE produtos (price + tipo + barcode) + auto-fix C5 barcode + INSERT 2 ajustes id=176013/176014 + fix bug G-AUDIT-1 + migration G-AUDIT-2.

### Estado dos 2 ajustes de teste no DB local (pós retries)
- id=176013 (210010800 250.330): `status=APROVADO, fase_pipeline='F5b_FALHA', picking_id_odoo=321600, invoice_id=None, chave_nfe=None`
- id=176014 (104000046 1.8): `status=APROVADO, fase_pipeline='F5b_FALHA', picking_id_odoo=321600, invoice_id=None, chave_nfe=None`
- Picking 321600 (FB/SAI/IND/01601): `state=cancel` (cancelado no retry 1)
- Quants ETAPA 0: intactos (saldos preservados — pipeline nunca chegou a tocar saldo, só criou picking depois cancelou)

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (7): 1, 2 (**4 modos** A/B/C/D v21+), 2.4, 4, 5 (7 átomos), 7 ABRANGENTE v20+, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, `faturamento_pipeline` (pipeline A-F + recovery + dispatch fluxo L3 1.2.x v19+ + opt-in v20+ + fix G-AUDIT-1 v21+).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo` (V1 — limitação descoberta v21+: NÃO cobre G007 price=0 nem l10n_br_tipo_produto).
- Fluxos L3 escritos (11): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+.
- Fluxos L3 pendentes: 1.1.x, 1.3, 2.3 (dependem refator AP6).

### Pendências críticas
- **Verificar resultado pipeline retry v21+** (rodando background ao final da sessão) — log em `/tmp/log_retry_pipeline_v21_*.json`
- Se OK: prosseguir S2 remoção tampão
- Se FALHA: investigar novo erro (provavelmente cadastro fiscal não-coberto C5 ou robô CIEL IT)

### Estado dos 2 ajustes do teste v21+ (no DB local)
- id=176013 (210010800 250.330): status=APROVADO, fase=? (depende do resultado do pipeline retry)
- id=176014 (104000046 1.8): idem
- Cross-check Odoo: stock.quant 264582 (FB/Estoque/P-15/05 lot=60033) deve ter 250.330 (ETAPA 0 confirmou); 264585 (FB/Estoque/sem-lote 104000046) deve ter 1,8

---

## §3. ESCOPO DESTA SESSÃO (v22+ — verificar pipeline retry + remoção tampão + refator AP6 + folhas L3 pendentes + C5 estendido)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Verificar resultado do pipeline retry v21+ (rodado em background). Se OK, prosseguir refator arquitetural (AP6 + remoção tampão + folhas L3 + C5 estendido). Se FALHA, investigar novo erro e decidir caminho.

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S0 — Resolver bug G-AUDIT-3 + force-reset ajustes para retry pipeline (NA ABERTURA)
- **Fix Skill 5** `criar_picking_inter_company` em `app/odoo/estoque/scripts/picking.py`: adicionar condição `if picking_existente.state == 'cancel': criar novo (não reaproveitar)`. Estados válidos para reaproveitar: draft/confirmed/assigned/done.
- Pytest novo cobrindo cenário "retry após cancel": picking existente state=cancel + origin match → cria NOVO picking (não reaproveita).
- **Force-update ajustes** 176013/176014: `UPDATE ajuste_estoque_inventario SET picking_id_odoo=NULL, fase_pipeline=NULL WHERE id IN (176013, 176014)`.
- Re-rodar pipeline real A→F com mesmos args. Esperado: pipeline cria picking NOVO (não reaproveita 321600 cancelado), F5a/F5b/F5c rodam, ETAPA C/D/F via L3.

#### S2 — Remoção tampão arquitetural (após pipeline OK)
- Remover `criar_picking_entrada_destino_manual` (Skill 5 v15a) — `app/odoo/estoque/scripts/picking.py` + ajustar pytest `test_stock_picking_service.py`
- Remover wrapper V1 STRICT `criar_recebimento_orchestrado` (Skill 7) — `app/odoo/estoque/scripts/escrituracao.py` + ajustar 11 pytest de `test_escrituracao_lf_service.py`
- Remover ETAPAS E/F legacy do orchestrator — manter apenas `_executar_etapa_f_via_fluxo_l3` (renomear para `executar_etapa_f`)
- Atualizar §6 catálogo CLAUDE.md (Tabela 1 Skills L2 — remover docblock DEPRECATED Skill 5)

#### S3 — Refator nomenclatura AP6 (Skill 8 ATÔMICA L2)
- Extrair método `executar_skill8_atomica(picking_ids, constants_por_acao, dry_run)` do orchestrator. Encapsula 5 ops C+D sobre `account.move`: validar constants + `action_liberar_faturamento` + polling invoice + validar fatura vs constants + SEFAZ Playwright.
- Atualizar §6 CLAUDE.md catálogo: Tabela 1 ganha entrada `faturando-odoo` (Skill 8 ATÔMICA L2 — método novo); Tabela 2 renomeia orchestrator para `inventario_pipeline`.
- Rename `faturamento_pipeline.py` → `inventario_pipeline.py` (rename + git mv + ajustar imports). OPCIONAL — pode ficar para v23+.

#### S4 — Expandir CONSTANTS_FLUXO_L3 para FB e CD destino
- Para cada direção pendente: descobrir team_id, payment_term_id, picking_type_id por company destino
- Atualizar `CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO` mapa
- Canary REAL PROD para cada direção nova (1 invoice por direção)
- Pytest mockados validando dispatch correto

#### S5 — Escrever folhas L3 pendentes (após AP6)
- `fluxos/1.1-faturar-saida-pura.md` (só saída sobre Skill 8 ATÔMICA L2 + Skill 2 + Skill 5)
- `fluxos/1.3-transferencia-completa.md` (composição saída + entrada)
- `fluxos/2.3-transferir-saldo-codigo.md` (UnificacaoCodigos)

#### S6 — Estender Sub-skill C5 V1 'inventario' (descoberta v21+)
- Cobrir G007 (`standard_price = 0` → BLOQUEIO ou AUTO-FIX setando 0.01)
- Cobrir `l10n_br_tipo_produto = False` (BLOQUEIO ou AUTO-FIX setando default '01' Matéria Prima)
- Sub-skill V1 + pytest novos

#### S7 — Resolver lote 'P-15/05' (descoberta v21+)
- Adicionar arg `forcar_lote_literal=True` em `resolver_lote_destino` que pula proxy P-15/05='sem-lote' e cria/busca lote literal real
- Atualizar todos callers que usam 'P-15/05' como literal vs proxy

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER — regras v14a-fix + v19+).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (regra v14a-ops — SUPERADO ao final v22+).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (8 documentos)
- [ ] Baseline pytest 576 confirmado
- [ ] **S1 PRIORITÁRIO**: ler log `/tmp/log_retry_pipeline_v21_*.json` + cross-check Odoo ajustes 176013/176014
- [ ] AskUserQuestion §1.4 confirmou escopo S1-S7 com Rafael

Implementação:
- [ ] S1 — verificação pipeline retry OK (ou erro identificado)
- [ ] S2 — remoção tampão arquitetural (incremental: Skill 5 v15a → tester → V1 STRICT → tester → ETAPAS E/F → tester)
- [ ] S3 — método `executar_skill8_atomica` extraído + Tabela 1/2 §6 atualizadas
- [ ] S4 — CONSTANTS expandidas para FB e CD destino + canary por direção nova + pytest mockados
- [ ] S5 — 3 folhas L3 escritas (1.1, 1.3, 2.3)
- [ ] S6 — Sub-skill C5 estendida (G007 + l10n_br_tipo_produto)
- [ ] S7 — Resolver lote P-15/05 com flag literal

Validação:
- [ ] Pytest baseline ≥ N atual confirmado + novos testes (estimativa 12-20 novos)
- [ ] ≥1 code-reviewer paralelo (constituição §6 + remoção tampão + C5 estendido)
- [ ] Atualizações cross-refs: SKILL.md `escriturando-odoo` + SKILL.md `faturando-odoo` + ROADMAP HANDOFF + PLANEJAMENTO §0

Documentação:
- [ ] Atualizar antipadrões §6.5 CLAUDE.md (AP2 ✅ se bulk validar; AP6 ✅ se refator OK)
- [ ] Atualizar §6 catálogo (Tabela 1 ganha Skill 8 ATÔMICA L2; Tabela 2 renomeia)
- [ ] Atualizar PROTECAO_PROXIMA_SESSAO.md se detectou novo antipadrão (esperado: nenhum se sessão correr bem)
- [ ] Memória NOVA `[[g_audit_1_etapa_int_vs_string]]` para gravar lição v21+ G-AUDIT-1
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Pipeline retry v21+ ainda FALHA por causa nova não-G-AUDIT-1 | MÉDIA | ALTO | S1 prioritário: ler log antes de qualquer outra ação. Se falha: investigar via `--modo resume --apenas-etapa <X>` para retomar do ponto onde parou. |
| Picking 321600 ainda órfão (cancel real do v21+ pode ter falhado) | BAIXA | MÉDIO | Verificar via Odoo direto no início. Se ainda draft: cancel via Skill 5. |
| Remoção tampão quebra pytest existentes | MÉDIA | MÉDIO | Plano: remover incrementalmente (Skill 5 v15a → tester → V1 STRICT → tester → ETAPAS E/F → tester). Cada remoção rodar pytest tests/odoo/. Se falhar, retroceder. |
| Constants FB/CD destino erradas (canary direção nova falha) | MÉDIA | MÉDIO | Antes de bulk PROD com direção nova, dry-run + validar via XML-RPC read que team_id/payment_term_id/picking_type_id existem + pertencem à company correta. |
| Refator AP6 quebra orchestrator existente | MÉDIA | ALTO | S3 incremental. Extrair método `executar_skill8_atomica` como WRAPPER sobre código existente (não move código fonte ainda; v23+ extrai service L2 dedicado). Pytest cobertura antes/depois. |
| Sessão estoura tokens (já longa em v21+) | ALTA | ALTO | Spawn subagente `gestor-estoque-odoo` para casos reais; principal só implementa refator + revisa. |
| Bug schema futuro tipo G-AUDIT-1 não detectado por pytest mockado | MÉDIA | ALTO | Considerar test de integração para auditoria (com REAL DB) — mas é trabalho separado. |

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
