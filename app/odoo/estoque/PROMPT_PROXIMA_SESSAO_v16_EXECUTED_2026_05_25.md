# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v16

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`). `main` continua VIVO em paralelo (Rafael commita lá — SPED ECD em progresso). Verificar se avançou e considerar rebase ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git fetch origin main && git log --oneline HEAD..origin/main  # ver se main avancou
```

## 📋 ESTADO ATUAL — apos v15c (ORCHESTRATOR PROD-GRADE + 15 HARDENING FIXES)

**Sessao v15c (2026-05-25)** entregou em 1 sessao:

1. **Pre-mortem + 4 code-reviewers PARALELOS** com focos distintos (~9min cada):
   - Conformidade Arquitetural — PLANEJAMENTO blueprint + Skill 6 v9 pattern
   - Aproveitamento de Recursos — atomos/constants/helpers existentes vs duplicacao
   - Fluxos + Gotchas — G014/G016/G018/G019/G020/G022/G023/G-ETB-*
   - Robustez Operacional — R-OPS-1..10 cenarios PROD com `--confirmar` real

2. **20 findings consolidados** (4 CRITICAL + 12 HIGH + 4 MEDIUM); aplicados 15/20:
   - **F1 (CRIT 95)**: idempotencia F5a via `origin` no atomo `criar_picking_inter_company` (Reviewer D R-OPS-1). Pattern espelha `criar_picking_entrada_destino_manual` v15a. Anti-duplicacao SEFAZ: sem isso, SSL drop apos create + commit local falha permitia re-run criar DUPLICATA -> 2 invoices CIEL IT -> 2 NFs SEFAZ irreversiveis (catastrofe fiscal). Novo status return: `CRIADO | IDEMPOTENT_DONE | IDEMPOTENT_OTHER`. Orchestrator pula F5b/F5c se `IDEMPOTENT_DONE`.
   - **F2 (CRIT 82)**: orchestrator aborta chunk se `_commit_resilient` retorna `False` apos F5a OK. Anti-cascata.
   - **F3 (CRIT 95)**: G014 lote vencido on-the-fly — docstring warning + flag `ajustes_lote_potencialmente_vencido` no output. Implementacao completa TODO v16.
   - **F4 (CRIT 95)**: D11 barreira MACRO explicita em `executar_pipeline_bulk` — `db.session.expire_all()` entre etapas (era implicito por sorte; blueprint exige explicito).
   - **F5 (HIGH 88)**: ETAPA A `raise NotImplementedError` em real-run sem `permitir_etapa_a_noop_real=True` explicito. Anti-armadilha em PROD.
   - **F6 (HIGH 85)**: `safe_session_get` helper anti-DetachedInstanceError apos `_commit_resilient` que faz `session.close()`.
   - **F7 (HIGH 90)**: `db.engine.dispose()` profilatico ANTES e APOS ETAPAS C/D no macro loop (ativo em v15c stubs; armadilha v16/v17 fechada).
   - **F8 (HIGH 95)**: `ACAO_PARA_DIRECAO` + `ACAO_PARA_CFOP_ENTRADA` + `ACOES_ENTRADA_FB` consolidadas em `app/odoo/constants/operacoes_fiscais.py`. Anti-duplicacao entre orchestrator e service legado.
   - **F9 (HIGH 85)**: `app/odoo/estoque/scripts/_commit_helpers.py` NOVO com `commit_resilient` + `safe_session_get` consolidados. SSL match tightened: lista especifica `['ssl', 'decryption', 'bad record', 'closed unexpectedly']` em vez de BROAD `'connection'` (que capturava falso-positivos benignos).
   - **F10 (HIGH 90)**: 4 constantes ETAPA F importadas + ref stub `executar_etapa_f` (guia implementer v17).
   - **F11 (HIGH 85)**: `PAYMENT_PROVIDER_SEM_PAGAMENTO` importado + ref stub C (guia implementer v16).
   - **F12 (HIGH 82)**: `AjusteEstoqueInventario.external_id_operacao` populado em F5a/F5b/F5c. Rastreabilidade auditoria<->registro pai restaurada.
   - **F14 (HIGH 85)**: contadores estruturados (proxy Skill 6 v9). Facilita observabilidade em bulk + suporte futuro `--resume` v18.
   - **F15 (HIGH 82)**: status `EXECUTADO_AUTO_CORRIGIDO` distinction quando compensatorio resolveu pendencia E zero falhas.
   - **F16 (MED 80)**: Semaphore=5 intra-picking analise. Atomo Skill 5 NAO tem Semaphore (sequencial puro). TODO v16 se performance bulk exigir.

3. **NAO APLICADOS (deferidos para v16+)**:
   - **F13** G-ETB-COMPENSATORIO acao_decidida: decisao Rafael — MANTER CR-H2 v15b (preservar `acao_decidida` origem).
   - **B6** `sanitize_for_json` em payloads auditoria com `Decimal`: TODO v16.
   - **B7** PRE-FLIGHT C5 injecao dependencia: TODO testabilidade futura.
   - **R-OPS-8** `--limite N` semantica ambigua: TODO doc clarity.

4. **Pytest**: 465 → **472 verdes em 15.27s** (+7 novos):
   - 3 idempotencia F1 em `test_stock_picking_service.py` (origin obrigatorio, IDEMPOTENT_DONE skip, IDEMPOTENT_OTHER preserve state)
   - 4 em `test_faturamento_pipeline_orchestrator.py` (ETAPA A raise sem flag, ETAPA A real com flag, AUTO_CORRIGIDO status, F5a IDEMPOTENT_DONE pula F5b/F5c)

5. **Smoke dry-run PROD re-validado** em cod 210639522 (INDUSTRIALIZACAO_FB_LF, status=PROPOSTO):
   - `python -m app.odoo.estoque.orchestrators.faturamento_pipeline --ciclo INVENTARIO_2026_05 --etapas A,B --cod-produto 210639522 --limite 1 --pular-pre-flight`
   - `status=DRY_RUN_OK em 2119ms`
   - `grupos_direcao={"INDUSTRIALIZACAO_FB_LF": 1}` (CR-C2 v15b confirmado)

6. **VEREDICTO Reviewer D pos-v15c**: **MIN seguranca SEFAZ alcancado** para uso PROD com `--confirmar` em 1 ajuste real. F1+F2 atomicos garantem zero risco de NF duplicada em re-execucao apos SSL drop. v15c agora e' seguro para canary.

**Baseline pytest**: **472 verdes em 15.27s** (435 baseline v15a + 30 v15b orchestrator + 7 v15c hardening).

**Documento vivo MACRO (regra inviolavel 0 — LER ANTES DE TOCAR Skill 8)**:
`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~1500+ LOC, 14 secoes + trilha v15c detalhada §12)

**Memorias-chave** (LER PRIMEIRO antes de v16):
- `[[skill5_picking_pattern]]` — pattern Skill 5 v3 + v15a (3 atomos) + **v15c F1 idempotencia origin**
- `[[skill6_planejar_pre_etapa_pattern]]` — pattern orchestrator C3 v9 (template reusado v15b/c)
- `[[sub-skill-c5-pattern]]` — pattern sub-skill C5 V1 'inventario' (v14b — invocada via subprocess)
- `[[teste-real-6-cods-v14a-ops]]` — origem operacional D-OPS-1..5

**Checkpoints concluidos: 9 de 24**
✅ C1 pre-mortem | ✅ C2 minera service | ✅ C3 minera script | ✅ C4 escopo confirmado
✅ C5 sub-skill auditando-cadastro-fiscal-odoo V1 (v14b)
✅ C6.5 Skill 5 estendida com 3 atomos inter-company (v15a)
✅ C6 orchestrator base esqueleto (v15b)
✅ C7 ETAPA B F5a criar pickings (v15b/c — F1 idempotencia)
✅ C8 ETAPA B F5b validar pickings (v15b)
✅ C9 ETAPA B F5c liberar faturamento (v15b — escopo expandido)

**Arquivos NOVOS criados em v15c**:
- `app/odoo/estoque/scripts/_commit_helpers.py` (~158 LOC — F9 consolidado)

**Arquivos modificados em v15c**:
- `app/odoo/estoque/scripts/picking.py` (F1 atomo idempotencia)
- `app/odoo/constants/operacoes_fiscais.py` (F8 consolidacao)
- `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (F2-F7+F10-F15)
- `tests/odoo/services/test_stock_picking_service.py` (3 testes F1)
- `tests/odoo/services/test_faturamento_pipeline_orchestrator.py` (4 testes F5/F15)
- `app/odoo/estoque/CLAUDE.md` (status v15c)
- `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (§0 + §12 trilha v15c)

## 🎯 PRIORIDADE v16 — ETAPA C F5d aguardar invoices + ETAPA A real-run

**Objetivo** (~200-250min): implementar ETAPA C (sub-etapas F5d.5/.6/.7) no orchestrator + integrar Skill 2 real em ETAPA A (CR-H3 v15b TODO) + completar G014 lote vencido on-the-fly (CR-F3 v15c TODO).

### Sub-objetivo C10: ETAPA C F5d aguardar invoices CIEL IT

Implementar `_executar_etapa_c` substituindo stub `NOT_IMPLEMENTED_v15b`:

1. Carrega ajustes com `fase_pipeline='F5c_LIBERADO'` (CR-C1 status filter ja aplicado)
2. Agrupa por `picking_id_odoo` (1 picking gera 1 invoice via robo CIEL IT)
3. **Polling longo** (default 1800s, intervalo 40s):
   - SNAPSHOT meta antes (D5 — anti-DetachedInstanceError)
   - Loop: `odoo.search_read('account.move', [['invoice_origin', '=', picking.name]], ...)`
   - Para cada invoice criada: `safe_session_get(AjusteEstoqueInventario, meta['id'])` re-fetch (D9 + F6 v15c)
4. **Sub-etapas defensivas** (D6 — falha individual NAO derruba):
   - **F5d.5** `_garantir_payment_provider` (G029): set `payment_provider_id=38` (SEM PAGAMENTO) se vazio
   - **F5d.6** `_corrigir_price_zero_em_invoice` (G007): fallback `standard_price` ou 0.01 em `account.move.line`
   - **F5d.7** `_garantir_fiscal_setup` (G034 DEV_*): forca `fiscal_position` + `l10n_br_tipo_pedido` correto para DEV_LF_FB/DEV_LF_CD/DEV_CD_LF via reset_to_draft + write + post
5. Atualiza `fase_pipeline='F5d_INVOICE_GERADA'` + `invoice_id_odoo` em cada ajuste
6. **D10 ja codificado no macro** (F7 v15c — `db.engine.dispose()` antes/apos C)
7. Auditoria via `_registrar_auditoria` + `external_id_operacao` em cada ajuste (F12 v15c pattern)

### Sub-objetivo C10.1: Helpers F5d.5/.6/.7 (EXTRAIR do service legado)

Capinar do `inventario_pipeline_service.py` (NAO copiar — extrair pattern):
- `_garantir_payment_provider` (L204-291 service legado) — G029 idempotente; fallback se write em posted falhar. Usa constante `PAYMENT_PROVIDER_SEM_PAGAMENTO` ja importada v15c F11.
- `_garantir_fiscal_setup` (L293-399) — G034 reset_to_draft+post fallback; guard pre-state autorizado. Reutiliza `FISCAL_SETUP_POR_ACAO` dict (3 acoes DEV mapeadas).
- `_corrigir_price_zero_em_invoice` (L401-506) — G007 fallback standard_price ou 0.01.

Localizacao: helpers podem ficar inline na classe `FaturamentoPipelineExecutor` OU em `app/odoo/estoque/scripts/_invoice_helpers.py` se outros orchestrators forem precisar. **Decisao v16: AskUserQuestion** ao iniciar.

### Sub-objetivo C10.2: ETAPA A real-run com Skill 2 integration (CR-H3 v15b TODO)

Substituir comportamento NOOP guard atual (raise NotImplementedError em real-run sem flag) por implementacao real:

1. Carrega ajustes com `fase_pipeline=[None, 'TRANSF_PENDENTE']` (filtro v15c).
2. Para cada ajuste:
   - READ `stock.quant` do produto+company no Odoo (resolver lote atual)
   - Se `lote_origem` do ajuste != `lote` do quant -> invocar `StockInternalTransferService.transferir_quantidade_para_lote_v2` (Skill 2 v2 com `delta_esperado` propagado)
   - Se `lote_origem` == lote atual -> marcar `fase_pipeline='TRANSF_OK'` direto (sem operacao real)
3. Auditoria + `external_id_operacao`.
4. Deprecate `permitir_etapa_a_noop_real` flag (manter por compat ate v17).

### Sub-objetivo C10.3: G014 lote vencido on-the-fly (CR-F3 v15c TODO)

Codificar no `_processar_chunk_etapa_b` ANTES de invocar `criar_picking_inter_company`:

1. READ `stock.lot` para todos os `lote_origem` distintos do chunk + check `expiration_date < HOJE`.
2. Para cada lote vencido com saldo livre > 0:
   - Calcular `qty_a_migrar` (script 09 L795-917 padrao)
   - Criar lote novo on-the-fly: `nome_lote_novo = f'INV-{cod}-{HOJE.strftime("%Y%m%d")}'`
   - Invocar `StockInternalTransferService.transferir_quantidade_para_lote_v2` (mover qty vencida -> lote novo)
   - Atualizar `linhas` do chunk com novo `lot_name`
3. Re-consultar quants apos transferencia (D11 pattern).
4. Continuar com F5a normalmente.

### Sub-objetivo C10.4: Pendencias v15c MEDIUM (opcional v16)

- **B6** `sanitize_for_json` em payloads de `_registrar_auditoria` — protege contra `Decimal` em `payload_json`/`resposta_json`.
- **R-OPS-8** doc clarity em CLI help: `--limite N` semantica.

### Tarefas concretas v16

1. **Setup + baseline** (5min):
   - `cd` worktree + venv + DATABASE_URL+ODOO_*
   - `git fetch + verificar main avancou; rebase se necessario`
   - `pytest tests/odoo/ -q --tb=no` baseline **472 verdes** esperado

2. **Ler MUITA documentacao** (regra inviolavel 0, ~30min):
   - `app/odoo/estoque/CLAUDE.md` (constituicao + tabela §6 atualizada v15c)
   - `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (especialmente §5 SSL/timeout + §7.2 D1-D9 + §10.3 + §12 trilha v15c)
   - `app/odoo/estoque/ROADMAP_SKILLS.md` HANDOFF v15c
   - Memorias: `[[skill5_picking_pattern]]` (v15a + F1 v15c) + `[[skill6_planejar_pre_etapa_pattern]]` (orchestrator C3 v9)
   - Source pattern reuso: `app/odoo/services/inventario_pipeline_service.py` L165-506 (helpers F5d.5/.6/.7) + L945-1102 (f5d_aguardar_invoices)
   - Orchestrator v15c atual: `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (~1700 LOC)
   - Atomo Skill 5 com F1: `app/odoo/estoque/scripts/picking.py:836-1100`
   - `_commit_helpers.py` v15c: `app/odoo/estoque/scripts/_commit_helpers.py`

3. **AskUserQuestion sobre escopo v16** (~5min):
   - Opcao A: C10 (F5d completo) + C10.1 (helpers) + C10.2 (ETAPA A real) + C10.3 (G014) — sessao longa ~250min
   - Opcao B: C10 + C10.1 sozinho — ETAPA A + G014 em v16-2
   - Opcao C: Capinar `_invoice_helpers.py` separado vs inline na classe

4. **Implementacao** (~150min se opcao A):
   - Editar `app/odoo/estoque/orchestrators/faturamento_pipeline.py`:
     - Adicionar helpers `_garantir_payment_provider`, `_garantir_fiscal_setup`, `_corrigir_price_zero_em_invoice` (inline OU import de `_invoice_helpers.py` novo)
     - Implementar `_executar_etapa_c` real (substituir stub)
     - Expandir `_executar_etapa_a` real (CR-H3 TODO v15b)
     - Adicionar `_g014_pre_check_lotes_vencidos` em `_processar_chunk_etapa_b` (CR-F3 TODO v15c)
   - >=20 pytest novos (F5d polling mock + sub-etapas + ETAPA A real + G014)

5. **Smoke dry-run PROD** (~15min):
   - Identificar 1 ajuste com `fase_pipeline='F5c_LIBERADO'` em PROD (12 esperados conforme contagem v15b — verificar atualizado)
   - Rodar `faturamento_pipeline.py --ciclo INVENTARIO_2026_05 --etapas C --dry-run --pular-pre-flight`
   - Validar: polling planejado + sub-etapas planejadas

6. **Code-review paralelo** (~20min):
   - Dispatch >=2 reviewers paralelos com focos distintos (F5d polling SSL/anti-DetachedInstance + sub-etapas idempotencia)

7. **Cross-refs + commit + PROMPT v17** (~25min):
   - CLAUDE.md estoque + ROADMAP HANDOFF + PLANEJAMENTO §0 + §7 (C10 ✅) + §12 trilha v16
   - Commit consolidado v16
   - Atualizar PROMPT_PROXIMA_SESSAO para v17 (F5e SEFAZ Playwright + ETAPA E RecLF + ETAPA F G023)

## ⚠️ PRE-MORTEM v16 (riscos novos)

| # | Risco | Mitigacao |
|---|-------|-----------|
| **R31** | Polling 1800s em PROD pode dormir SSL pos-keepalive — re-fetch ajuste expira no meio | F6 `safe_session_get` apos polling resolved (ja codificado v15c) + D14 `commit_resilient` (ja v15c) + D10 dispose macro (ja v15c F7) |
| **R32** | Sub-etapa F5d.7 (G034) em invoice ja `state='posted'` exige reset_to_draft — pode quebrar se NF ja SEFAZ-autorizada | Codificar guard `l10n_br_situacao_nf NOT IN ('autorizado', 'excecao_autorizado')` antes do reset (script L293-399 padrao) |
| **R33** | Robo CIEL IT em pico >2h sem criar invoice — timeout do polling expira -> bulk parcial | Adicionar `--janela-permitida` warning (D11 do PLANEJAMENTO §5.3). Operador override `--ignorar-janela` |
| **R34** | ETAPA A real-run com Skill 2 chamada N+1 (1 read quant + 1 transfer per ajuste) — bulk 700 ajustes = 1400 RPCs Odoo | Considerar batch read de quants em 1 RPC + dispatch transfer apenas quando necessario (~10-30% dos ajustes esperado precisar) |
| **R35** | G014 lote vencido on-the-fly cria lotes INV-{cod}-{HOJE} mas se onda re-roda no dia seguinte, novo lote criado (acumulacao) | Idempotencia via search `stock.lot` por nome EXATO antes de criar (Skill 2 ja faz internamente? Verificar) |
| **R36** | Sub-etapa F5d.5 (G029 payment_provider) write em `account.move` ja posted pode falhar — reset_to_draft? | Codificar fallback v15c F6 padrao — try write direto, se falhar try reset_to_draft+write+post |
| **R37** | Ajuste pode ter `picking_id_odoo` populado mas robo CIEL IT NAO criou invoice (timing) — orchestrator interpreta como timeout e falha | Differentiate `'sem invoice ainda'` (continuar polling) vs `'invoice criada mas state errado'` (sub-etapa F5d.5+) |

## LEITURAS OBRIGATÓRIAS (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituição) — §6 catálogo skills atualizado v15c
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF v15c
3. `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (regra inviolavel 0):
   - §0 cabeçalho (status v15c — 472 verdes, 15 fixes aplicados)
   - §5 SSL/timeout/recovery (G016 + D10/D14)
   - §7.2 D1-D9 mineracao service (F5d L945-1102 + helpers .5/.6/.7 L165-506)
   - §10.3 paralelismo (etapa-barreira + D10/D11)
   - §12 trilha v15c (esta sessao terminou) — detalha 15 fixes
4. Memorias: `[[skill5_picking_pattern]]` (v15a + F1 v15c) + `[[skill6_planejar_pre_etapa_pattern]]` (orchestrator C3 v9)
5. Orchestrator v15c atual: `app/odoo/estoque/orchestrators/faturamento_pipeline.py`
6. Helper v15c novo: `app/odoo/estoque/scripts/_commit_helpers.py`

Para implementacao:
- `app/odoo/services/inventario_pipeline_service.py` L165-506 (helpers F5d) + L945-1102 (f5d_aguardar_invoices) — EXTRAIR padroes, NAO copiar
- `app/odoo/estoque/scripts/transfer.py` (Skill 2 `transferir_quantidade_para_lote_v2`) — para ETAPA A real
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py:795-917` (G014 logica) — EXTRAIR

## CHECKLIST DA SESSÃO v16

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v15c (ea455fe8)
[ ] Pytest baseline: 472 verdes esperado
[ ] Ler memorias [[skill5_picking_pattern]] (v15a+F1) + [[skill6_planejar_pre_etapa_pattern]]
[ ] Ler PLANEJAMENTO §5 + §7.2 D1-D9 + §10.3 + §12 v15c
[ ] AskUserQuestion sobre escopo v16 (C10+C10.1+C10.2+C10.3 OU faseado)
[ ] AskUserQuestion sobre localizacao helpers F5d.5/.6/.7 (inline OU _invoice_helpers.py)
[ ] Editar faturamento_pipeline.py:
[ ]   - Adicionar helpers _garantir_payment_provider (G029)
[ ]   - Adicionar helpers _garantir_fiscal_setup (G034 DEV_*)
[ ]   - Adicionar helpers _corrigir_price_zero_em_invoice (G007)
[ ]   - Implementar _executar_etapa_c real (substituir stub)
[ ]   - Expandir _executar_etapa_a real (CR-H3 v15b TODO + Skill 2 integration)
[ ]   - Codificar G014 pre-check em _processar_chunk_etapa_b (CR-F3 v15c TODO)
[ ]   - Deprecate permitir_etapa_a_noop_real (manter compat ate v17)
[ ]   - (opcional B6) sanitize_for_json em _registrar_auditoria payloads
[ ] 20+ pytest novos verdes (F5d polling + sub-etapas + ETAPA A real + G014)
[ ] Smoke dry-run PROD em ajuste F5c_LIBERADO real
[ ] >=2 code-reviewers paralelos (focos: SSL/anti-DetachedInstance + sub-etapas idempotencia)
[ ] Atualizar PLANEJAMENTO §0 + §7 (C10 ✅) + §12 trilha v16 + ROADMAP HANDOFF
[ ] Commit consolidado v16
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v17 (F5e SEFAZ + ETAPA E + ETAPA F)
```

## CRONOGRAMA RESTANTE (apos v15c)

| Sessão | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| v15c (concluida) | Pre-mortem + 4 reviewers paralelos + 15 hardening fixes | (refinamento C6-C9) | Medio ✅ |
| **v16 (proxima)** | **C10 F5d aguardar invoices + sub-etapas .5/.6/.7 + ETAPA A real (CR-H3) + G014 (CR-F3)** | C10 | Medio (SSL critico + sub-etapas idempotentes) |
| v17 | C11 F5e SEFAZ Playwright (IRREVERSIVEL) + C12 ETAPA E RecLF + C13 ETAPA F G023 invocando atomo Skill 5 v15a | C11, C12, C13 | Alto (SEFAZ + paralelismo G-RECLF-1) |
| v18 | C14 recovery (--resume + stagnation detector) + C15 SKILL.md + C16 pytest baseline + C17 smokes + B6 sanitize_for_json | C14-C17 | Medio |
| v19 | C18 folhas fluxos + C19 cross-refs + C20 Canary REAL PROD (1 ajuste) | C18-C20 | Alto (1a NF real Skill 8) |
| v20+ | C21 bulk REAL PROD + C22 code-review + C23 commit final + arquivar 09_* SUPERADOS | C21-C23 | Alto (volume real) |

**Total restante**: 5-6 sessoes (v16 → v20+).

## REGRAS INVIOLÁVEIS NOVAS v15c (somar as 60+ anteriores)

67. **(v15c F1 CRITICAL)** Atomo `criar_picking_inter_company` da Skill 5 v15c+ EXIGE `origin` obrigatorio + busca por origin antes de create. SEM essa idempotencia, re-execucao apos SSL drop cria DUPLICATA -> 2 NFs SEFAZ irreversiveis. Status return novo: `CRIADO | IDEMPOTENT_DONE | IDEMPOTENT_OTHER`. Tentativa de regressao re-introduz catastrofe fiscal.

68. **(v15c F2)** Orchestrator `_processar_chunk_etapa_b` ABORTA chunk (`return out_chunk`) se `_commit_resilient` retorna `False` apos F5a OK. Continuar para F5b com DB local dessincronizado e' bug.

69. **(v15c F4)** `executar_pipeline_bulk` faz `db.session.expire_all()` EXPLICITO entre etapas (D11). Era implicito em v15b (cada etapa fazia internamente). Blueprint exige explicito no macro.

70. **(v15c F5)** `executar_etapa_a` em real-run sem `permitir_etapa_a_noop_real=True` levanta `NotImplementedError`. Anti-armadilha: marcar `TRANSF_OK` sem validar Odoo permitia ETAPA B operar em quants nao preparados. v16 substitui guard por Skill 2 real.

71. **(v15c F7)** `db.engine.dispose()` profilatico ANTES e APOS ETAPAS C/D no macro `executar_pipeline_bulk`. Ativo em v15c stubs; v16/v17 quando ETAPA C/D escalarem ja' tem proteção D10.

72. **(v15c F8)** `ACAO_PARA_DIRECAO` + `ACAO_PARA_CFOP_ENTRADA` + `ACOES_ENTRADA_FB` SAO fontes unicas em `app/odoo/constants/operacoes_fiscais.py`. Service legado `inventario_pipeline_service.py` mantem copia local ate v17 capinar — orchestrator IMPORTA daqui.

73. **(v15c F9)** Commit SSL-resilient via `from app.odoo.estoque.scripts._commit_helpers import commit_resilient, safe_session_get`. SSL match TIGHTENED (lista especifica `['ssl', 'decryption', 'bad record', 'closed unexpectedly']`). Versoes inline antigas marcadas DEPRECATE.

74. **(v15c F12)** `AjusteEstoqueInventario.external_id_operacao` populado em CADA fase (F5a/F5b/F5c). Rastreabilidade auditoria<->registro pai inviolavel.

## NÃO-FAZER (red flags v16)

❌ Começar v16 SEM ler PLANEJAMENTO §12 trilha v15c (entender o que 15 fixes mudaram)
❌ Recriar `_commit_resilient` inline — DEVE importar de `_commit_helpers.py`
❌ Recriar `ACAO_PARA_DIRECAO` no orchestrator — DEVE importar de `operacoes_fiscais.py`
❌ Esquecer `db.engine.dispose()` ANTES e APOS ETAPA C (D10 ja' codificado em v15c — preservar quando implementar C real)
❌ Esquecer SNAPSHOT meta antes do polling (D5) + `safe_session_get` apos (D9 + F6 v15c)
❌ Falha em sub-etapa F5d.5/.6/.7 derrubar o ajuste — devem ser try/except (D6) independentes
❌ Implementar F5e Playwright em v16 (isso é v17 — preservar contexto SEFAZ irreversivel)
❌ Esquecer `external_id_operacao` em F5d_INVOICE_GERADA (F12 v15c pattern)
❌ Esquecer F2 abort se commit_resilient falha (preservar em qualquer nova sub-etapa)
❌ Quebrar pytest baseline 472 verdes (esperado >=492 apos v16 com 20+ pytest novos)
❌ Aceitar TODO B6 sanitize_for_json em v16 se houver Decimal nos payloads de F5d (codificar)

## REFERÊNCIAS RÁPIDAS

- **Commit v15c**: `ea455fe8` (worktree feat/estoque-odoo)
- **Commit v15b**: `e38ec281` (orchestrator base)
- **Commit v15a**: `8ecfaaff`+`6c9fffff` (Skill 5 estendida)
- **Baseline pytest**: 472 verdes em 15.27s
- **Smoke PROD ultimo**: cod 210639522 INDUSTRIALIZACAO_FB_LF DRY_RUN_OK
- **Atomos Skill 5 v15a + F1 v15c**: 3 atomos inter-company + idempotencia origin
- **Sub-skill C5 v14b**: PRE-FLIGHT via subprocess (perfil 'inventario')

---END---
