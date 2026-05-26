---
name: faturando-odoo
description: >-
  Skill WRITE (orchestrator C3 macro) para FATURAR SAIDA inter-company de
  inventario: NF (account.move) -> robo CIEL IT XML-RPC -> SEFAZ via Playwright
  (IRREVERSIVEL). Constituição §6: Skill 8 = SO SAIDA; par da Skill 7
  `escriturando-odoo` (= SO ENTRADA RecebimentoLf/DFe). Quem une saida + entrada
  = FLUXO L3 (1.3-transferencia-completa.md ⬜ a escrever v20+).

  Pipeline A->B->C->D->E->F com PRE-FLIGHT C5 + 3 modos CLI (bulk / pre-flight
  / resume v18). Compoe Skill 2 v2 (ETAPA A) + Skill 5 v15a 3 atomos inter-company
  (F5a/F5b/F5c + ETAPA F G023) + Playwright SEFAZ (ETAPA D irreversivel) +
  Skill 7 `escriturando-odoo` (ETAPA E delegada).

  Usar quando o pedido eh: "fatura a NF inter-company X", "executa onda completa
  de faturamento LF/CD/FB", "retoma faturamento travado em D apos crash",
  "smoke 1 ajuste end-to-end", "pre-flight cadastro fiscal antes de bulk",
  "transmite NFs via SEFAZ".

  V1 LIVE (2026-05-26 v17.5+v18): ETAPA F canary DEV_FB_LF + TRANSFERIR_FB_CD
  via flag `--auto-confirma-direcao-nova` (PALIATIVO — caminho B; refator v19+
  para FLUXO L3 que invoca Skill 7 escriturando-odoo extrair PO+picking nativo).

  NAO USAR PARA:
  - Escrituracao ENTRADA (RecebimentoLf/DFe) -> Skill 7 escriturando-odoo
  - Picking generico (cancelar/validar/devolver fora pipeline) -> Skill 5
  - Transferencias internas pre-faturamento intra-empresa -> Skill 2
  - Recebimento de COMPRAS (DFe fornecedor 4 fases) -> gestor-recebimento
  - Cancelar NF SEFAZ-autorizada (processo formal 24h) -> NAO ha atomo
  - Lancar CTe / despesa extra -> integracao-odoo (LancamentoOdooService 16 etapas)

  `--dry-run` eh o DEFAULT no CLI; ETAPA D em real-run exige `--confirmar-sefaz`
  (2 nivel — IRREVERSIVEL). ETAPA F canary direcoes novas exige
  `--auto-confirma-direcao-nova`.
allowed-tools: Read, Bash, Glob, Grep
---

# faturando-odoo (WRITE — orchestrator C3 macro)

Skill **PIPELINE COMPLETO A-F LIVE v17.5+v18** (criada em 2026-05-25 v15b
como esqueleto; A-F maturada v16+v17; revert ETAPA E + Skill 7 + ETAPA F
canary v17.5; recovery `executar_pipeline_resume` v18). Constituicao:
`app/odoo/estoque/CLAUDE.md` §6.

Orchestrator: `app/odoo/estoque/orchestrators/faturamento_pipeline.py`
(FaturamentoPipelineExecutor, ~4150 LOC).
Service-fonte legado (COMPAT, NAO MEXER): `app/odoo/services/inventario_pipeline_service.py` (1346 LOC, minerado em §7.2 do planejamento).
Script-fonte macro (SUPERADO ao final v22+): `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (1866 LOC, minerado em §7.3).

---

## REGRAS CRITICAS

1. **`--dry-run` eh o DEFAULT.** Sem `--confirmar`, so calcula e mostra o plano.
2. **`--confirmar-sefaz` exigido para ETAPA D real-run** (IRREVERSIVEL — NF
   autorizada SEFAZ so cancela via processo formal 24h sem uso + declaracao).
3. **`--auto-confirma-direcao-nova` exigido para ETAPA F canary** DEV_FB_LF +
   TRANSFERIR_FB_CD (sem precedente PROD em v17.5; caminho B PALIATIVO).
4. **PRE-FLIGHT C5 obrigatorio** (sub-skill `auditando-cadastro-fiscal-odoo`
   `--perfil inventario`) — `--pular-pre-flight` so para pytest/smoke.
5. **Etapa = barreira de sincronizacao macro** (D11): `db.session.expire_all()`
   + re-load entre etapas; `db.engine.dispose()` profilatico antes/apos C+D.
6. **CR-H4 guard arquitetural**: ETAPA D bloqueada se ETAPA B falhou (anti-cascata).
7. **Sub-etapas D5/D7/D8/D9 codificadas** em ETAPA D (SNAPSHOT meta + HARD_FAIL_CONFIG
   aborta batch + idempotencia tripla F5e + safe_session_get pos-Playwright).
8. **NAO mexer no service externo `RecebimentoLfOdooService`** (4562 LOC, 37
   etapas — validados PROD; encapsulado pela Skill 7 atomo).
9. **NAO mexer no script `09_executar_onda1_bulk.py`** (regra v14a-ops — SUPERADO
   ao final do v22+ apos canary + bulk REAL PROD validados).

---

## MODOS DISPONIVEIS

### `--modo bulk` (default — pipeline A->F)
Executa etapas em sequencia, com barreira MACRO entre cada uma.
```
PRE-FLIGHT C5 -> A -> expire_all -> B -> expire_all -> C -> dispose -> D -> dispose -> E -> F
```
Aceita `--etapas A,B` para parar antes de C (smoke parcial). ETAPA D em
real-run exige `--confirmar-sefaz`. ETAPA F canary exige `--auto-confirma-direcao-nova`.

### `--modo pre-flight` (auditoria de cadastro fiscal)
Invoca sub-skill C5 `auditando-cadastro-fiscal-odoo` `--perfil inventario`
e retorna JSON sem entrar no pipeline. Use quando quiser checar cadastro
sem rodar nada.

### `--modo resume` (v18 — recovery iterativo)
Loop de `executar_pipeline_bulk(etapas=(apenas_etapa,))` ate' (a) pendentes==0
OU (b) detector_stagnation OU (c) max_iter atingido. Substitui scripts shell
`fat_lf_resume.sh` + `fat_lf_resume_entrada.sh`. Exige `--apenas-etapa B/C/D/E/F`.
Default `max_iter=18` + `detector_stagnation=True`. Recovery NAO re-roda
PRE-FLIGHT (custoso; ETAPAS B-F nao escrevem cadastro).

---

## Contrato — `FaturamentoPipelineExecutor.executar_pipeline_bulk` (entry-point principal)

```
objeto:        account.move (NF saida) + stock.picking (saida) + Playwright SEFAZ
               (compoe Skills 2 + 5 + 7 + servico Playwright)
input:         --ciclo NOME --etapas LISTA [--company-origem-id ID]
               [--cod-produto X] [--limite N] [--confirmar] [--confirmar-sefaz]
               [--auto-confirma-direcao-nova] [--pular-pre-flight]
output (JSON): {ciclo, etapas_solicitadas, pre_flight, etapas_executadas:
               {A: {...}, B: {...}, ...}, status, tempo_ms}
pre-condicoes: AjusteEstoqueInventario com status in (PROPOSTO, APROVADO)
               + acoes mapeadas em ACAO_PARA_DIRECAO
               PRE-FLIGHT C5 pode_faturar=True (ou --pular-pre-flight)
pos-condicoes: NF autorizada SEFAZ (chave_nfe gravada) + fase_pipeline avancada
               etapa a etapa + RecebimentoLf criado p/ ACOES_ENTRADA_FB
               + picking entrada manual destino criado p/ ACOES_ENTRADA_DESTINO_MANUAL
gotchas-invariante:
  - G011 timing CIEL IT (polling fire_and_poll)
  - G016 SSL drop (_commit_resilient + engine.dispose)
  - G018 weight=0 (l10n_br_peso_liquido fallback no atomo Skill 5)
  - G019/G020 picking state (validar() re-le state pos-button_validate)
  - G022 over-reservation (sleep 5s entre chunks ETAPA B)
  - G023 company_id forcado em moves (atomo Skill 5)
  - G034 fiscal_position DEV_* (corrigir_fiscal_setup F5d.7)
  - G035 barcode invalido (sub-skill C5 G035 pre-flight)
  - G037 (v18 NOVO) operacao nao cadastrada exige cfop_esperado da MATRIZ_INTERCOMPANY
  - D-OPS-3 tracking='none' (atomo Skill 5 remove lot_name automaticamente)
  - D-OPS-5 produto sem lote (Skill 2 aceita_tracking_none=True)
  - HARD_FAIL_CONFIG_ERRORS aborta batch SEFAZ (D7)
modos:         dry-run default -> --confirmar (B/C/E/F) -> --confirmar-sefaz (D)
status:        EXECUTADO_OK | EXECUTADO_PARCIAL | DRY_RUN_OK | DRY_RUN_PARCIAL
               | BLOQUEADO_PRE_FLIGHT | FALHA_PRE_FLIGHT_CLI_AUSENTE
               | FALHA_PRE_FLIGHT_TIMEOUT | FALHA_USO
```

## Contrato — `FaturamentoPipelineExecutor.executar_pipeline_resume` (v18 — recovery)

```
objeto:        loop iterativo de executar_pipeline_bulk(etapas=(apenas_etapa,))
input:         --apenas-etapa B|C|D|E|F --max-iter 18 --timeout-iter 900
               [--sem-stagnation] [--confirmar] [--confirmar-sefaz] [demais flags do bulk]
output (JSON): {modo='resume', ciclo, apenas_etapa, max_iter, iteracoes_executadas,
               restantes_iniciais, restantes_por_iter: [{iter, restantes,
               status_bulk, tempo_ms}, ...], motivo_parada, ultima_invocacao_bulk,
               status, tempo_ms, erro?}
motivo_parada: TUDO_OK_INICIAL | TUDO_OK | STAGNATION | MAX_ITER | EXCECAO | FALHA_USO
pos-cond:     pendentes da etapa zerados (TUDO_OK) OU bloqueado (operador investiga)
```

---

## Receita 1: Canary 1 ajuste + Bulk onda + ETAPA F canary com flag

**Contexto v17.5+v18**: smoke end-to-end com 1 produto, depois bulk PROD,
e canary ETAPA F (caminho B PALIATIVO — refator v19+ extrair FLUXO L3 +
Skill 7 escriturando-odoo).

```bash
# 1. SMOKE dry-run 1 ajuste (pre-flight + A-F simulado)
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' \
  /home/rafaelnascimento/projetos/frete_sistema/.env); set +a

python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --ciclo INVENTARIO_2026_05 \
  --etapas A,B,C,D,E,F \
  --cod-produto 105000007 \
  --limite 1 \
  --pular-pre-flight  # smoke dispensa pre-flight C5

# Esperado: DRY_RUN_OK em ~1-2s; etapas_executadas mostra plano por etapa.

# 2. BULK real PROD onda completa (com pre-flight + 2 niveis confirmar)
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --ciclo INVENTARIO_2026_05 \
  --company-origem-id 5 \
  --confirmar \
  --confirmar-sefaz \
  --auto-confirma-direcao-nova \
  --usuario operador_onda1

# Tempo estimado: A=segundos; B=minutos; C=15-30min (polling CIEL IT);
# D=5-10min/NF * N (Playwright SEFAZ); E=30-60min/invoice (G-RECLF-1);
# F=segundos/picking. Onda 100 ajustes: ~50-100h sequencial.

# 3. ETAPA F canary isolada (DEV_FB_LF + TRANSFERIR_FB_CD — PALIATIVO v17.5)
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --ciclo INVENTARIO_2026_05 \
  --etapas F \
  --cod-produto 999999 \
  --confirmar \
  --auto-confirma-direcao-nova  # libera canary direcoes novas

# Esperado: picking manual criado via Skill 5 atomo
# `criar_picking_entrada_destino_manual` (CAMINHO B paliativo — caminho A
# correto fiscalmente seria via FLUXO L3 escriturar DFe que cria PO+picking
# nativo; refator v19+).
```

## Receita 2: Resume apos crash mid-ETAPA D (--modo resume --apenas-etapa D)

**Contexto v18**: Playwright SEFAZ travou (G016 SSL drop, robo CIEL IT lento,
crash mid-loop). Re-rodar ETAPA D em loop ate' todas NFs transmitidas OU
detector_stagnation parar (operador investiga).

```bash
# Loop ate 18 iter (default) ou TUDO_OK ou STAGNATION
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --modo resume \
  --apenas-etapa D \
  --ciclo INVENTARIO_2026_05 \
  --max-iter 18 \
  --confirmar \
  --confirmar-sefaz

# Output JSON:
# {
#   "modo": "resume", "apenas_etapa": "D", "max_iter": 18,
#   "iteracoes_executadas": 5,
#   "restantes_iniciais": 50,
#   "restantes_por_iter": [
#     {"iter": 1, "restantes": 35, "status_bulk": "EXECUTADO_OK", "tempo_ms": 854312},
#     {"iter": 2, "restantes": 18, ...},
#     ...
#     {"iter": 5, "restantes": 0, ...}
#   ],
#   "motivo_parada": "TUDO_OK",
#   "ultima_invocacao_bulk": {...},
#   "status": "EXECUTADO_OK"
# }

# Exit code 0 = TUDO_OK; 1 = STAGNATION/MAX_ITER (operador investiga);
# 4 = DRY_RUN_OK.

# Variante: desligar stagnation detector (operador sabe que D tem timing
# irregular e quer mais chances)
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --modo resume --apenas-etapa D --ciclo INVENTARIO_2026_05 \
  --sem-stagnation --max-iter 30 \
  --confirmar --confirmar-sefaz
```

## Receita 3: Resume mid-ETAPA E + F isoladas (RecebimentoLf + entrada manual)

**Contexto v18**: ETAPA E (Skill 7 RecebimentoLf X->FB) demora 30-60min/invoice
via robo CIEL IT (G-RECLF-1). Em onda 100 invoices = 50-100h sequencial.
Substitui `fat_lf_resume_entrada.sh` (E loop 30 iter + F loop 12 iter).

```bash
# ETAPA E: cria RecebimentoLf para PERDA_LF_FB / DEV_LF_FB / DEV_CD_LF / DEV_LF_CD.
# HIGH-3 RETOMA se status='processando' (anti-RecLf orfao por crash).
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --modo resume --apenas-etapa E \
  --ciclo INVENTARIO_2026_05 \
  --max-iter 30 \
  --confirmar

# ETAPA F: picking entrada manual destino (G023) para INDUSTRIALIZACAO_FB_LF
# + canary DEV_FB_LF/TRANSFERIR_FB_CD com flag.
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --modo resume --apenas-etapa F \
  --ciclo INVENTARIO_2026_05 \
  --max-iter 12 \
  --confirmar \
  --auto-confirma-direcao-nova  # opcional, libera canary

# Combinacao: rodar E ate' OK, depois F:
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --modo resume --apenas-etapa E --ciclo INVENTARIO_2026_05 \
  --max-iter 30 --confirmar && \
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --modo resume --apenas-etapa F --ciclo INVENTARIO_2026_05 \
  --max-iter 12 --confirmar --auto-confirma-direcao-nova
```

## Receita 4: Pre-flight isolado (--modo pre-flight, sub-skill C5 sem dispatch)

**Contexto**: Auditoria de cadastro fiscal antes de rodar pipeline. Operador
quer ver se ha bloqueios (NCM, barcode, weight) sem disparar SEFAZ.

```bash
python -m app.odoo.estoque.orchestrators.faturamento_pipeline \
  --modo pre-flight \
  --ciclo INVENTARIO_2026_05

# Output JSON da sub-skill C5 (perfil 'inventario'):
# {
#   "status_global": "PRE_FLIGHT_WARN" | "PRE_FLIGHT_OK" | "PRE_FLIGHT_BLOQUEADO",
#   "pode_faturar": true | false,
#   "auditados": 158,
#   "bloqueios": {"ncm": [...], "barcode": [...], "weight": [...]},
#   "warnings": {...},
#   "tempo_ms": 987
# }

# Exit code 0 = PRE_FLIGHT_OK ou WARN; 1 = BLOQUEADO (corrigir cadastro antes).

# Variante: sub-skill C5 com auto-fix barcode (G035)
python .claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py \
  --ciclo INVENTARIO_2026_05 \
  --auto-corrigir-barcode  # opcional, escreve product.barcode=False
```

---

## TRADE-OFFS V1 ACEITOS

| Trade-off | Razao | Mitigacao |
|-----------|-------|-----------|
| **ETAPA E SEQUENCIAL** | Decisao 10.7 v17 (Rafael 2026-05-25): `RecebimentoLfOdooService` NAO eh thread-safe (Redis state interno). | Recovery via `--modo resume --apenas-etapa E` + HIGH-3 retoma. Aceito 50-100h/onda. |
| **ETAPA D Playwright serial** | 1 browser global SSW; G016 SSL drop frequente. | `--modo resume --apenas-etapa D --max-iter 18` + idempotencia tripla F5e. |
| **PRE-FLIGHT C5 via subprocess** | Sub-skill C5 eh CLI separado (perfis multiplos: inventario, futuro venda-cliente). | Tradeoff: env=os.environ.copy() + sys.executable preserva venv. |
| **ETAPA F canary direcoes novas** (DEV_FB_LF + TRANSFERIR_FB_CD) | Sem precedente PROD em v17.5. PT 50 CD/IN/INTER descoberto via audit. | Flag `--auto-confirma-direcao-nova` bloqueia em real-run sem confirmacao explicita; dry-run sempre planeja todas. |
| **MIGRACAO -> INV-{cod}-{YYYYMMDD} lote na entrada manual** | Lote MIGRACAO eh agregador; entrada manual cria lote real por dia + cod. | Idempotente por dia; pickings de mesmo dia mesmo cod reusam lote. |
| **`--timeout-iter` NAO eh ENFORCADO em v18** (CR v18 F3) | Parametro existe no CLI + assinatura do `executar_pipeline_resume`, mas NAO eh propagado para `executar_pipeline_bulk` (que nao tem timeout). Operador que passa `--timeout-iter 300` esperando 5min/iter NAO ganha enforcement. | Operador deve usar `timeout NNN python -m ...` do shell Linux para enforcement real. Enforcement via threading pendente refator v19+. |
| **stdout mistura logs Flask + JSON** (CR v18 F4) | `app/__init__.py` + extensoes escrevem logs em stdout durante setup ("✅ Tipos PostgreSQL...", "✅ Modulo HORA registrado..."); JSON final tambem vai para stdout via `print(json.dumps(result))`. Aceitavel para operador humano (le terminal). CRITICO se Skill 8 for invocada via subprocess por outra skill (parser JSON quebra em logs pre-JSON). | Operador: `python -m ... 2>/dev/null \| tail -N \| jq` OU redirecionar arquivo direto. Para subprocess futuro: configurar logs em stderr OU adicionar `--quiet` flag (pendente v19+). |
| **CR-H4 guard ETAPA D NAO se aplica em --modo resume isolado** (CR v18 F2) | `executar_pipeline_bulk` tem CR-H4 que aborta ETAPA D se ETAPA B falhou. Mas `--modo resume --apenas-etapa D` chama bulk com `etapas=(D,)` — B nao esta no caminho, CR-H4 nao avalia. | OK em pratica: `executar_etapa_d` filtra `fase_pipeline=[F5d_INVOICE_GERADA, F5e_FALHA]`. Ajustes em fase pre-D (None/TRANSF/F5a/F5b/F5c) sao ignorados — recovery so processa ajustes ja com invoice. Operador deve rodar `--modo bulk --etapas A,B,C,D` antes de tentar resume D. |

---

## ANTIPADROES DETECTADOS V17.5 — REFATOR V19+ (NAO ENTRA NO ESCOPO V18)

> Documentado para que sessoes futuras nao reintroduzam.

### Antipadrao 1: Skill 7 V1 STRICT (raise NotImplementedError)
- Atomo `EscrituracaoLfService.criar_recebimento_orchestrado` raise se cnpj!=LF
  OU company_recebedor!=FB. Limita Skill 7 a 1 direcao.
- **Correto**: Skill 7 deveria ser ATOMICA mas ABRANGENTE (1 objeto Odoo:
  DFe/account.move). Limites = FLUXOS + CONSTANTS + PRE-FLIGHT, NAO o atomo.
- **Esperado v19+**: extrair atomos COMUNS entre `RecebimentoLfOdooService`
  (37 steps) + `LancamentoOdooService` (16 etapas — fretes/CTe) + `escriturar_dfe_lf.py`
  (FLUXO A inventario). Atomos: `buscar_ou_criar_dfe`, `configurar_dfe`,
  `gerar_po_from_dfe`, `configurar_po`, `confirmar_po`, `criar_invoice_from_po`,
  `configurar_invoice`, `calcular_imposto`, `postar_invoice`, `finalizar_lancamento`.

### Antipadrao 2: ETAPA F orchestrator cria picking manual via Skill 5
- ETAPA F invoca `criar_picking_entrada_destino_manual` (Skill 5) que cria
  picking SEM PO + partner_id.
- **Correto**: ETAPA F deveria ser FLUXO L3 que compoe:
  - Skill 7: `escriturar_dfe(...)` -> PO criada -> picking nativo (com PO+partner)
  - Skill 5: `preencher_lotes_picking(picking_id, lote='MIGRACAO')` (atomo a criar)
  - Skill 7: `criar_invoice_from_po(po_id)` -> ENTIN CFOP 1901
- **Esperado v19+**: criar FLUXO L3 `1.2.1-escriturar-dfe-industrializacao.md`
  + reescrever ETAPA F para invocar FLUXO; `criar_picking_entrada_destino_manual`
  permanece como CAMINHO B paliativo documentado.

### Antipadrao 3 (relacionado): orchestrator Skill 8 NUNCA deveria chamar
- Skill 5 ou Skill 7 INLINE. Eh FLUXO L3 que compoe.
- Constituicao §6 reforcada: "Fluxo >> Skill"
- v17.5 ETAPA F chama Skill 5 atomo direto -> viola §6
- v17.5 ETAPA E chama Skill 7 atomo do orchestrator -> viola §6
  (mas menos grave que v17 inline ~420 LOC)
- **Esperado v19+**: extrair ETAPA E e ETAPA F do orchestrator para FLUXOS L3;
  orchestrator Skill 8 = SO SAIDA (A->B->C->D); FLUXO L3 1.3 compoe
  Skill 8 saida + Skill 7 entrada.

### Antipadrao 4: V1 STRICT pre-cond ANTES de dry-run check
- Skill 7 raise NotImplementedError mesmo em `dry_run=True`. Operador nao
  consegue "planejar" um CD->FB hipotetico.
- Reviewer 1 F4 conf 80 marcou como API footgun pequeno.
- **Esperado v19+**: ao refatorar Skill 7 ABRANGENTE, dry-run sempre deve
  planejar (mesmo direcoes nao implementadas), so write-path raise.

---

## CROSS-REFS

- Constituicao: `app/odoo/estoque/CLAUDE.md` §6 (catalogo Skill 8)
- Planejamento Skill 8 MACRO: `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`
  (sobrevive N sessoes; REGRA INVIOLAVEL 0 = ler INTEIRO antes de mexer)
- Roadmap migracao: `app/odoo/estoque/ROADMAP_SKILLS.md` HANDOFF v18
- Subagente: `.claude/agents/gestor-estoque-odoo.md` (atualizar com Skill 8)
- ROUTING_SKILLS: `.claude/references/ROUTING_SKILLS.md` (entry Skill 8)
- tool_skill_mapper: `app/agente/services/tool_skill_mapper.py`
- Skill 7 par (entrada): `.claude/skills/escriturando-odoo/SKILL.md`
- Sub-skill C5 PRE-FLIGHT: `.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md`
- Skill 5 atomos inter-company: `.claude/skills/operando-picking-odoo/SKILL.md`
- Skill 2 v2 ETAPA A: `.claude/skills/transferindo-interno-odoo/SKILL.md`
- Service-fonte legado (COMPAT): `app/odoo/services/inventario_pipeline_service.py`
- Script-fonte SUPERADO ao final: `scripts/inventario_2026_05/09_executar_onda1_bulk.py`
- Scripts shell substituidos pelo --modo resume: `scripts/inventario_2026_05/fat_lf_resume.sh`
  + `scripts/inventario_2026_05/fat_lf_resume_entrada.sh`
- Gotchas Odoo: `.claude/references/odoo/GOTCHAS.md` (referencia rapida) +
  `docs/inventario-2026-05/02-gotchas/` (G011, G016, G018, G019,
  G020, G022, G023, G034, G035, G036, G037 NOVO v18, D-OPS-3, D-OPS-5)
- IDs fixos: `.claude/references/odoo/IDS_FIXOS.md` (PT 19 LF/IN, PT 50 CD/IN/INTER,
  PT 53 FB/Exped/Industr)

---

## CHECKLIST DE EXPANSAO V19+ (futuro — antipadroes detectados v17.5)

- [ ] Refatorar Skill 7 ABRANGENTE — extrair atomos COMUNS entre `RecebimentoLfOdooService`
      + `LancamentoOdooService` + `escriturar_dfe_lf.py`
- [ ] Criar atomo Skill 5 `preencher_lotes_picking(picking_id, lote=...)`
- [ ] Criar FLUXO L3 `1.2.1-escriturar-dfe-industrializacao.md` compondo
      Skill 7 + Skill 5
- [ ] Criar FLUXO L3 `1.5-lancar-frete-cte.md` (provar reuso atomos cross-modulo)
- [ ] Criar FLUXO L3 `1.6-lancar-despesa-extra.md`
- [ ] Reescrever ETAPA F orchestrator para invocar FLUXO L3 1.2.1
      (em vez de Skill 5 inline)
- [ ] Arquivar `criar_picking_entrada_destino_manual` como caminho B paliativo
      documentado (NAO remove — pode ser util em DFe que demora)
- [ ] Criar FLUXO L3 `1.3-transferencia-completa.md` (Skill 8 saida + Skill 7 entrada)
- [ ] Eventualmente: refatorar parcial RecebimentoLfOdoo + LancamentoOdoo
      para virarem WRAPPERS dos atomos Skill 7 (inversao da relacao)
- [ ] 5+ pytest novos cobrindo FLUXO L3 1.2.1 + atomo preencher_lotes_picking
- [ ] CLI wrapper `.claude/skills/faturando-odoo/scripts/faturar.py` (entry-point
      Python wrapping orchestrator com helpers de smoke/canary/resume + JSON unico stdout)
