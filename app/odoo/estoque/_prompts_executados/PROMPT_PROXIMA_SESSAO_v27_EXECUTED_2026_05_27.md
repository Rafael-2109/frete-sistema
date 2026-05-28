# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v27+ S1 opt-in `--usar-skill8-atomica-v25` no `executar_pipeline_bulk` + S3 rename orchestrator `faturamento_pipeline.py` → `inventario_pipeline.py` + S4 expand CONSTANTS FB+CD + S5 folhas L3 1.1.x/1.3. S0 canary REAL F1-F4 **deferido** (zero candidato natural pós-cleanup F5d_BLOCKER_TX v26+; aguarda próxima INDUSTRIALIZACAO_FB_LF do operador).
**Base**: commits v25+ S0 + v26+ EXECUTED (`ea505c0e` + `fe0fd04a` + `701e4885`) — 4 fixes F1-F4 codificados + 662 pytest verdes + banco local limpo.
**Risco**: MÉDIO (S1 opt-in é dispatch fino; S3 rename exige alias compat com 8 imports; S4 expand requer XML-RPC discovery).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-27 v26+ PARTIAL EXECUTED (sucessor do v25+ S0 + v26+ cleanup F5d).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20,21,22,23,24,25_S0,26_PARTIAL}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N31 + AR1-AR13 + lições memories; atenção especial a **N27-N31 ✅ CODIFICADOS v25+ S0** + **AR13** "caminho novo regrediu hardenings do legacy").
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo — Skill 7 ABRANGENTE v25+ tem 10 átomos + Skill 8 ATÔMICA L2 v24+) + §6.5 (antipadrões — AP6 RESOLVIDO PARCIAL v24+) + §14 (histórico desvios — D-V25-1) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer (nota cleanup F5d v26+ adicionada).
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`app/odoo/estoque/CIRURGIA_AVULSO_FRASCO_2026_05_27.md`** — análise root cause + 5 falhas + 4 fixes F1-F4 ✅ CODIFICADOS v25+ (LEITURA OBRIGATÓRIA se sessão eventualmente rodar canary REAL — deferido).
7. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
8. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
9. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.
10. **`app/odoo/estoque/scripts/faturamento.py`** (v24+) — 5 átomos Skill 8 ATÔMICA L2 (espelha Skill 7 ABRANGENTE v19+).
11. **`.claude/skills/faturando-odoo/SKILL.md`** — fachada atualizada v24+ (5 átomos + contratos + exemplo composição).

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 662 passed (v25+ S0 + v26+ cleanup baseline)
```

Se ≠ 662 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v26+ PARTIAL — FINALIZADA — 4 fixes F1-F4 codificados + cleanup F5d_BLOCKER_TX banco local)

### Estado do código
- **Commits base**: `ea505c0e` (v25+ S0 fixes F1-F4) + `fe0fd04a` (v25+ S0 docs) + `701e4885` (v26+ cleanup F5d banco local).
- **Baseline pytest**: 662 verdes (655 v24.1+ + 7 net v25+ S0).
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura (v25+ S0 + v26+ cleanup)
- **Skill 7 ABRANGENTE LIVE v25+** — `app/odoo/estoque/scripts/escrituracao.py` com **10 átomos**: 7 v19+ + 2 v23+/v23.5+ + **1 v25+ NOVO `alinhar_dfe_lines_company`** (F2a — generaliza B-V23-1 p/ caminho A). `preencher_po` ganhou param opcional `l10n_br_tipo_pedido` (F3c).
- **Skill 8 ATÔMICA L2 LIVE v24+** — `app/odoo/estoque/scripts/faturamento.py` com 5 átomos espelhando Skill 7. Inalterada v25+/v26+.
- **Orchestrator C3 LEGACY `faturamento_pipeline.py`** — ganhou **F1+F2a+F2b+F3a-d+F4** no `executar_fluxo_l3_1_2_x` + `_executar_etapa_f_via_fluxo_l3` + `_resolver_constants_fluxo_l3`. Total ~5200 LOC. Rename → `inventario_pipeline.py` AINDA pendente v27+.
- **Sub-skill C5 estendida v24+** — Inalterada v25+/v26+.

### Estado banco local pós-cleanup v26+
- INDUSTRIALIZACAO_FB_LF F5d_BLOCKER_TX: **0** (era 30, apagado em `701e4885` decisão Rafael)
- INDUSTRIALIZACAO_FB_LF F5e_SEFAZ_OK: 1 (apenas 177465 AVULSO_FRASCO — já idempotente Odoo via cirurgia manual v24+)
- INDUSTRIALIZACAO_FB_LF F5f_ENTRADA_OK: 104 (43 ENCONTRO_CONTAS_PASTA23 + 59 FATURAMENTO_LF + 2 INVENTARIO_2026_05) — concluídos
- INDUSTRIALIZACAO_FB_LF F5f_FALHA: 0
- 67 registros `operacao_odoo_auditoria` correlatos também apagados (soft-link `tabela_origem`+`registro_id`)

### Estado FINAL ajustes 176013/176014 PROD (v23+ — preservado v24+/v25+/v26+)
- id=176013/176014: `status='EXECUTADO', fase_pipeline='F5f_ENTRADA_OK'`
- Picking SAÍDA 321601 (FB/SAI/IND/01602): state=done
- Invoice SAÍDA 716448 RPI/2026/00238: SEFAZ autorizada chave `35260561724241000178550010000945661007164482`
- Invoice ENTRADA 717630 ENTIN/2026/05/0055: posted LF, R$ 12.525,54 untaxed
- PO 42419 C2619591: state=purchase, team=143 RAFAEL, picking 321617 done, invoice 717630
- DFe 43533: criado v22+, lines company=LF (após fix manual v23+)

### Estado FINAL operação AVULSO_2026_05_27_FRASCO PROD (v24+ — preservado v25+/v26+)
- Invoice ENTIN/2026/05/0056 (id=719071): posted journal 1047 ENTIN, R$ 7.796,58
- NF SAÍDA 718364: SEFAZ autorizada chave `35260561724241000178550010000945741007183640`
- PO 42543 (C2602695): purchase, LF, tipo=serv-industrializacao, fp=131, team=143 Rafael (workaround manual cirúrgico)
- Picking 321834 (LF/IN/01780): done, lote AJ-27-05 (correto, do XML SEFAZ)
- LF/Estoque/AJ-27-05 (quant 265199): 37688un

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (8): 1, 2 (4 modos A/B/C/D v21+), 2.4, 4, 5 (7 átomos + G-AUDIT-3 v22+), **7 ABRANGENTE v25+ (10 átomos)**, **8 ATÔMICA v24+ (5 átomos)**, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, `faturamento_pipeline` (pipeline A-F + recovery + opt-in v19+ + **F1-F4 v25+** — rename para `inventario_pipeline` pendente v27+).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo` (V1 'inventario' v14b + G038 v22+ + G007+tipo_produto v24+).
- Fluxos L3 escritos (11): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+.

---

## §3. ESCOPO DESTA SESSÃO (v27+ — S1 opt-in skill8 atômica + S3 rename + S4 expand CONSTANTS + S5 folhas L3)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Migrar orchestrator legacy `faturamento_pipeline.py` para usar Skill 8 ATÔMICA L2 (criada v24+) via opt-in `--usar-skill8-atomica-v25`. Renomear orchestrator. Expand CONSTANTS FB+CD. Escrever folhas L3 1.1.x + 1.3 (Markdown).

**S0 canary REAL F1-F4 DEFERIDO**: pós-cleanup F5d v26+, zero candidato natural no banco. Aguarda próxima INDUSTRIALIZACAO_FB_LF orgânica do operador. Quando surgir: rodar `--usar-fluxo-l3-v19 --confirmar-sefaz` validando que F1-F4 codificados eliminam workarounds manuais (lote correto + dfe.line.company alinhada + G023 force + tipos certo + team=143 fixo).

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S1 — Opt-in `--usar-skill8-atomica-v25` no orchestrator (PRIORITÁRIO v27+)
- Adicionar flag CLI no `executar_pipeline_bulk` (pattern espelhado de `--usar-fluxo-l3-v19`).
- Quando flag=True, ETAPAS C+D delegam à Skill 8 ATÔMICA (via novo método `_executar_etapas_c_d_via_atomos`).
- Default OFF preserva 100% legacy = zero risco regressão.
- Pytest cobrindo dispatch (3-5 testes mockados).

#### S2 — Canary REAL PROD do opt-in skill8 atômica (quando lote natural surgir)
- Selecionar 1-5 ajustes naturais que entrarem em F5e_SEFAZ_OK.
- Rodar `executar_pipeline_bulk --usar-skill8-atomica-v25 --confirmar-sefaz`.
- Validar: paridade com legacy (mesmas chaves SEFAZ, mesmas fase_pipeline finais).
- Junto com S2 valida também S0 v26+ (F1-F4) — canary unificado.

#### S3 — Rename orchestrator + alias compat
- `git mv app/odoo/estoque/orchestrators/faturamento_pipeline.py app/odoo/estoque/orchestrators/inventario_pipeline.py`
- Criar `faturamento_pipeline.py` STUB que re-importa de `inventario_pipeline` (alias compat para 8 imports atuais).
- Atualizar SKILL.md fachada + CLAUDE.md §6 Tabela 3.

#### S4 — Expand CONSTANTS FB+CD
- Discovery XML-RPC `team_id` + `payment_term_id` + `picking_type_id` + `payment_provider_id` para company=1 (FB) e company=4 (CD).
- Mapear `L10N_BR_TIPO_PEDIDO_POR_ACAO` para todas direções via lookup MATRIZ_INTERCOMPANY (manter formato `{'dfe', 'po'}` introduzido v25+ F3a).
- Decisão por destino: STATIC fixo (como F4 fez p/ LF=143) OU G039 dinâmico — Rafael define caso-a-caso.
- Pytest mockado cobrindo 3 direções.

#### S5 — Folhas L3 1.1.x + 1.3
- 1.1.x (só saída) compõe Skill 8 ATÔMICA L2.
- 1.3 (transferência completa) compõe Skill 8 ATÔMICA + Skill 7 ABRANGENTE via 1.2.x.
- Markdown apenas (sem código novo).

#### S6 — Após canary OK (se sobrar tempo)
- Remover ETAPAS C+D legacy do orchestrator (~500 LOC).
- Migrar 14 testes C+D de `test_faturamento_pipeline_orchestrator.py` para `test_faturamento_invoice_service.py`.
- Default flip: `--usar-skill8-atomica-v25=True` (e remover flag em vN+).

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (SUPERADO ao final v22+).
- ❌ S0 canary REAL F1-F4 sem lote natural — aguardar operador disparar INDUSTRIALIZACAO_FB_LF orgânica (alternativa: forçar saída sintética via planilha sai/ENTIN custosa fiscalmente).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (11 documentos incluindo CIRURGIA_AVULSO_FRASCO + PROTECAO N27-N31)
- [ ] Baseline pytest 662 confirmado
- [ ] Cross-check Odoo: estado dos ajustes 176013/14, PO 42419, invoice 717630, PO 42543, invoice 719071 (estados preservados v23+ + v24+)
- [ ] Confirmar banco local: zero INDUSTRIALIZACAO_FB_LF em F5d_BLOCKER_TX (cleanup v26+)
- [ ] Confirmar candidatos canary natural — se surgiram entre sessões, fazer S2 antes de S1
- [ ] AskUserQuestion §1.4 confirmou escopo S1-S6 com Rafael

Implementação:
- [ ] S1 — Opt-in `--usar-skill8-atomica-v25` + helper `_executar_etapas_c_d_via_atomos` + 3-5 pytest dispatch
- [ ] S2 — Canary REAL PROD opt-in (quando lote natural surgir; valida F1-F4 + opt-in juntos)
- [ ] S3 — Rename + alias compat (8 imports atuais preservados)
- [ ] S4 — Expand CONSTANTS FB+CD via discovery XML-RPC + pytest (formato `{'dfe', 'po'}` F3a)
- [ ] S5 — Folhas L3 1.1.x + 1.3 (Markdown)
- [ ] S6 — Se canary skill8 OK: remover ETAPAs C+D legacy + migrar 14 testes

Validação:
- [ ] Pytest baseline ≥ 662 + novos testes (estimativa 5-10 novos)
- [ ] ≥1 code-reviewer paralelo (S1 dispatch + S2 canary)
- [ ] Atualizações cross-refs: SKILL.md fachada + ROADMAP HANDOFF + PROTECAO

Documentação:
- [ ] Atualizar PROTECAO (se houver novo antipadrão — esperado nenhum se S1+S3+S4 limpos)
- [ ] Atualizar CLAUDE.md §6 (catálogo se status mudou) + §14 (D-V27-X se novo desvio)
- [ ] Memórias `[[<slug>-pattern]]` salvas via `mcp__memory__save_memory`
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| S1 opt-in skill8 dispatch tem comportamento divergente vs legacy | ALTA | ALTO | Default OFF preserva legacy; pytest mockado cobre dispatch antes de canary; só ativa em produção via flag explícita. Canary 1 ajuste primeiro + diff manual logs legacy vs opt-in. |
| S2 canary depende de lote natural que pode não surgir nesta sessão | ALTA | MÉDIO | Documentar que S2 fica para sessão N+1 se lote não surgir; S1 fica codificado mas inert (default OFF) sem risco. F1-F4 também ficam validados só por pytest até lote natural. |
| Rename quebra imports externos (8 atuais) | MÉDIA | MÉDIO | Grep `faturamento_pipeline` ANTES; criar alias compat `faturamento_pipeline.py` stub que re-exporta de `inventario_pipeline`. Pytest CI valida imports OK. |
| Discovery XML-RPC FB/CD não encontra IDs corretos (cadastro fiscal não pronto) | MÉDIA | MÉDIO | Documentar pendência por company; adiar entries não disponíveis para sessão v28+; F4 v25+ STATIC=143 p/ LF não bloqueia avanço. |
| Sessão estoura tokens com S1+S3+S4+S5 | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` para S2 canary (quando aplicável); principal só S1+S3+S4+S5 (puro código + markdown). |

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
