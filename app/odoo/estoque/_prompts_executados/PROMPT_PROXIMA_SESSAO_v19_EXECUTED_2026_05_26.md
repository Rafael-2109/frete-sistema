# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v19+ refator arquitetural — extrair átomos comuns para Skill 7 ABRANGENTE + criar FLUXO L3 1.2.1 + reescrever ETAPA F do orchestrator Skill 8.
**Base**: commit `f30348f4` (v18 Fase 0 — saneamento documental).
**Risco**: MUITO ALTO (cross-modulo).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-26 v18 Fase 0 (template definitivo — substitui 8 prompts acumulados).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N13 + AR1-AR5 + lições memories).
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo) + §6.5 (antipadrões CAUSA/CONSEQUÊNCIA/COMO EVITAR) + §14 (histórico desvios) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer.
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 (regra inviolável 0).
6. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
7. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
8. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.

### 1.3 Confirmar baseline pytest

```bash
timeout 60 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 521 passed (v18 baseline)
```

Se ≠ 521 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão N-1)

### Estado do código
- **Commit base**: `f30348f4` (v18 Fase 0 — saneamento documental).
- **Baseline pytest**: 521 verdes em 14.76s.
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura
- **Constituição saneada v18 Fase 0**: §1.1 + §3.1 + §6 (4 tabelas) + §6.5 + §14 + §15.
- **Escudo PROTECAO_PROXIMA_SESSAO.md**: ✅ vivo.
- **8 prompts antigos arquivados** em `_prompts_executados/`.
- **Histórico v13-v18 migrado** para VALIDACAO_FINAL_SESSAO.md.

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (7): 1, 2, 2.4, 4, 5, 7 ⚠️V1 STRICT, 9 (READ)
- Orchestrators C3 (2): Skill 6 executor, Skill 8 pipeline A-F + recovery v18
- Sub-skill PRE-FLIGHT: auditando-cadastro-fiscal-odoo
- Fluxos L3 escritos (9): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1
- Fluxos L3 pendentes (galho 1 TODO): 1.1.x, 1.2.1, 1.3, 2.3

### Antipadrões documentados (CLAUDE.md §6.5)
- **AP1**: Skill 7 V1 STRICT (raise NotImplementedError) — refator v19+
- **AP2**: Skill 8 ETAPA F invoca Skill 5 atomo INLINE (caminho B paliativo) — refator v19+
- **AP3**: Orchestrator C3 chamando skills INLINE (origem AP1+AP2) — corrigido em §6.5 com 3 tabelas
- **AP4**: V1 STRICT raise ANTES de dry-run check — refator v19+
- **AP5**: Criar gotcha sem ler docstrings de constants (lição G037 v18)

### Insight arquitetural confirmado por Rafael
Comparação `RecebimentoLfOdooService` (12 passos) × `LancamentoOdooService` (4 passos) × `escriturar_dfe_lf.py` (FLUXO A) revela **8 átomos comuns** que devem compor Skill 7 ABRANGENTE:
1. `buscar_ou_criar_dfe(chave_nfe, xml?, company)`
2. `escriturar_dfe(dfe_id, l10n_br_tipo_pedido, ...)`
3. `gerar_po_from_dfe(dfe_id, ctx_force_company)` (fire_and_poll)
4. `preencher_po(po_id, kwargs)`
5. `preencher_picking_de_po(po_id, lotes)` (Skill 5 — novo átomo)
6. `criar_invoice_from_po(po_id)`
7. `postar_invoice(invoice_id, fiscal_setup)`
8. `transmitir_sefaz(invoice_id)` (já existe Skill 8 ETAPA D)

> Tendência futura (Rafael): `RecebimentoLfOdoo` + `LancamentoOdoo` viram **WRAPPERS** dos átomos Skill 7. Inversão da relação atual.

### Pendências (checkpoints Skill 8)
- C14-C17 ✅ v18 (recovery + SKILL.md + pytest + smokes)
- **C18 folhas L3 (1.1*, 1.3, 1.2.1)** ⬜ — DEPENDE refator v19+ desta sessão
- C19 cross-refs final ⬜
- C20 canary REAL PROD ⬜
- C21 bulk REAL PROD ⬜
- C22 code-review final ⬜
- C23 commit + arquivar `09_executar_onda1_bulk.py` ⬜

---

## §3. ESCOPO DESTA SESSÃO (v19+ — refator Skill 7 ABRANGENTE)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Eliminar **AP1 + AP2 + AP3 + AP4** extraindo átomos comuns para Skill 7 ABRANGENTE e criando FLUXO L3 1.2.1. Refator NÃO mexe em `RecebimentoLfOdooService` (4562 LOC) nem `LancamentoOdooService` (16 etapas) — apenas EXTRAI átomos que SERÃO USADOS pela Skill 7 + futuros wrappers.

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S1 — Extrair atomos comuns para Skill 7 ABRANGENTE (5 átomos novos no service `escrituracao.py`)

Criar 5 atomos novos na Skill 7 service (sem mexer no `EscrituracaoLfService.criar_recebimento_orchestrado` atual — mantém V1 STRICT como wrapper temporário):

1. `buscar_ou_criar_dfe(chave_nfe: str, xml: Optional[str], company_id: int) → dfe_id`
2. `escriturar_dfe(dfe_id: int, l10n_br_tipo_pedido: str, **kwargs) → bool`
3. `gerar_po_from_dfe(dfe_id: int, ctx_force_company: bool = True, timeout_s: int = 1800) → po_id`
4. `preencher_po(po_id: int, **kwargs) → bool` (team_id, payment_term, picking_type, operacao, partner_ref)
5. `criar_invoice_from_po(po_id: int) → invoice_id`

Pre-cond comum: dry-run sempre planeja (NÃO `raise NotImplementedError` em pre-cond — só write-path raise). Corrige AP4.

Cada átomo: 2-3 pytest mockados verdes mínimos.

#### S2 — Extender Skill 5 com átomo `preencher_lotes_picking`

Novo átomo em `picking.py`:
- `preencher_lotes_picking(picking_id: int, lote_default: str = 'MIGRAÇÃO', mapping_lote_por_ml: Optional[Dict] = None) → bool`
- Aplicável para pickings NATIVOS (criados via DFe→PO) — não substitui `criar_picking_entrada_destino_manual` (caminho B paliativo permanece arquivado).
- 3+ pytest novos.

#### S3 — Criar FLUXO L3 `1.2.1-escriturar-dfe-industrializacao.md`

Folha de fluxo em `app/odoo/estoque/fluxos/1.2.1-escriturar-dfe-industrializacao.md`:
- **Premissas**: chave_nfe da NF SEFAZ-OK; produto + lote; CFOP esperado.
- **Sequência**: Skill 7 buscar_ou_criar_dfe → Skill 7 escriturar_dfe → Skill 7 gerar_po_from_dfe → Skill 7 preencher_po → Skill 7 confirmar_po → Skill 5 preencher_lotes_picking → Skill 7 criar_invoice_from_po → Skill 7 postar_invoice.
- **Gotchas**: G011 timing CIEL IT (polling 30min) + G016 SSL drop + l10n_br_tipo_pedido='serv-industrializacao' → CFOP 1901 derivado.
- **Exemplo**: caso real INDUSTRIALIZACAO_FB_LF.

#### S4 — Reescrever orchestrator Skill 8 ETAPA F para invocar FLUXO L3 1.2.1

Substituir invocação INLINE de `criar_picking_entrada_destino_manual` por composição dos átomos Skill 7 + Skill 5 conforme FLUXO L3 1.2.1. Corrige AP2.

**IMPORTANTE**: manter `criar_picking_entrada_destino_manual` ARQUIVADO como caminho B paliativo (DFe pode demorar real; fallback) — documentar no header da função e em `_prompts_executados/`.

#### S5 — Atualizar antipadrões §6.5 do CLAUDE.md

Marcar AP1+AP2+AP3+AP4 como ✅ RESOLVIDOS (refator v19 aplicado). Manter AP5 (não foi tocado).

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER — regras v14a-fix + v19+).
- ❌ Implementar wrappers de RecLF/LancOdoo sobre átomos Skill 7 (próximo passo v20+).
- ❌ Canary REAL PROD (próximo passo v20+).
- ❌ Folhas L3 do galho 1 que não sejam 1.2.1 (1.1.x, 1.3, 1.5 ficam para v20+).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (8 documentos)
- [ ] Baseline pytest 521 confirmado
- [ ] AskUserQuestion §1.4 confirmou escopo S1-S5 com Rafael

Implementação:
- [ ] S1 — 5 átomos novos em `escrituracao.py` + pytest cada
- [ ] S2 — `preencher_lotes_picking` em `picking.py` + pytest
- [ ] S3 — FLUXO L3 `1.2.1-escriturar-dfe-industrializacao.md`
- [ ] S4 — orchestrator ETAPA F reescrito invocando FLUXO 1.2.1
- [ ] S5 — antipadrões §6.5 marcados ✅ RESOLVIDOS (AP1+AP2+AP3+AP4)

Validação:
- [ ] Pytest baseline ≥530 verdes (521 + ~10 novos)
- [ ] Smoke dry-run PROD ETAPA F via FLUXO L3 1.2.1 (NÃO real — só plano)
- [ ] ≥1 code-reviewer paralelo (constituição §6 conformance + edge cases dos átomos novos)
- [ ] Atualizações cross-refs: SKILL.md `escriturando-odoo` + SKILL.md `faturando-odoo` + ROADMAP HANDOFF + PLANEJAMENTO §0 + §12 trilha v19

Documentação:
- [ ] Atualizar antipadrões §6.5 CLAUDE.md (AP1-AP4 ✅ se resolvidos)
- [ ] Atualizar PROTECAO_PROXIMA_SESSAO.md se detectou novo antipadrão (§6 abaixo)
- [ ] Memória NOVA `[[skill7-abrangente-pattern]]` se padrão emergir
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Átomos Skill 7 ABRANGENTE divergem do contrato de `RecebimentoLfOdooService` | MÉDIA | ALTO (refator inutil) | Antes de codar átomo, ler INTEIRO o método análogo no RecebimentoLfOdoo (header + corpo) e mapear contrato. NÃO importar/usar — só ler. |
| FLUXO L3 1.2.1 sem caso real para validar | ALTA | MÉDIO | Smoke dry-run apenas; validação REAL fica para v20+ canary. Documentar como "fluxo escrito sem caso real validado v19+; canary v20+". |
| Orchestrator ETAPA F quebra após reescrita | ALTA | ALTO | Manter `criar_picking_entrada_destino_manual` ARQUIVADO como fallback. Flag `--usar-fluxo-l3-1-2-1` para A/B testing. Reverter se smoke falhar. |
| Pytest novos validam só feliz path | MÉDIA | MÉDIO | code-reviewer paralelo foca em edge cases (timeout, SSL drop, fire_and_poll mismatch). |
| Sessão estoura tokens | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` via Task tool para execução; principal só implementa átomos novos. (Lição v7 ~150k tokens.) |
| Premissa errada na nova Skill 7 (caso G037 v18) | MÉDIA | ALTO | LER `operacoes_fiscais.py` + `picking_types.py` INTEIROS antes (AP5). Validar com Rafael antes de codar. |

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
