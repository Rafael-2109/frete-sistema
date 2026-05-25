# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v14b

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **HEAD apos v14a-ops: `7205a2bb` docs(estoque): v14a-ops — TESTE REAL 6 cods LF→FB PROD + §7.5 (5 dificuldades D-OPS-1..D-OPS-5)**). `main` continua VIVO em paralelo (Rafael commita lá — SPED ECD em progresso) — verificar se avançou e considerar rebase ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git fetch origin main && git log --oneline 7205a2bb..origin/main  # ver se main avancou
```

## 📋 ESTADO ATUAL — apos v14a-ops (TESTE REAL 6 cods PROD VALIDADO)

**Sessao v14a-ops (2026-05-25, 51min)** executou teste real LF→FB de 6 cods em PROD com scripts existentes (NAO Skill 8). Operacao COMPLETA: **3 NFs SEFAZ autorizadas + 1590.9 un consolidadas em FB/Indisp/MIGRAÇÃO**. Descobriu **5 dificuldades reais (D-OPS-1..D-OPS-5)** que Skill 8 v15+ deve eliminar.

**Documento vivo de planejamento** (REGRA INVIOLAVEL 0 — LER INTEIRO ANTES de qualquer modificacao em codigo Skill 8 OU sub-skill OU fix Skill 2):
- `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~1300 LOC, 14 seções + §7.5 NOVA dificuldades operacionais)

**Memorias-chave para esta sessao**:
- `[[teste-real-6-cods-v14a-ops]]` — **LICAO OPERACIONAL** v14a-ops com workarounds aplicados em PROD (LER PRIMEIRO!)
- `[[skill2-distribuir-indisp-pattern]]` — Pattern Skill 2 atual + bug D-OPS-5 documentado

**Checkpoints concluídos**: 4 de 24
- ✅ **C1** — Pre-mortem completo (§7.1)
- ✅ **C2** — Mineracao service `inventario_pipeline_service.py` (§7.2 D1-D9)
- ✅ **C3** — Mineracao script `09_executar_onda1_bulk.py` (§7.3 D10-D18)
- ✅ **C4** — Escopo confirmado: pipeline COMPLETO A-F em N sessoes
- ✅ **Bonus v14a-fix** — Mineracao RecebimentoLfOdooService (§7.4 G-RECLF-1..11, READ-only NAO MEXER)
- ✅ **Bonus v14a-ops** — Teste real 6 cods PROD + 5 dificuldades documentadas (§7.5 D-OPS-1..D-OPS-5)

## 🎯 PRIORIDADES v14b (em ordem)

### PRIORIDADE 1 — Fix bug D-OPS-5 da Skill 2 `transferindo-interno-odoo` (~30-60min)

**Bug**: `app/odoo/estoque/scripts/transfer.py:1145+1147` em `_listar_quants_origem`:
```python
domain.append(['location_id', '!=', loc_indisp])
domain.append(['lot_id', '!=', False])   # <-- BUG: filtra produtos tracking='none'
```

**Sintoma**: para produto `tracking='none'` (saldo sem lot_id), Skill 2 modo C `distribuir_para_indisponivel` retorna `quants_disponiveis=0` → `FALHA_SEM_QUANT`. Caso real validado em v14a-ops: cod 103500105 PIMENTA JALAPENO.

**Fix proposto**:
1. Adicionar parametro `aceita_tracking_none=True` (default) em `_listar_quants_origem`
2. Se `True`, NAO aplicar filtro `['lot_id', '!=', False]`
3. Modo C `transferir_para_indisponivel` precisa detectar quant com `lot_id=False` e:
   - Se produto `tracking='none'`: chamar `ajustar_quant` 2x (zerar origem sem lote + delta+ destino com lote MIGRAÇÃO `lot_svc.criar_se_nao_existe`)
   - Se produto `tracking='lot'` mas quant orfao sem lote: erro claro (anomalia)
4. Helper `distribuir_para_indisponivel` propaga `aceita_tracking_none` para `_listar_quants_origem`

**Pytest novos (>=3)**:
- `test_listar_quants_origem_inclui_tracking_none` (com mock product.tracking='none')
- `test_modo_c_tracking_none_chama_ajustar_quant_2x` (zerar + delta+ destino)
- `test_modo_c_quant_orfao_tracking_lot_levanta_erro`

**Validacao PROD** (canary com cod tracking='none' real):
- Buscar cod tracking='none' com saldo em FB/Estoque (ex: pesquisar `product.tracking='none' AND existe quant em FB/Estoque AND NAO em FB/Indisp`)
- Rodar Skill 2 `distribuir_para_indisponivel --cods <X>=<qty> --empresa FB --dry-run`
- Confirmar resultado vs workaround v14a-ops (2 chamadas Skill 1)
- Commit `feat(estoque): fix Skill 2 D-OPS-5 — aceita tracking='none' em _listar_quants_origem`

### PRIORIDADE 2 — Criar sub-skill `auditando-cadastro-fiscal-odoo` perfil inventário V1 (C5, ~90-120min)

Skill 8 §4 — sub-skill agnostica para pre-flight, **agora COM 2 aprendizados v14a-ops incorporados**:

**NOVO (v14a-ops aprendizado D-OPS-2)**: pre-flight deve verificar **duplicacao em pipeline ativo**:
- Para cada cod_produto da onda, query AjusteEstoqueInventario:
  - Mesmo `cod_produto` + mesmo `company_id` + ciclo qualquer + `status IN ('APROVADO','PROPOSTO','EXECUTADO')` + `fase_pipeline IN ('F5a..F5e_SEFAZ_OK')` → BLOQUEIO (pipeline ativo)
- Reporta cods em pipeline ativo + sugere ação (mover para REPROCESSADO ou aguardar)
- **NAO bloqueia automaticamente** — apenas reporta; operador decide

**NOVO (v14a-ops aprendizado D-OPS-3)**: pre-flight deve flaggar produtos `tracking='none'`:
- Atualmente bug L965 do script 09 + L1145 Skill 2 não tratam tracking='none'
- Pre-flight reporta: "produto X tem tracking='none'; usar workaround `lote_origem='SEMLOTE'` ou aguardar fix Skill 2"
- Apos fix D-OPS-5 (PRIORIDADE 1), essa flag vira INFO (não warning)

**Tarefas concretas** (revisar PLANEJAMENTO §4 + §10.5):
1. AskUserQuestion: incluir G035 (barcode invalido SEFAZ cstat=225) no V1 OU adiar?
2. Criar service `app/odoo/estoque/scripts/cadastro_fiscal_audit.py`:
   - Funcao top-level `auditar_cadastro_inventario(odoo, produto_ids OR ciclo, auto_corrigir_barcode=False) -> dict`
   - Checks: G017 NCM + G018 weight (warn) + tracking='none' flag (info) + duplicacao pipeline (warn) + opcional G035 barcode
   - Dry-run default; --confirmar so para G035 auto-fix
3. SKILL.md + CLI wrapper `.claude/skills/auditando-cadastro-fiscal-odoo/`
4. Cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md raiz + estoque §6)
5. Pytest >=5 verdes
6. Smoke dry-run em onda real
7. Atualizar PLANEJAMENTO §0 + §4 + §7 (C5 ✅) + §12 + ROADMAP HANDOFF v14b
8. Commit `feat(estoque): v14b — Skill auditando-cadastro-fiscal-odoo perfil inventario V1 com aprendizados D-OPS-2/3`

### PRIORIDADE 3 — Decidir tratamento D-OPS-3 (bug L965 script 09) — AskUserQuestion

**Bug**: script 09 L965 `if not q.get('lot_id'): continue` pula quants sem lot_id no FIFO. Para produto tracking='none', gera compensatorio INDUSTRIALIZACAO_FB_LF inverso (sem sentido operacional).

**Opcoes**:
- **(a) NÃO mexer no script** (regra Rafael v14a-ops "use scripts disponíveis apenas"): documentado, futuro Skill 5 atomo `criar_picking_inter_company` (C6.5 v15a) eliminará o bug.
- **(b) Patchar o script** com minimal fix: aceitar quants sem lot_id quando produto.tracking='none'. Pesa risco de quebrar uso atual do script.
- **(c) Workaround padronizado**: helper Python wrapper que cria AjusteEstoqueInventario com `lote_origem='SEMLOTE'` para produtos tracking='none' antes de rodar script 09 (low risk).

Recomendacao: **(a)** — alinha com "scripts existentes" + sub-skill V1 (C5) ja vai flagger tracking='none'; v15a Skill 5 codifica fix permanente.

## ⚠️ PRE-MORTEM v14b (LER §8.1 do PLANEJAMENTO + R3/R6/R13/R15)

| # | Risco | Em v14b |
|---|-------|---------|
| **R3** | Sub-skill perfis múltiplos viola "skills nascem de demanda real" | V1 **INLINE simples**; estrutura de perfis SO' quando 2o perfil real existir |
| **R4** | Pre-flight como sub-skill = 2 comandos + cross-refs + subprocess + risco divergência | Documentar TRADE-OFF no SKILL.md |
| **R13** | Eu (agente) releio PLANEJAMENTO mas IGNORO padrões D1-D18 + D-OPS-1..D-OPS-5 | Checklist no fim de v14b: D-OPS-2 e D-OPS-3 considerados no pre-flight da sub-skill? |
| **R15** | Sub-skill `auditando-cadastro-fiscal-odoo` nunca tem perfil 2 — estrutura overkill | Aceitar V1 minima + simples |
| **NOVO R16 v14a-ops** | Fix Skill 2 D-OPS-5 quebra os 17 pytest existentes de `distribuir_para_indisponivel` | Pytest >=3 NOVOS + rodar baseline `pytest tests/odoo/ -q` antes e apos; canary OBRIGATORIO em 1 cod real tracking='none' |

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituição)
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (procurar "v14a-ops")
3. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO** (regra inviolavel 0):
   - §0 cabeçalho estado
   - §1-§6 visão + escopo + decomposição A-F + pre-flight delegado + SSL/timeout
   - §4 contrato sub-skill `auditando-cadastro-fiscal-odoo`
   - §7.2 D1-D9 + §7.3 D10-D18 + §7.4 G-RECLF-1..11 (preservar)
   - **§7.5 D-OPS-1..D-OPS-5** (CRITICO — aprendizados v14a-ops com mitigações)
   - §8.1 pre-mortem 15 riscos R1-R15
   - §9 pendências + §10 6 decisões resolvidas
   - §12 trilha v13+v14a+v14a-fix+v14a-ops
4. Memory `[[teste-real-6-cods-v14a-ops]]` — workarounds aplicados em PROD
5. Memory `[[skill2-distribuir-indisp-pattern]]` — bug D-OPS-5 documentado
6. **Para PRIORIDADE 1 fix Skill 2**: `app/odoo/estoque/scripts/transfer.py:1104-1180` (`_listar_quants_origem`) + `1224-1450` (`distribuir_para_indisponivel`)
7. **Para PRIORIDADE 2 C5**: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:228-294` (`validar_cadastro_fiscal`) + `app/odoo/utils/gtin_validator.py` (G035)

## 📚 DESCOBERTAS-CHAVE D1-D18 + G-RECLF-1..11 + D-OPS-1..5 (padrões a PRESERVAR)

**D1-D9** (service `inventario_pipeline_service.py` v13): SNAPSHOT antes threads, agrupamento por picking, bug L19/L20/L21 fix F5b, G023 `linhas_esperadas`, SNAPSHOT meta polling longo, sub-etapas F5d.5/.6/.7, HARD_FAIL_CONFIG_ERRORS, idempotência tripla F5e, `db.session.get` re-fetch.

**D10-D18** (script `09_executar_onda1_bulk.py` v14a): `db.engine.dispose()` profilático antes/após C+D, `expire_all() + carregar_ajustes` entre etapas, `--apenas-etapa`/`--ate-etapa`, ETAPA A SEQUENCIAL, `_commit_resilient` MAIS FORTE, ETAPA A DELEGAVEL Skill 2, `sleep 5s` entre chunks B (G022), `ACAO_PARA_CFOP_ENTRADA` 5xxx→1xxx, default `dry_run=True`.

**G-RECLF-1..11** (RecebimentoLfOdooService v14a-fix READ-only): bulk não viável síncrono, FASE 6+7 falha sem derrubar FB, retry/SSL versão MAIS FORTE, Playwright concorrente JÁ MITIGADO, PAYMENT_PROVIDER diferentes, PICKING_TYPE diferentes, idempotência codificada.

**D-OPS-1..5** (NOVO v14a-ops — TESTE REAL): CICLO hardcoded, falta pre-flight duplicação, bug L965 tracking='none' script 09, picking automático pós-RecLF sem MO, bug L1145 mesmo padrão Skill 2.

## CHECKLIST DA SESSÃO v14b

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde 7205a2bb: git fetch origin main && git log --oneline 7205a2bb..origin/main
[ ] Pytest baseline: 393 verdes esperado (rodar `pytest tests/odoo/ -q --tb=no`)
[ ] Ler memory [[teste-real-6-cods-v14a-ops]] + [[skill2-distribuir-indisp-pattern]]
[ ] Ler ROADMAP HANDOFF v14a-ops + PLANEJAMENTO §7.5 INTEIRO
[ ] AskUserQuestion: foco v14b — PRIORIDADE 1 (fix Skill 2) | PRIORIDADE 2 (C5 sub-skill) | ambos
[ ] Se PRIORIDADE 1: ler transfer.py:1104-1450 + planejar fix + pytest >=3 + canary tracking='none'
[ ] Se PRIORIDADE 2: AskUserQuestion sobre G035 + criar service + SKILL.md + CLI + cross-refs + pytest >=5 + smoke
[ ] AskUserQuestion sobre PRIORIDADE 3 (tratamento bug L965 script 09 D-OPS-3)
[ ] Atualizar PLANEJAMENTO §0 + §7 + §12 (trilha v14b) + ROADMAP HANDOFF
[ ] Code-review paralelo (feature-dev:code-reviewer) ao fim
[ ] Commit consolidado por prioridade
[ ] Atualizar este PROMPT_PROXIMA_SESSAO.md para v15a
```

## CRONOGRAMA RESTANTE (estimativa pos-v14a-ops)

| Sessão | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| ~~v14a~~ | ~~C3 mineração script + revalidar R1~~ | ~~C3~~ | ~~Baixo~~ ✅ |
| ~~v14a-fix~~ | ~~RecebimentoLfOdoo §7.4 + ETAPA F atomo Skill 5 + gotchas~~ | ~~4 lacunas~~ | ~~Baixo~~ ✅ |
| ~~v14a-ops~~ | ~~TESTE REAL 6 cods PROD + 5 dificuldades D-OPS-1..5~~ | ~~Bonus operacional~~ | ~~Baixo (com workarounds)~~ ✅ |
| **v14b (esta)** | **PRIORIDADE 1**: fix Skill 2 D-OPS-5 + **PRIORIDADE 2**: C5 sub-skill auditando-cadastro-fiscal-odoo V1 (com aprendizados D-OPS-2/3) | C5 + fix S2 | Médio (mexe Skill 2 madura + cria sub-skill nova) |
| **v15a** | C6.5 estender Skill 5 com **3 átomos** inter-company (`criar_picking_inter_company` + `validar_picking_inter_company` + `criar_picking_entrada_destino_manual`) — INCORPORA fix D-OPS-3 (tracking='none' no atomo novo) | C6.5 | Médio (mexe skill madura) |
| **v15b** | C6+C7+C8 orchestrator base + F5a + F5b (chama átomos novos Skill 5; invoca sub-skill C5; centraliza D17) | C6, C7, C8 | Médio |
| **v16** | C9+C10 F5c + F5d (G016+G007+G034+G029 + D10 dispose + D14 commit_resilient + D11 expire_all) | C9, C10 | Médio (SSL crítico) |
| **v17** | C11+C12+C13 F5e + etapas E/F (G023 + D17 centralizado + D-OPS-2b fix F5e propagação + D-OPS-4 pós-hook ETAPA E) | C11, C12, C13 | Alto (SEFAZ) |
| **v18** | C14+C15+C16+C17 recovery + SKILL.md + tests + smokes | C14-C17 | Médio |
| **v19** | C18+C19+C20 folhas + cross-refs + Canary REAL PROD | C18-C20 | Alto (1ª NF real Skill 8) |
| **v20+** | C21+C22+C23 bulk REAL PROD + code-review + commit final + arquivar 09_* SUPERADOS | C21-C23 | Alto (volume real) |

**Total restante: 8-9 sessões** (v14b → v20+).

## REGRAS INVIOLÁVEIS NOVAS v14a-ops (somar as 50 anteriores)

51. **(v14a-ops) Skill 2 `_listar_quants_origem` L1145+1147 filtra `lot_id != False`** — sintoma `FALHA_SEM_QUANT` para tracking='none'. **PRIORIDADE 1 v14b**: fix com `aceita_tracking_none=True` default + pytest >=3 novos + canary PROD em cod tracking='none' real.
52. **(v14a-ops) Script 09 `09_executar_onda1_bulk.py:965`** tem MESMO bug filtro `lot_id` (PULA quants sem lot_id). **NÃO MEXER no script** (regra Rafael). Workaround: `lote_origem='SEMLOTE'` no AjusteEstoqueInventario força entrada em `ajustes_com_lote` L944. Skill 8 v15+ codifica fix no atomo novo Skill 5 `criar_picking_inter_company`.
53. **(v14a-ops) F5e do service `inventario_pipeline_service.py:1245`** propaga `chave_nfe` para TODOS ajustes do mesmo `invoice_id`, mesmo SEM linha real → falso positivo F5e_SEFAZ_OK em compensatórios. **Fix em v17** (C11): replicar so' para ajustes com linha real (cross-ref `account.move.line.product_id`).
54. **(v14a-ops) Picking automático pós-RecLF** com `origin=False` + `group_id=False` + dst=Estoque Virtual/Produção pode aparecer e reservar saldo recém-recebido sem MO. **Fix em v17** (C12): pós-hook ETAPA E detecta+cancela via heuristica. Workaround manual: Skill 5 modo `cancelar`.
55. **(v14a-ops) `ajuste_estoque_inventario.status` varchar(20)** — limite curto. Migration futura: varchar(40+). Atenção em nomes de status descritivos.
56. **(v14a-ops) Sub-skill C5 deve incluir pre-flight de DUPLICAÇÃO** (D-OPS-2) — query AjusteEstoqueInventario por cod_produto+company+fase pipeline ativa. Aborta com mensagem clara se houver duplicata.
57. **(v14a-ops) Sub-skill C5 deve flaggar tracking='none'** (D-OPS-3) — apos fix Skill 2 D-OPS-5 vira INFO; antes do fix vira WARN ("usar workaround SEMLOTE").

## NÃO-FAZER (red flags v14b)

- ❌ Começar v14b SEM ler memory `[[teste-real-6-cods-v14a-ops]]` + PLANEJAMENTO §7.5
- ❌ Fix Skill 2 D-OPS-5 sem pytest >=3 novos OU sem canary PROD em cod tracking='none' real
- ❌ Patchar script 09 (D-OPS-3) — Rafael disse "use scripts existentes apenas" + Skill 8 v15+ resolve
- ❌ Criar sub-skill com estrutura de perfis múltiplos antes do 2o perfil real existir (R3+R15)
- ❌ Implementar C6.5 (Skill 5 inter-company átomos) em v14b — isso é v15a
- ❌ Implementar orchestrator Skill 8 base em v14b — isso é v15b
- ❌ Esquecer cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md raiz + CLAUDE.md estoque)
- ❌ Pular AskUserQuestion sobre G035 (decisão importante que afeta escopo V1)
- ❌ Quebrar pytest baseline 393 verdes (esperado 396+ após v14b se PRIORIDADE 1 + 398+ se ambas)
- ❌ Esquecer de atualizar §0 + §4 + §7 + §9 + §12 + ROADMAP HANDOFF a CADA commit

---END---
