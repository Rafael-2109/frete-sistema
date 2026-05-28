# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v28+ S2 canary REAL PROD (opt-in `--usar-skill8-atomica-v25` + flags F1-F4 v25+ — quando lote natural surgir) + S6 cleanup ETAPAs C+D legacy (após canary OK) + remoção stub `faturamento_pipeline.py` (após grep zero imports).
**Base**: commits v27+ S1+S3+S4+S5 (`ab35d5f3` + `47085916` + `843045a9` + `b7f32476`) — opt-in skill8 atômica LIVE + rename + expand CONSTANTS FB+CD + folhas L3 1.1.1/1.3 + 672 pytest verdes.
**Risco**: ALTO (S2 canary REAL toca SEFAZ irreversível; S6 remove ~500 LOC legacy só após canary).
**Estimativa**: 1-3 sessões (depende quando lote natural surgir).

> **Criado em**: 2026-05-27 v27+ S1+S3+S4+S5 EXECUTED (sucessor do v27+ que executou §3 inteiro do PROMPT anterior).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20,21,22,23,24,25_S0,26_PARTIAL,27}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

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

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N31 + AR1-AR13 + lições memories; atenção especial a N27-N31 ✅ CODIFICADOS v25+ S0 + AR13 "caminho novo regrediu hardenings do legacy").
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo — Skill 7 ABRANGENTE v25+ tem 10 átomos + Skill 8 ATÔMICA L2 v24+ + orchestrator `inventario_pipeline` v27+ S3) + §6.5 (antipadrões — AP6 RESOLVIDO PARCIAL v24+ + opt-in S1 v27+) + §14 (histórico desvios — D-V25-1) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer (cleanup F5d v26+ + S1+S3+S4+S5 v27+ marcados ✅).
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`app/odoo/estoque/CIRURGIA_AVULSO_FRASCO_2026_05_27.md`** — análise root cause + 5 falhas + 4 fixes F1-F4 ✅ CODIFICADOS v25+ (LEITURA OBRIGATÓRIA se sessão rodar canary REAL).
7. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
8. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
9. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.
10. **`app/odoo/estoque/scripts/faturamento.py`** (v24+) — 5 átomos Skill 8 ATÔMICA L2 (espelha Skill 7 ABRANGENTE v19+).
11. **`.claude/skills/faturando-odoo/SKILL.md`** — fachada atualizada v27+ S3 (paths apontam para inventario_pipeline).
12. **`app/odoo/estoque/fluxos/1.1.1-faturamento-saida-pura.md`** + **`1.3-transferencia-completa.md`** — folhas L3 escritas v27+ S5 (composição via opt-in).

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 672 passed (v27+ S1+S4 baseline)
```

Se ≠ 672 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v27+ — FINALIZADA — S1+S3+S4+S5 EXECUTED)

### Estado do código
- **Commits base**: `ab35d5f3` (S1 opt-in skill8) + `47085916` (S3 rename) + `843045a9` (S4 CONSTANTS) + `b7f32476` (S5 folhas L3).
- **Baseline pytest**: 672 verdes (662 v26+ + 10 net v27+ = 6 S1 + 4 S4).
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura (v27+)

- **Orchestrator C3 LEGACY renomeado v27+ S3**: `app/odoo/estoque/orchestrators/inventario_pipeline.py` (~5600 LOC) + STUB ALIAS COMPAT `faturamento_pipeline.py` (~75 LOC re-exporta tudo + entry-point CLI legacy).
- **Skill 8 ATÔMICA L2 LIVE v24+** (`scripts/faturamento.py` 5 átomos) — inalterada v27+.
- **Skill 7 ABRANGENTE LIVE v25+** (`scripts/escrituracao.py` 10 átomos) — inalterada v27+.
- **Opt-in `--usar-skill8-atomica-v25` LIVE v27+ S1**: helpers `_executar_etapa_c_via_skill8_atomica` + `_executar_etapa_d_via_skill8_atomica` delegam ETAPAs C+D aos átomos 3, 4 e 5 da Skill 8 ATÔMICA. Default OFF preserva legacy.
- **Opt-in `--usar-fluxo-l3-v19` LIVE v20+** mantido (substitui ETAPAs E+F pelo FLUXO L3 1.2.x — caminho A/B).
- **CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO** expandido v27+ S4: cobre 3 companies (FB=1, CD=4, LF=5). FB+CD com `team_id=None` (G039 dinâmico); LF=5 com `team_id=143` STATIC FIXO (F4 v25+).
- **L10N_BR_TIPO_PEDIDO_POR_ACAO** expandido v27+ S4: cobre 8 ações da MATRIZ_INTERCOMPANY (dfe='compra' UNIVERSAL + po derivado).
- **Folhas L3 escritas (13)**: 2.1-2.9, 3.1, 4.1, 1.2.1, 1.2.2, **1.1.1 NOVO v27+ S5** (saída pura via Skill 8 ATÔMICA), **1.3 NOVO v27+ S5** (transferência completa = 1.1.1 + 1.2.x).

### Estado banco local (pós-cleanup v26+ + zero mudança v27+)

- INDUSTRIALIZACAO_FB_LF F5d_BLOCKER_TX: **0** (cleanup v26+ commit `701e4885`)
- INDUSTRIALIZACAO_FB_LF F5e_SEFAZ_OK: 1 (apenas 177465 AVULSO_FRASCO — idempotente Odoo via cirurgia manual v24+)
- INDUSTRIALIZACAO_FB_LF F5f_ENTRADA_OK: 104 (concluídos)
- INDUSTRIALIZACAO_FB_LF F5f_FALHA: 0

### Estado FINAL ajustes PROD (preservado v23+/v24+/v25+/v26+/v27+ — NÃO MEXIDO)

- **176013/176014**: `status='EXECUTADO', fase_pipeline='F5f_ENTRADA_OK'`. Invoice ENTRADA 717630 (ENTIN/2026/05/0055): posted LF R$ 12.525,54. PO 42419 (C2619591): purchase, team=143 RAFAEL, picking 321617 done.
- **177465 (AVULSO_FRASCO)**: `status='EXECUTADO', fase_pipeline='F5e_SEFAZ_OK'`. Invoice ENTRADA 719071 (ENTIN/2026/05/0056): posted LF R$ 7.796,58. PO 42543 (C2602695): purchase, LF, tipo=serv-industrializacao, fp=131, team=143 Rafael. Picking 321834 (LF/IN/01780): done, lote AJ-27-05. LF/Estoque/AJ-27-05: 37688un.

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)

- Skills L2 atômicas (8): 1, 2 (4 modos A/B/C/D v21+), 2.4, 4, 5 (7 átomos + G-AUDIT-3 v22+), **7 ABRANGENTE v25+ (10 átomos)**, **8 ATÔMICA v24+ (5 átomos)**, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, **`inventario_pipeline` v27+ S3** (pipeline A-F + recovery + opt-in v19+ S3 + opt-in v27+ S1) + STUB `faturamento_pipeline.py` (alias compat).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo` (V1 'inventario' v14b + G038 v22+ + G007+tipo_produto v24+).
- Fluxos L3 escritos (13): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+, **1.1.1 v27+ S5**, **1.3 v27+ S5**.

---

## §3. ESCOPO DESTA SESSÃO (v28+ — S7 destravar ETAPA E + S2 canary REAL + S6 cleanup legacy + stub removal)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro

**S7 PRIORITÁRIO (resolução Finding 2 S4 — decisão Rafael 2026-05-27):** implementar `_executar_etapa_e_via_fluxo_l3` espelhando o helper existente de ETAPA F. Destrava 4 ações X→FB (PERDA_LF_FB, TRANSFERIR_CD_FB, DEV_LF_FB, DEV_CD_LF) para usarem o caminho FLUXO L3 1.2.x (buscar DFe / criar manual) quando `--usar-fluxo-l3-v19=True`. Hoje retornam SKIP_NAO_SUPORTADA_V20_FLUXO_L3.

Validar o opt-in `--usar-skill8-atomica-v25` em PROD com 1-5 ajustes naturais (canary REAL); após validar paridade vs legacy, remover ETAPAs C+D legacy do orchestrator + migrar testes. Em paralelo, remover stub `faturamento_pipeline.py` quando seguro (grep zero imports Python ativos).

**Dependência crítica:** lote natural INDUSTRIALIZACAO_FB_LF (ou PERDA_LF_FB / TRANSFERIR_*_CD para canary FB+CD destino). Sem lote, sessão fica em standby — pode rodar S6 (remoção legacy ETAPAs C+D) preventivamente APENAS se Rafael autorizar sem canary (risco alto). **S7 é puro código + pytest — não depende de lote natural, pode rodar primeiro.**

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S7 — Destravar ETAPA E via FLUXO L3 (PRIORITÁRIO — puro código v28+)

**Contexto (decisão Rafael 2026-05-27):** "robô CIEL IT tem mesmo defeito de atraso em QUALQUER tipo — CD→FB também tem que funcionar pelo pattern de pesquisa DFe + criar manual". Hoje `executar_etapa_e` com `usar_fluxo_l3_v19=True` retorna `SKIP_NAO_SUPORTADA_V20_FLUXO_L3` (linha ~3628). Vai destravado em v28+ S7.

- Implementar `_executar_etapa_e_via_fluxo_l3` (espelha `_executar_etapa_f_via_fluxo_l3` linhas ~3402-3563 — mas filtra `ACOES_ENTRADA_FB` em vez de `ACOES_ENTRADA_DESTINO_MANUAL`).
- Modificar `executar_etapa_e`: trocar early return SKIP por dispatch ao helper novo (igual ao pattern de ETAPA F).
- Mapeamento já pronto v27+ S4: CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[1]=FB + L10N_BR_TIPO_PEDIDO_POR_ACAO['PERDA_LF_FB' / 'TRANSFERIR_CD_FB' / 'DEV_LF_FB'] + CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[5]=LF + L10N_BR_TIPO_PEDIDO_POR_ACAO['DEV_CD_LF']. Verificar que `_resolver_constants_fluxo_l3` retorna constants OK para todas 4 ações.
- **Atenção:** `_resolver_constants_fluxo_l3` faz override G039 dinâmico para `company_destino != 5`. FB destino (3 ações) vai exercitar esse caminho na primeira vez — `_resolver_team_g039` precisa estar funcional para Rafael uid=42 na company FB (pode requerer criar purchase.team FB G039 antes do canary).
- **Pytest novos (esperado 4-6):**
  - `test_v28_s7_etapa_e_via_fluxo_l3_lf_destino_dry_run` (DEV_CD_LF → LF=5)
  - `test_v28_s7_etapa_e_via_fluxo_l3_fb_destino_dry_run` (TRANSFERIR_CD_FB → FB=1)
  - `test_v28_s7_etapa_e_via_fluxo_l3_perda_lf_fb_real_run_mockado`
  - `test_v28_s7_etapa_e_via_fluxo_l3_transferir_cd_fb_real_run_mockado`
  - `test_v28_s7_default_off_preserva_etapa_e_legacy`
  - `test_v28_s7_acao_nao_mapeada_retorna_nao_suportada` (defensivo)
- **Não toca:** legacy `executar_etapa_e` (RecebimentoLf via Skill 7 V1 STRICT) preservado para `--usar-fluxo-l3-v19=False` (default OFF).

#### S2 — Canary REAL PROD opt-in skill8 atômica (quando lote surgir)

- Selecionar 1 ajuste natural que entrar em F5c_LIBERADO ou F5d_INVOICE_GERADA.
- Rodar pipeline com **ambas as flags** (valida F1-F4 v25+ + opt-in v25+ S1 juntos):
  ```bash
  python -m app.odoo.estoque.orchestrators.inventario_pipeline \
    --modo resume --apenas-etapa F --usar-fluxo-l3-v19 \
    --usar-skill8-atomica-v25 --confirmar --confirmar-sefaz \
    --ciclo <CICLO_REAL> --pular-pre-flight \
    --limite 1   # canary mínimo
  ```
- Validar paridade vs legacy:
  - Chave SEFAZ válida e única
  - `fase_pipeline='F5e_SEFAZ_OK'` ou `F5f_ENTRADA_OK`
  - Saldo no lote correto (não MIGRAÇÃO)
  - `team=143` (LF) ou G039 dinâmico (FB/CD)
  - `dfe.line.company_id` alinhada com destino
  - Tipos DFe='compra' / PO=`<derivado>`
  - PO criada na company destino correta + picking nativo done

#### S2.b — Canary REAL FB/CD destino (separado — depende de S7 implementado primeiro)

- Quando próxima PERDA_LF_FB / TRANSFERIR_CD_FB / DEV_LF_FB / DEV_CD_LF / TRANSFERIR_FB_CD natural surgir, rodar com `--usar-fluxo-l3-v19 --confirmar --confirmar-sefaz`.
- Valida CONSTANTS v27+ S4 FB+CD (picking_type_id, payment_term_id, team_id=None → G039).
- Para ações X→FB (4 ações), S7 deve estar implementado (ETAPA E via FLUXO L3).
- Após OK: Rafael decide STATIC vs G039 dinâmico p/ FB/CD (espelha decisão F4 LF=143).

#### S6 — Remover ETAPAs C+D legacy (após S2 OK)

- `executar_etapa_c` (linhas 1938-2326 do orchestrator) — remover ~390 LOC.
- `executar_etapa_d` (linhas 2327-2900) — remover ~580 LOC.
- Manter helpers `_executar_etapa_c_via_skill8_atomica` + `_executar_etapa_d_via_skill8_atomica` (renomear para `executar_etapa_c` + `executar_etapa_d` definitivos).
- Flip default: `usar_skill8_atomica_v25=True` por padrão (e remover flag em v29+).
- Migrar 14 testes de `test_faturamento_pipeline_orchestrator.py` (que testam ETAPAs C+D legacy) para `test_faturamento_invoice_service.py` (que testa Skill 8 ATÔMICA direta).
- Pytest baseline esperado: 672 → ~670 (testes legacy migrados sem perda de cobertura).

#### S6.b — Remover stub `faturamento_pipeline.py` (paralelo)

- `grep -rn 'faturamento_pipeline' --include="*.py"` retorna ZERO imports Python ativos.
- Confirmar via pytest passa SEM o stub:
  ```bash
  rm app/odoo/estoque/orchestrators/faturamento_pipeline.py
  timeout 90 python -m pytest tests/odoo/ --tb=line -q
  ```
- Se OK: commit removendo stub + atualizar PROTECAO_PROXIMA_SESSAO.md N32 "stub removido v28+".
- Se FAIL: descobrir caller esquecido, atualizar para `inventario_pipeline`, retentar.

### O que NÃO entra nesta sessão (escopo declarado fora)

- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER N11/N12).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (SUPERADO ao final v22+).
- ❌ S2 canary REAL sem lote natural — aguardar operador (não forçar saída sintética).
- ❌ Folha 1.5 (lançar frete CTe) ou 1.6 (despesa extra) — fora do escopo de inventário.

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (12 documentos incluindo folhas 1.1.1 + 1.3 v27+ S5)
- [ ] Baseline pytest 672 confirmado
- [ ] Cross-check Odoo: estado dos ajustes 176013/14 + 177465 (preservado v23+/v24+/v25+/v26+/v27+)
- [ ] Identificar candidatos canary: query `AjusteEstoqueInventario` em F5c_LIBERADO ou F5d_INVOICE_GERADA recém-criados (filtrar `created_at >= '2026-05-27 18:00'`)
- [ ] AskUserQuestion §1.4 confirmou escopo + ordem prioridade com Rafael

Implementação:
- [ ] **S2** — Canary REAL com opt-in `--usar-skill8-atomica-v25 --usar-fluxo-l3-v19 --confirmar --confirmar-sefaz` (validar paridade vs legacy via comparação de outputs)
- [ ] **S2.b** — Canary REAL FB ou CD destino (se lote surgir)
- [ ] **S6** — Após S2 OK: remover ETAPAs C+D legacy + migrar 14 testes
- [ ] **S6.b** — Remover stub `faturamento_pipeline.py` + atualizar PROTECAO N32

Validação:
- [ ] Pytest baseline ≥ 670 (672 - testes migrados + testes novos)
- [ ] ≥1 code-reviewer paralelo (S2 canary + S6 cleanup) via Task tool
- [ ] Atualizações cross-refs: CLAUDE.md §6 Tabela 1 entry skill 8 + ROADMAP HANDOFF

Documentação:
- [ ] Atualizar PROTECAO se houver novo antipadrão (esperado: nenhum se S2+S6 limpos)
- [ ] Atualizar CLAUDE.md §6 (catálogo se status mudou) + §14 (D-V28-X se novo desvio)
- [ ] Memórias `[[<slug>-pattern]]` salvas via `mcp__memory__save_memory`
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| S2 canary com opt-in skill8 atômica diverge do legacy | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` em background para canary; compara output legacy (executar_etapa_c) vs novo (helper v25+ S1) via log JSON; rollback automático se chave_nfe diferente ou fase_pipeline divergente. |
| Lote natural não surge nesta sessão | ALTA | MÉDIO | S2 fica para sessão N+1 (deferido); S6 NÃO executa sem canary (risco alto remover ~1000 LOC sem validar). S6.b stub pode executar standalone. |
| S6 remoção ETAPAs C+D legacy quebra testes não-migrados | MÉDIA | MÉDIO | Antes de remover: mapear todos os testes que referenciam `executar_etapa_c`/`executar_etapa_d` legacy; migrar mentalmente; rodar pytest após cada migração; rollback se >5% testes quebrarem. |
| S6.b remoção stub quebra import oculto em script ad-hoc | BAIXA | BAIXO | `grep -rn 'faturamento_pipeline'` antes de remover; também incluir `scripts/` ad-hoc. Pytest passa sem stub valida que código de teste OK. |
| Discovery XML-RPC FB/CD canary retorna IDs diferentes de v27+ S4 | BAIXA | MÉDIO | CONSTANTS são CANDIDATE — primeira canary REAL ajusta caso a caso; Rafael confirma valores corretos antes do flip default. |
| Sessão estoura tokens com S2+S6+S6.b | MÉDIA | ALTO | Spawn subagente `gestor-estoque-odoo` para S2 canary (lição v7 ~150k tokens); principal só S6+S6.b (puro código). |

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
