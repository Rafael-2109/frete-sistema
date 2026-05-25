# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v14b

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **HEAD apos v14a-fix: docs(estoque): v14a-fix — RecebimentoLfOdoo mineracao §7.4 + ETAPA F via Skill 5 + gotchas destacados**). `main` continua VIVO em paralelo (Rafael commita lá — SPED ECD em progresso) — verificar se avançou e considerar rebase ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git fetch origin main && git log --oneline f9b875c2..origin/main  # ver se main avancou desde v14a
```

## 📋 ESTADO ATUAL — Skill 8 `faturando-odoo` PLANEJADA + 3 MINERACOES COMPLETAS (apos v14a-fix)

Sessão v14a (2026-05-25) concluiu C3 (mineração `09_executar_onda1_bulk.py` 1866 LOC) + revalidou R1: **decisão 10.3 INTACTA**. Pattern macro **etapa = barreira de sincronização** CONFIRMADO; sub-nuance MICRO ETAPA B (pipeline por picking com sleep 5s G022) documentada.

**v14a-fix (2026-05-25)** — auditoria Rafael identificou 4 lacunas → RESOLVIDAS:
1. **L1 ETAPA F via Skill 5**: 3o átomo NOVO `criar_picking_entrada_destino_manual` (C6.5 expandido — Fluxo>>Skills mantido).
2. **L2 RecebimentoLfOdooService 4562 LOC minerado §7.4 READ-only** — **NÃO MEXER**: 37 etapas em 7 fases (FB DFe→PO→Picking→Invoice→Finalização→Transfer FB→CD→Recebimento CD). 30-60min POR INVOICE. **11 gotchas G-RECLF-1 a G-RECLF-11** documentados. **G-RECLF-9 (Playwright SEFAZ concorrente) JÁ MITIGADO** pelo etapa-barreira.
3. **L3+L4 Gotchas DESTACADOS em §7.3**: G-ETB-COMPENSATORIO (qty_restante>0 cria AjusteEstoqueInventario PROPOSTO para ondas futuras) + G-ETB-G014 (lote vencido on-the-fly via Skill 2).
4. **5 pendências novas §9**: paralelismo ETAPA E (G-RECLF-1 v17), centralizar constantes ETAPA F (bloqueia C6.5 v15a), verificar atomo Skill 2 v1 ou v2 em G014 (v15b).

**Documento vivo de planejamento** (REGRA INVIOLAVEL 0 — LER INTEIRO ANTES de qualquer modificacao em codigo Skill 8 OU sub-skill):
- `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~1100 LOC, 14 seções + pre-mortem §8.1 + §7.3 NOVA mineracao script)

**Checkpoints concluídos após v14a**: 4 de 24
- ✅ **C1** — Pre-mortem completo (§7.1 — 4 dimensões x 6 etapas)
- ✅ **C2** — Mineração detalhada `inventario_pipeline_service.py` (§7.2 — 14 métodos + 9 descobertas-chave **D1-D9**)
- ✅ **C3** — Mineração detalhada `09_executar_onda1_bulk.py` (§7.3 — 11 funções + 9 descobertas-chave **D10-D18**) — v14a
- ✅ **C4** — Escopo confirmado: pipeline COMPLETO A-F em N sessões

**6 decisões RESOLVIDAS** (v13) + **R1 REVALIDADA** (v14a) — sem decisões pendentes para v14b.

## 📚 DESCOBERTAS-CHAVE D1-D18 (padrões a PRESERVAR no orchestrator Skill 8 v15)

**D1-D9** (service `inventario_pipeline_service.py` — v13):
- D1: SNAPSHOT antes de threads (evita DetachedInstanceError)
- D2: agrupamento por picking (1 picking = N ajustes)
- D3: bug L19/L20/L21 fix em F5b (preencher_qty_done ENTRE action_assign e ajustar — sequência inviolável)
- D4: G023 `linhas_esperadas` em F5b validate (consolida MLs pre button_validate)
- D5: SNAPSHOT meta + `db.session.get` re-fetch em polling longo
- D6: sub-etapas F5d.5/.6/.7 em try/except (falha individual não derruba ajuste)
- D7: `HARD_FAIL_CONFIG_ERRORS` aborta batch (playwright/odoo password ausente)
- D8: idempotência TRIPLA em F5e (sem inv_id, batch, persistência)
- D9: `db.session.get` re-fetch + `_commit_with_retry` após Playwright

**D10-D18** (script `09_executar_onda1_bulk.py` — v14a):
- D10: `db.engine.dispose()` PROFILÁTICO antes E após ETAPAS C+D
- D11: `db.session.expire_all() + carregar_ajustes()` entre etapas (re-load DB)
- D12: `--apenas-etapa` + `--ate-etapa` para recovery operacional
- D13: ETAPA A SEQUENCIAL (max_workers legacy — XML-RPC não thread-safe Request-sent)
- D14: `_commit_resilient` (script) MAIS FORTE que `_commit_with_retry` (service) — faz `engine.dispose()` se SSL
- D15: ETAPA A 100% DELEGÁVEL para Skill 2 `transferindo-interno-odoo`
- D16: `time.sleep(5)` entre chunks ETAPA B (G022 over-reservation mitigation)
- D17: `ACAO_PARA_CFOP_ENTRADA` 5xxx→1xxx (PERDA 5903→1903, TRANSFERIR 5152→1152, DEV 5949→1949)
- D18: default `dry_run=True` + `--confirmar` + `--confirmar-sefaz` (2 níveis)

**G-ETB destacados v14a-fix** (ETAPA B script):
- G-ETB-COMPENSATORIO: `qty_restante > 0` em PERDA_LF_FB cria NOVO `AjusteEstoqueInventario(acao='INDUSTRIALIZACAO_FB_LF', status='PROPOSTO')` para ondas futuras (preservar em C7)
- G-ETB-G014: lote vencido on-the-fly via `StockInternalTransferService.transferir_quantidade_para_lote` → lote novo `INV-{cod}-{HOJE}` (preservar em C7; verificar v1 ou v2 — pendência §9)

**G-RECLF-1 a G-RECLF-11** (RecebimentoLfOdooService 4562 LOC — v14a-fix §7.4):
- G-RECLF-1: 30-60min/invoice — bulk não viável síncrono (decidir paralelismo em v17)
- G-RECLF-2: FASE 6+7 pode falhar sem derrubar FB — aceitar `transfer_status='erro'` como sucesso parcial
- G-RECLF-3: idempotência ja' codificada — pre-check `existente AND status='processado'` antes de re-chamar
- G-RECLF-4: `_safe_update`/`_checkpoint` MAIS FORTES que D14 — consolidar com util compartilhada
- G-RECLF-5: `app.utils.database_retry.commit_with_retry` ja existe — Skill 8 deve usar (não re-implementar)
- G-RECLF-6: PAYMENT_PROVIDER_ID 92/30 (RecebimentoLfOdoo) DIFERENTE 38 (Skill 8) — sem conflito (propósitos diferentes)
- G-RECLF-7: PICKING_TYPE 51/13 (RecebimentoLfOdoo) DIFERENTE MATRIZ Skill 8 — sem conflito
- G-RECLF-8: PARTNER_CD_IN_FB=34 (consistente com COMPANY_PARTNER_ID Skill 8) ✓
- G-RECLF-9: Playwright SEFAZ concorrente (step_23 vs F5e) — **JÁ MITIGADO pelo etapa-barreira** ✓
- G-RECLF-10: `processar_transfer_only` exige FB-OK — Rafael pode usar para retry FASE 6+7
- G-RECLF-11: Reset etapa=18 se erro pos-18 (idempotência interna)

## ⚠️ PRE-MORTEM — Riscos CRÍTICOS para v14b (LER §8.1 INTEIRO)

| # | Risco | O que fazer em v14b |
|---|-------|---------------------|
| **R3** | Sub-skill perfis múltiplos viola "skills nascem de demanda real" | **V1 INLINE simples; estrutura de perfis SO' quando 2o perfil chegar (NÃO especulativo)** |
| **R4** | Pre-flight como sub-skill = 2 comandos + cross-refs + subprocess + risco divergência | **Documentar TRADE-OFF no SKILL.md: "ganha reuso futuro; perde simplicidade atual"** |
| **R13** | Eu (agente) releio PLANEJAMENTO mas IGNORO padrões D1-D18 | **Checklist no fim de v14b: D17 (ACAO_PARA_CFOP_ENTRADA) NÃO impacta C5 mas D11+D14 podem se sub-skill chamar Odoo via XML-RPC** |
| **R15** | Sub-skill `auditando-cadastro-fiscal-odoo` nunca tem perfil 2 — estrutura overkill | **Aceitar V1 mínima + simples; expandir perfis SO' com demanda real** |

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituição)
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (procurar "v14a")
3. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO** (regra inviolável 0):
   - §0 cabeçalho estado
   - §1-§6 visão + escopo + decomposição A-F + pre-flight delegado + SSL/timeout + pattern reuso
   - **§4 SUB-SKILL `auditando-cadastro-fiscal-odoo`** (CRÍTICO — contrato V0 + perfis + validações + integração)
   - §7.2 D1-D9 + §7.3 D10-D18 (padrões a preservar)
   - §8.1 pre-mortem 15 riscos R1-R15
   - §9 pendências (RESOLVIDAS v14a + NOVAS para v14b)
   - §10 6 decisões RESOLVIDAS
   - §11 cronograma + §12 trilha v13+v14a
4. `.claude/agents/gestor-estoque-odoo.md` (subagente — invariantes existentes + arvore L4)
5. **Para C5**: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:228-294` (`validar_cadastro_fiscal` — fonte LOCALIZADA em v14a) + L297-413 (`corrigir_weight_zero` + `aplicar_peso_volumes_fallback_picking` — G018 v2)
6. Skills LIVES analogas para pattern: `.claude/skills/consultando-quant-odoo/SKILL.md` (READ ancillary atual — modelo para nova READ ancillary)

## FOCO da Sessão v14b — RECOMENDAÇÃO

**FOCO ÚNICO: C5 — Criar sub-skill `auditando-cadastro-fiscal-odoo` perfil inventário V1**

**Objetivo**: criar sub-skill agnóstica (com 1 perfil V1) que Skill 8 invocará no `--bulk`/`--canary` para validar cadastro fiscal ANTES de criar pickings. Aplicar R3 (V1 INLINE simples, sem estrutura de perfis múltiplos especulativa).

**Tarefas concretas (~6 passos)**:

### 1. Verificar baseline + atualizar §0 + ASKUSERQUESTION sobre G035

- Pytest baseline: `pytest tests/odoo/ -q --tb=no` → esperado 393 verdes
- **AskUserQuestion para Rafael** (decisão pendente v14b):
  - G035 (barcode inválido em `product.barcode`) entra no V1 da sub-skill OU adia?
  - Razão: G035 NÃO está no script `09_executar_onda1_bulk.py` minerado v14a (`validar_cadastro_fiscal` cobre só G017+G018). G035 mencionado em §4.3 do PLANEJAMENTO mas sem fonte localizada.
  - Opções: (a) V1 cobre G017+G018 só (alinha com script — minimo); (b) V1 cobre G017+G018+G035 (preenche §4.3 mas precisa descobrir lógica G035); (c) buscar `gtin_validator.py` no repo via grep antes de decidir
- Atualizar §0 (sessão v14b in_progress) + criar §12 entrada "Sessão v14b"

### 2. Criar service base `app/odoo/estoque/scripts/cadastro_fiscal_audit.py`

- Pattern: extrair lógica de `09_executar_onda1_bulk.py:228-294` (`validar_cadastro_fiscal`) — copiar literal + adaptar para retornar dict estruturado em vez de raise
- Função top-level (V1 INLINE, sem estrutura de perfis):
  ```python
  def auditar_cadastro_inventario(
      odoo, produto_ids: list[int],
      auto_corrigir_barcode: bool = False,  # G035 opcional (se decisão acima incluir)
      dry_run: bool = True,
  ) -> dict:
      """Audita G017 NCM + G018 weight (+ G035 barcode se incluir).

      Returns:
          {
              'status_global': 'PRE_FLIGHT_OK' | 'PRE_FLIGHT_BLOQUEADO',
              'pode_faturar': bool,
              'bloqueios': {
                  'ncm_faltando': [{'cod': X, 'nome': Y}],
                  'weight_zero': [...],  # G018 warning so'
                  'barcode_invalido': [...],  # G035 se incluir
              },
              'acoes_aplicadas': [...],  # se --auto-corrigir-barcode
              'relatorio_path': '/tmp/audit_cadastro_*.json',
          }
      """
  ```
- **CRÍTICO**: NÃO usar estrutura de perfis (R3+R15). Adicionar perfis SÓ quando 2o perfil real existir.
- Defaults seguros: `dry_run=True`, `auto_corrigir_barcode=False`
- Modo `--confirmar` aplica APENAS G035 auto-correção (se incluído); G017+G018 são READ-only
- Aplicar D14: usar versão MAIS FORTE de commit (chama `db.engine.dispose()` se SSL) ou pelo menos defensivo se vai escrever em product.barcode

### 3. Criar SKILL.md + CLI wrapper

- `.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md`:
  - Frontmatter description rica (triga em "audita cadastro fiscal", "pre-flight inventario", "validar NCM produtos", "barcode invalido SEFAZ")
  - Contrato (objeto + input + output + pré/pós-condições + gotchas G017/G018/G035)
  - 5+ receitas (auditar produtos por IDs, auditar onda inteira, auto-corrigir G035, integração com Skill 8 via subprocess, smoke dry-run)
  - Trade-offs documentados (R4): "ganha reuso futuro; perde simplicidade atual"
- `.claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro.py`:
  - Args: `--produto-ids LISTA` OU `--ciclo NOME` (le AjusteEstoqueInventario do ciclo)
  - `--auto-corrigir-barcode` (default False, exige `--confirmar` E `--limite N`)
  - `--dry-run` default (D18 pattern)
  - Exit codes: 0 (PRE_FLIGHT_OK) / 1 (PRE_FLIGHT_BLOQUEADO) / 2 (uso) / 4 (DRY_RUN_OK)
  - Output JSON estruturado no fim do stdout

### 4. Pytest >5 verdes em `tests/odoo/services/test_cadastro_fiscal_audit_service.py`

- Mock `odoo.read('product.product', ...)`:
  - test_audit_ok_todos_validos
  - test_audit_g017_ncm_faltando_marca_bloqueio
  - test_audit_g018_weight_zero_marca_warning_nao_bloqueia
  - test_audit_g035_barcode_invalido (se incluir)
  - test_auto_corrigir_barcode_dry_run_nao_escreve
  - test_auto_corrigir_barcode_confirmar_escreve
  - test_produto_ids_vazio_retorna_status_ok
- Baseline esperado: 393 → 398+ verdes

### 5. Smoke dry-run em onda real (sem write)

- Rodar CLI sobre `INVENTARIO_2026_05` ciclo (ou subset) — `--dry-run` puro
- Salvar log JSON em `/tmp/log_skill_auditando_v14b_smoke.json`
- Verificar saída: produtos com G017/G018 faltantes corretamente listados
- **NÃO usar `--confirmar`** nesta sessão (esperar canary C20 com Rafael)

### 6. Cross-refs + atualizar §0 + §4 + §7 (C5 ✅) + §12 + ROADMAP HANDOFF v14b + commit

- Cross-refs:
  - `.claude/agents/gestor-estoque-odoo.md` — adicionar `auditando-cadastro-fiscal-odoo` em `skills:` (lista)
  - `.claude/references/ROUTING_SKILLS.md` — incluir nova skill (47→48 invocáveis; +1 Skills Odoo READ)
  - `tool_skill_mapper.py` — mapear `'auditando-cadastro-fiscal-odoo': 'Estoque Odoo (Audit READ)'`
  - `CLAUDE.md` raiz — Skills WRITE + Skills READ (auditando entra READ)
  - `app/odoo/estoque/CLAUDE.md` §6 catálogo — READ ancillary passa de 1 (`consultando-quant-odoo`) para 2 (+ `auditando-cadastro-fiscal-odoo`)
- §0 (status global atualizado: C5 ✅, 5 de 24)
- §4 (sub-skill V1 IMPLEMENTADA — atualizar status "Item / Quando / Status")
- §7 tabela (C5 marcado ✅ com referência arquivos criados)
- §9 (pendências resolvidas)
- §12 (trilha v14b)
- ROADMAP_SKILLS HANDOFF v14b (nova entrada)
- Commit consolidado: `feat(estoque): v14b — Skill auditando-cadastro-fiscal-odoo perfil inventario V1`

**Tempo estimado**: ~90-120min, ~150k tokens.

## REGRAS INVIOLÁVEIS NOVAS v14a (somar as 41 anteriores)

42. **(v14a) 9 descobertas D10-D18** do §7.3 são padrões a PRESERVAR no orchestrator Skill 8 v15. D10/D11/D14 são CRÍTICAS para SSL/timeout; D17 deve ser CENTRALIZADO em `app/odoo/constants/operacoes_fiscais.py` antes do orchestrator v15b.
43. **(v14a) Pattern macro etapa = barreira CONFIRMADO**; sub-nuance MICRO ETAPA B (pipeline por picking sleep 5s G022) preservada. v15 orchestrator deve respeitar AMBOS.
44. **(v14a) `validar_cadastro_fiscal` LOCALIZADO em script L228-294** — `gtin_validator.py` separado NÃO necessário para G017/G018 V1. G035 ainda em investigação (decidir em v14b).
45. **(v14a) Constantes inline a CENTRALIZAR**: `ACAO_PARA_CFOP_ENTRADA`, `ACOES_ENTRADA_FB`, `ACOES_ENTRADA_DESTINO_MANUAL`, `PICKING_TYPE_ENTRADA_DESTINO_MANUAL`, `COMPANY_LABEL_ENTRADA`, `LOCATION_ORIGEM_ENTRADA_INDUSTR` — antes ou durante v15b/v17.
46. **(v14a-fix) NÃO MEXER em `RecebimentoLfOdooService`** (4562 LOC validados em PROD) — Skill 8 INVOCA `processar_recebimento(rec_id)` na ETAPA E como entry-point publico. Aceita `transfer_status='erro'` como sucesso parcial (FASE 6+7 podem falhar sem derrubar FB).
47. **(v14a-fix) ETAPA F NUNCA implementa picking inline** — sempre via Skill 5 atomo `criar_picking_entrada_destino_manual` (C6.5 expandido v15a). Encapsula G011 lot_name + G023 company_id forcado + G019/G020 state check + idempotencia via origin.
48. **(v14a-fix) Consolidar `_commit_resilient`/`_commit_with_retry`/`_safe_update`/`_checkpoint`** em util compartilhada — usar `app.utils.database_retry.commit_with_retry` ja existente OU criar `app/odoo/estoque/scripts/_commit_helpers.py` (v15b ou v16).
49. **(v14a-fix) Centralizar constantes ETAPA F ANTES de C6.5 v15a** (`ACOES_ENTRADA_DESTINO_MANUAL`, `PICKING_TYPE_ENTRADA_DESTINO_MANUAL`, `COMPANY_LABEL_ENTRADA`, `LOCATION_ORIGEM_ENTRADA_INDUSTR`) — o novo atomo Skill 5 PRECISA destas constantes; centralizar em `app/odoo/constants/operacoes_fiscais.py` (mesmo arquivo MATRIZ_INTERCOMPANY) bloqueia C6.5 se não feito.
50. **(v14a-fix) Decisão paralelismo ETAPA E pendente para v17** (G-RECLF-1) — 30-60min POR INVOICE; bulk 100 invoices = 50-100h síncrono. OPCAO A: assíncrono via RQ worker; OPCAO B: paralelo invoice_ids distintos (verificar thread-safety RecebimentoLfOdoo); OPCAO C: sequencial + recovery `--apenas-etapa=E --resume`. AskUserQuestion em v17.

## NÃO-FAZER (red flags v14b)

- ❌ Começar v14b SEM ler PLANEJAMENTO §4 (sub-skill contrato V0) + §7.3 D10-D18
- ❌ Criar sub-skill com estrutura de perfis múltiplos antes do 2o perfil real existir (R3+R15)
- ❌ Modificar `validar_cadastro_fiscal` no script original — apenas EXTRAIR/REPLICAR no service novo
- ❌ Implementar C6.5 (Skill 5 inter-company atomos) em v14b — isso é v15a
- ❌ Implementar orchestrator Skill 8 base em v14b — isso é v15b
- ❌ Esquecer cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md raiz + CLAUDE.md estoque)
- ❌ Pular AskUserQuestion sobre G035 (decisão importante que afeta escopo V1)
- ❌ Quebrar pytest baseline 393 verdes (esperado 398+ após v14b)
- ❌ Esquecer de atualizar §0 + §4 + §7 + §9 + §12 + ROADMAP HANDOFF a CADA commit

## CHECKLIST DA SESSÃO v14b

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar se main avancou desde f9b875c2: git fetch origin main && git log --oneline f9b875c2..origin/main
[ ] Pytest baseline: 393 verdes esperado (rodar `pytest tests/odoo/ -q --tb=no`)
[ ] Ler ROADMAP HANDOFF v14a + PLANEJAMENTO_SKILL8 INTEIRO (especial §4 sub-skill + §7.3 D10-D18 + §9 pendencias v14b)
[ ] AskUserQuestion: G035 incluir no V1 OU adiar?
[ ] Criar service `cadastro_fiscal_audit.py` (extrair de script L228-294)
[ ] Criar SKILL.md + CLI wrapper
[ ] Criar pytest >5 verdes (target 398+)
[ ] Smoke dry-run em onda real (sem --confirmar)
[ ] Cross-refs: subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md raiz + CLAUDE.md estoque §6
[ ] Atualizar PLANEJAMENTO: §0 + §4 + §7 (C5 ✅) + §9 + §12 (trilha v14b)
[ ] Atualizar ROADMAP HANDOFF v14b
[ ] Code-review paralelo (feature-dev:code-reviewer) ao fim
[ ] Commit consolidado `feat(estoque): v14b — Skill auditando-cadastro-fiscal-odoo perfil inventario V1`
[ ] Atualizar este PROMPT_PROXIMA_SESSAO.md para v15a (Skill 5 inter-company atomos)
```

## CRONOGRAMA RESTANTE (estimativa pos-v14a)

| Sessão | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| ~~v14a~~ | ~~C3 mineração script + revalidar R1~~ | ~~C3~~ | ~~Baixo~~ ✅ |
| ~~v14a-fix~~ | ~~RecebimentoLfOdoo §7.4 + ETAPA F atomo Skill 5 + gotchas destacados~~ | ~~4 lacunas RESOLVIDAS~~ | ~~Baixo~~ ✅ |
| **v14b (esta)** | C5 sub-skill auditando-cadastro-fiscal-odoo perfil inventário V1 | C5 | Baixo-Médio |
| **v15a** | **Centralizar constantes ETAPA F (pre-req)** + C6.5 estender Skill 5 com **3 átomos** inter-company (`criar_picking_inter_company` + `validar_picking_inter_company` + **NOVO `criar_picking_entrada_destino_manual`** v14a-fix) | C6.5 (expandido) | Médio (mexe skill madura — pytest >8 verdes + canary obrigatório em 2 pickings: 1 inter-company + 1 entrada destino manual) |
| **v15b** | C6+C7+C8 orchestrator base + F5a + F5b (chama átomos novos Skill 5; invoca sub-skill C5 no bulk; centraliza D17 ACAO_PARA_CFOP_ENTRADA) | C6, C7, C8 | Médio |
| **v16** | C9+C10 F5c + F5d (G016+G007+G034+G029 + D10 dispose profilático + D14 commit_resilient forte + D11 expire_all entre etapas) | C9, C10 | Médio (SSL crítico) |
| **v17** | C11+C12+C13 F5e + etapas E/F (G023 company_id forçado + D17 centralizado finalizado) | C11, C12, C13 | Alto (SEFAZ + G023) |
| **v18** | C14+C15+C16+C17 recovery (`--resume`, `--apenas-etapa` D12) + SKILL.md + tests + smokes | C14-C17 | Médio |
| **v19** | C18+C19+C20 folhas + cross-refs + CANARY REAL PROD (1 ajuste) | C18-C20 | Alto (PRIMEIRA NF real) |
| **v20+** | C21+C22+C23 bulk REAL PROD + code-review + commit final + arquivar 09_* SUPERADOS | C21-C23 | Alto (volume real) |

**Total restante: 8-9 sessões** (sub-skill C5 em v14b; resto conforme plano v13 + ajustes).

---END---
