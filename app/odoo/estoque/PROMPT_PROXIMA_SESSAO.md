# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v24+ codificar fix raiz B-V23-1 (Skill 7 `criar_dfe_a_partir_do_invoice_saida` force company_id=destino nas dfe.lines) + B-V23-2 (novo átomo `resolver_account_id_por_company` + hook em `gerar_po_from_dfe`/`preencher_po`) + bulk REAL PROD (não só 2 ajustes) via opt-in `--usar-fluxo-l3-v19` com fixes aplicados. Adiados v25+: AP6 refator + expand CONSTANTS FB/CD + C5 G007.
**Base**: commit a fazer v23+ (G039 codificado + 17 testes net + invoice ENTIN/2026/05/0055 posted PROD + 2 bugs B-V23-1/2 documentados). 597 pytest verdes.
**Risco**: MÉDIO (2 fixes em Skill 7 ABRANGENTE — código já validado em PROD com workaround manual; bulk REAL PROD acende novos cenários).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-27 v23+ EXECUTED (sucessor do v22+ EXECUTED).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20,21,22,23}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N26 + AR1-AR12 + lições memories). **Atenção especial a N25/N26 NOVOS v23+** (B-V23-1 e B-V23-2 — bugs Skill 7 PENDENTES) e N24 ✅ RESOLVIDO v23+ (G039 codificado).
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo) + §6.5 (antipadrões) + §14 (histórico desvios — D-V22 + D-V23) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer.
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
7. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
8. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 597 passed (v23+ baseline)
```

Se ≠ 597 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v23+ — FINALIZADA — Caminho B 100% PROD + G039 codificado + 2 bugs Skill 7 descobertos)

### Estado do código
- **Commit base**: v23+ EXECUTED (G039 codificado + B-V23-1/2 documentados + invoice ENTIN/2026/05/0055 posted PROD).
- **Baseline pytest**: 597 verdes (580 v22+ + 17 net v23+).
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura
- **Skill 7 GANHOU átomo G039** v23+ — `garantir_purchase_team(user_id, company_id, dry_run)` em `escrituracao.py` ~150 LOC + constant `_COMPANY_SIGLA_DEFAULT` (1=FB, 4=CD, 5=LF). Idempotência por (user_id, company_id, active=True); CREATE com nome template "Aprovação {sigla} - {primeiro_nome}". 7 pytest cobrindo cenários.
- **Orchestrator GANHOU hook G039** v23+ — `_resolver_team_g039` com cache `_g039_team_cache: Dict[(uid, company_id), team_id]`; lazy auth; substitui `team_id` STATIC no `_resolver_constants_fluxo_l3` pelo team correto. Fallback silencioso (warning + STATIC) se hook falhar. 7 pytest cobrindo hit cache, miss, falha, override constants, fallback.
- **Orchestrator GANHOU fix S2** v23+ — `_contar_pendentes_por_etapa` ETAPA F aceita `status IN (PROPOSTO, APROVADO, EXECUTADO)`. Demais etapas preservam PROPOSTO/APROVADO. 3 pytest.
- **FLUXO L3 1.2.x CAMINHO B VALIDADO 100% em PROD v23+** — primeiro fim-a-fim: PO 42419 confirmada (team 143 RAFAEL) → picking 321617 done (LF/Estoque) → invoice ENTIN/2026/05/0055 posted (R$ 12.525,54 untaxed CFOP 1949). Validação cascateada descobriu 2 bugs Skill 7 (B-V23-1/2) que precisaram workaround manual PROD.

### Estado dos 2 ajustes de teste v23+ (museum vivo)
- id=176013/176014: `status='EXECUTADO', fase_pipeline='F5f_ENTRADA_OK'`
- Picking saída 321601 done; saída SEFAZ 716448 chave 35260561724241000178550010000945661007164482
- PO entrada 42419 `state=purchase, team_id=143, picking_ids=[321617], invoice_ids=[717630]`
- Picking entrada 321617 (LF/IN/01779): `state=done` (LF/Estoque)
- Invoice entrada 717630 (ENTIN/2026/05/0055): `state=posted, move_type=in_invoice, company=LF, journal=1047 'ENTRADA REMESSA INDUSTRIALIZAÇÃO', amount_untaxed=12525.54, amount_total=0.0 (neutralizado CFOP 1949)`
- DFe entrada 43533 (lines company corrigidas v23+ workaround)

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (7): 1, 2 (4 modos A/B/C/D v21+), 2.4, 4, 5 (7 átomos + G-AUDIT-3 v22+), **7 ABRANGENTE v20+ + G039 v23+** (8 átomos total: 7 ABRANGENTES + garantir_purchase_team), 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, `faturamento_pipeline` (pipeline A-F + recovery + dispatch fluxo L3 1.2.x v19+ + opt-in v20+ + fix G-AUDIT-1 v21+ + hook G039 v23+ + fix contador F v23+).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo` (V1 'inventario' v14b + G038 v22+).
- Fluxos L3 escritos (11): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+ (Caminho B 100% validado v23+).

### Bugs arquiteturais descobertos v23+ (PENDENTES v24+)

#### B-V23-1 — `criar_dfe_a_partir_do_invoice_saida` cria dfe.lines com company_id ERRADO
- Lines herdam company_id do XML da SAÍDA (FB=1) em vez de DESTINO (LF=5).
- Sintoma: passo 9 falha 'leitura dfe.line' (Fault 4).
- Workaround v23+: write dfe.line.company_id manualmente.
- **Fix v24+**: codificar no átomo — após `action_processar_arquivo_manual`, read dfe.lines + write company_id=company_destino.

#### B-V23-2 — `gerar_po_from_dfe`/`preencher_po` deixa PO.line.account_id em company errada
- account_id resolvido para account.account da FONTE (FB id=22611) em vez de DESTINO (LF id=26459).
- Sintoma após fix B-V23-1: "Empresas incompatíveis".
- Workaround v23+: write PO.line.account_id manualmente.
- **Fix v24+**: novo átomo helper `resolver_account_id_por_company(account_id_fonte, company_destino)` + hook nos átomos Skill 7 que tocam PO.lines.

---

## §3. ESCOPO DESTA SESSÃO (v24+ — codificar B-V23-1 + B-V23-2 + bulk REAL PROD)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Codificar os 2 bugs descobertos em v23+ (B-V23-1 e B-V23-2) no Skill 7 ABRANGENTE → eliminar workarounds manuais → permitir bulk REAL PROD via FLUXO L3 1.2.x caminho B (não só 2 ajustes 176013/14, mas onda completa).

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S1 — Codificar fix raiz B-V23-1 no átomo `criar_dfe_a_partir_do_invoice_saida`
- Após `action_processar_arquivo_manual` (que cria DFe + lines), ler dfe.lines criadas (search por dfe_id) + write `{'company_id': company_destino}`.
- Idempotência: read antes do write; se já estiver correto, skip.
- Pytest novo cobrindo: lines em company errada (write executado) + lines em company correta (skip idempotente).
- Smoke real PROD: criar DFe novo via XML de outra invoice de SAÍDA → verificar lines.company_id já correto sem workaround manual.

#### S2 — Codificar fix raiz B-V23-2: átomo helper + hook
- Novo átomo Skill 7 `resolver_account_id_por_company(account_id_fonte, company_destino)`: read account.account fonte (read code) → search [('code','=',code), ('company_id','=',company_destino)] → retorna id destino OU None se não encontrar (caller decide o que fazer).
- Hook em `gerar_po_from_dfe` OU `preencher_po` (decidir onde): após criar/preencher PO.lines, iterar lines + para cada line: read `account_id` + chamar `resolver_account_id_por_company` + write se diferente.
- Pytest novo cobrindo: account em company correta (skip) + account em company errada (resolve + write) + account não existe na destino (FALHA com erro claro).

#### S3 — Bulk REAL PROD via opt-in `--usar-fluxo-l3-v19`
- Pós-S1+S2 OK: rodar `executar_pipeline_resume --apenas-etapa F --usar-fluxo-l3-v19 --ciclo INVENTARIO_2026_05 --confirmar --confirmar-sefaz` sobre conjunto maior de ajustes (não só 176013/14 que já estão em F5f_ENTRADA_OK).
- Monitorar: novos bugs cascateados? Performance? Idempotência ETAPA F multi-invoice?
- Documentar findings em `VALIDACAO_FINAL_SESSAO.md` §"Sessão v24+".

#### S4 — Expand CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO para FB=1 e CD=4
- Pós-S3 OK: mapear `team_id` + `payment_term_id` + `picking_type_id` + `payment_provider_id` para FB e CD destino (atualmente só LF=5 mapeada).
- Pré-cond: descobrir IDs corretos via XML-RPC (queries similares ao que foi feito v23+ para account_id LF=26459).
- Pytest mockado cobrindo as 3 direções.

#### S5 — Itens adiados v23+ (oportunístico)
- AP6 refator: extrair Skill 8 ATÔMICA L2 do orchestrator (5 ops C+D sobre `account.move`)
- Folhas L3 1.1.x (só saída) + 1.3 (transferência completa)
- C5 G007 (standard_price=0) + l10n_br_tipo_produto

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (SUPERADO ao final v22+).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (8 documentos)
- [ ] Baseline pytest 597 confirmado
- [ ] Cross-check Odoo: estado dos ajustes 176013/14, PO 42419, invoice 717630 (estado preservado)
- [ ] AskUserQuestion §1.4 confirmou escopo S1-S5 com Rafael

Implementação:
- [ ] S1 — B-V23-1 fix no `criar_dfe_a_partir_do_invoice_saida` + pytest + smoke real PROD
- [ ] S2 — B-V23-2 átomo `resolver_account_id_por_company` + hook + pytest + smoke real PROD
- [ ] S3 — Bulk REAL PROD via opt-in (escolher subset de ajustes para o canary do bulk)
- [ ] S4 — Expand CONSTANTS para FB + CD (se sobrar tempo)
- [ ] S5 — AP6/folhas L3/C5 G007 conforme tempo

Validação:
- [ ] Pytest baseline ≥ 597 + novos testes (estimativa 4-8 novos)
- [ ] ≥1 code-reviewer paralelo (Skill 7 fixes)
- [ ] Atualizações cross-refs: SKILL.md `escriturando-odoo` + ROADMAP HANDOFF + PROTECAO N25/N26 (passar para RESOLVIDOS)

Documentação:
- [ ] Atualizar PROTECAO N25/N26 (RESOLVIDOS)
- [ ] Atualizar CLAUDE.md §6.5 + §14 (D-V23-2/3 fix raiz codificado)
- [ ] Memórias `[[b_v23_1_dfe_line_company_id]]` + `[[b_v23_2_po_line_account_id]]` resolvidas
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Fix B-V23-1 quebra cenários onde dfe.lines DEVEM ficar em company fonte (ex: DFe de COMPRA externa) | BAIXA | ALTO | Restringir fix ao caso `criar_dfe_a_partir_do_invoice_saida` (NF interna nossa) — não tocar fluxo de DFe de compras (gestor-recebimento). Pytest cobre os 2 cenários. |
| Fix B-V23-2 acende novos bugs cascateados (taxes, fiscal_position, etc.) | ALTA | MÉDIO | S3 bulk REAL PROD em conjunto pequeno (3-5 ajustes) antes de onda grande. Capturar erros + iterar conforme cascade. |
| `resolver_account_id_por_company` retorna None (account não existe na destino) | MÉDIA | ALTO | Átomo retorna `{'status': 'FALHA', 'erro': 'account_nao_existe_em_destino'}`; caller (orchestrator) decide se aborta linha ou tenta fallback (ex: usar account default da company destino). Logging detalhado. |
| Bulk REAL PROD trava com SEFAZ rejeição em algum ajuste novo (não 176013/14) | MÉDIA | MÉDIO | Pre-flight C5 deve pegar antes. Se passar pre-flight mas rejeitar SEFAZ, recovery captura erro + ajustes individuais ficam em fase intermediária + operador investiga. |
| Sessão estoura tokens | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` para casos reais; principal só implementa refator + revisa. |

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
