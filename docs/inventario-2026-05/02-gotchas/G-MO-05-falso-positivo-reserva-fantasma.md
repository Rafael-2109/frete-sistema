<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G-MO-05 — `medir_consumo_mo` indistinto por `state` inflava FURO_CONTABIL em MOs com apenas RESERVA FANTASMA

> **Papel:** G-MO-05 — `medir_consumo_mo` indistinto por `state` inflava FURO_CONTABIL em MOs com apenas RESERVA FANTASMA.

## Indice

- [Sintoma](#sintoma)
- [Causa raiz](#causa-raiz)
- [Solução (v6 — 2026-05-27)](#solução-v6-2026-05-27)
  - [Particionamento de states](#particionamento-de-states)
  - [Nova assinatura](#nova-assinatura)
  - [Guard refinado](#guard-refinado)
  - [Novos status canônicos](#novos-status-canônicos)
  - [Modos READ acessórios (§6.b)](#modos-read-acessórios-6b)
- [Onde está codificada a invariante](#onde-está-codificada-a-invariante)
- [Caso real (origem)](#caso-real-origem)
- [Outros lugares que podem ter mesma falha (auditar)](#outros-lugares-que-podem-ter-mesma-falha-auditar)
- [Ref](#ref)

**Severidade**: MEDIUM (false-positive bloqueava cancelamento legítimo; nenhum dano físico — apenas forçava operador a criar script ad-hoc para bypass do guard)
**Status**: ✅ CORRIGIDO em `app/odoo/estoque/scripts/mo.py` v6 (2026-05-27 — sessão Claude Code 27/05) — `medir_consumo_mo` retorna dict particionado `{done, reservado, total}`; guard G-MO-01 distingue FURO REAL (`done > TOL`) de RESERVA FANTASMA (`reservado > TOL` e `done = 0`).
**Detecção**: codificada no próprio service (invariante de átomo §1 da constituição). Modos READ `listar_mos` / `detalhar_mo` v6 expõem classificação `SEGURO|RESERVA_FANTASMA|FURO_REAL` por item.
**Escopo**: Skill 4 `operando-mo-odoo` (cancelar MO single ou batch). Demais skills não usam `medir_consumo_mo`.

## Sintoma

Skill 4 classificava como `FALHA_FURO_CONTABIL` (G-MO-01 V1) MOs cujos `stock.move` raw materials tinham `quantity > 0` mesmo quando esses moves estavam em `state IN (assigned, waiting, partially_available, confirmed)` — ou seja, apenas com reserva marcada (`picked=True`), sem consumo CONTÁBIL efetivado.

Resultado: operador era forçado a criar script ad-hoc para `action_cancel` direto (caso 2026-05-27: `/tmp/cancelar_mo_nativo.py` foi criado exatamente para isso), perdendo (a) idempotência do service; (b) log JSON estruturado; (c) tratamento de status canônico; (d) cobertura de testes pytest.

## Causa raiz

`medir_consumo_mo` V1 (linhas 97-122 do `mo.py` pré-v6) somava `stock.move.quantity` filtrando apenas por `state != 'cancel'`:

```python
mvs = self.odoo.search_read(
    'stock.move',
    [['raw_material_production_id', 'in', list(ch)],
     ['state', '!=', 'cancel']],
    ['raw_material_production_id', 'quantity'],
)
for m in mvs:
    consumo[rid[0]] += float(m.get('quantity') or 0)
```

Não distinguia:

- **`state='done'`** = baixa CONTÁBIL efetivada → cancelar via `action_cancel` deixa componentes consumidos sem produto finalizado = **furo real**.
- **`state IN (assigned, waiting, partially_available, confirmed)`** = apenas reserva marcada (`picked=True` em Odoo 17 = "operador marcou que pegou da prateleira") → cancelar via `action_cancel` libera as reservas (cascade Odoo), **sem furo** (componentes nunca saíram do estoque contábil).

Em Odoo 17 CIEL IT, `picked=True` em move `assigned`/`waiting` **não** baixa estoque — só dispara baixa quando `button_validate` faz o move ir para `state='done'`. Em MOs zumbi de 2024-2026, ninguém clicou "Marcar como Concluído" → MOs ficaram em `to_close`/`progress` com `picked=True` em todos os raws → V1 somava quantidades e considerava "furo".

## Solução (v6 — 2026-05-27)

**REGRA INVIOLÁVEL**: `medir_consumo_mo` particiona consumo por `state`. Guard G-MO-01 bloqueia apenas `done`.

### Particionamento de states

```python
_STATES_CONSUMO_DONE = ('done',)
_STATES_CONSUMO_RESERVADO = ('assigned', 'waiting', 'partially_available', 'confirmed')
```

### Nova assinatura

```python
def medir_consumo_mo(mo_ids) -> Dict[int, Dict[str, float]]:
    """Retorna {mo_id: {'done': float, 'reservado': float, 'total': float}}."""
```

`medir_consumo_mo_legacy(mo_ids) -> Dict[int, float]` mantido como compat (apenas `total`) para callers que ainda dependem do formato antigo. Deprecar gradualmente.

### Guard refinado

```python
# Antes (V1): bloqueava se total > TOL
if consumo_total > TOL_CONSUMO and not forcar_consumo:
    return FALHA_FURO_CONTABIL

# Depois (V6): bloqueia APENAS done > TOL
if done > TOL_CONSUMO and not forcar_consumo:
    return FALHA_FURO_CONTABIL_REAL
# done = 0 e reservado > 0 -> passa com OK_RESERVA_FANTASMA
reserva_fantasma = reservado > TOL_CONSUMO
if dry_run:
    return DRY_RUN_OK_RESERVA_FANTASMA if reserva_fantasma else DRY_RUN_OK
# real:
if state_apos == 'cancel':
    return OK_RESERVA_FANTASMA if reserva_fantasma else EXECUTADO
```

### Novos status canônicos

- `OK_RESERVA_FANTASMA` / `DRY_RUN_OK_RESERVA_FANTASMA` — sucesso com aviso de reserva fantasma (libera reservas sem furo).
- `FALHA_FURO_CONTABIL_REAL` / `DRY_RUN_FALHA_FURO_CONTABIL_REAL` — substitui o antigo `FALHA_FURO_CONTABIL` (mantido como alias deprecated no `_FALHAS` da CLI).

### Modos READ acessórios (§6.b)

`listar_mos(criterio)` e `detalhar_mo(mo_id)` expõem o rótulo `classificacao` por item, derivado da mesma `medir_consumo_mo` v6:

- `SEGURO` (`done = 0` e `reservado = 0`)
- `RESERVA_FANTASMA` (`done = 0` e `reservado > 0`)
- `FURO_REAL` (`done > 0`)

## Onde está codificada a invariante

- `app/odoo/estoque/scripts/mo.py::_STATES_CONSUMO_DONE/RESERVADO` (constantes módulo)
- `app/odoo/estoque/scripts/mo.py::medir_consumo_mo` (refatorada)
- `app/odoo/estoque/scripts/mo.py::cancelar_mo` (passo 4 — guard refinado)
- `app/odoo/estoque/scripts/mo.py::listar_mos` (classifica cada item)
- `app/odoo/estoque/scripts/mo.py::detalhar_mo` (atribui classificacao)

Cobertura pytest: 42 testes em `tests/odoo/services/test_stock_mo_service.py` (29 refatorados + 13 novos). 4 testes específicos para o gotcha:

- `test_medir_consumo_mo_retorna_dict_done_reservado_total` — particionamento por state
- `test_cancelar_mo_falha_furo_contabil_real_done_acima_tol` — bloqueio só por `done`
- `test_cancelar_mo_reserva_fantasma_passa_em_dry_run` — fantasma passa em dry-run
- `test_cancelar_mo_reserva_fantasma_executa_real_sem_furo` — fantasma executa sem furo

## Caso real (origem)

**Cenário**: 343 MOs zumbi pré-2026-05-15 (Skill 4 dry-run em 2026-05-27).

- Guard V1: classificou **29 MOs como FURO** (todas em FB; 28 confirmed/to_close + 1 progress).
- Auditoria caso a caso: **TODAS** as 29 tinham `done = 0`; eram apenas reservas marcadas (assigned/waiting/picked).
- Execução com guard V6 teria classificado as 29 como `OK_RESERVA_FANTASMA` → cancelamento direto via skill sem bypass.
- **Workaround usado** (`/tmp/cancelar_mo_nativo.py` com `action_cancel` direto + audit pré/pós): 28/28 state=cancel; 13.610,765 un de reserva liberadas em 22 quants; 201 MLs unlinkadas; 0 anomalias.
- **Resultado final do batch completo**: 342 MOs canceladas (314 limpas via `--consumo zero` + 28 via workaround). 0 furos.

A v6 codifica o pattern do workaround DENTRO do átomo, eliminando a necessidade de script ad-hoc no futuro.

## Outros lugares que podem ter mesma falha (auditar)

Callers de `medir_consumo_mo` em código externo (se algum tratar o retorno como float):

```bash
grep -rn "medir_consumo_mo\b" app/ scripts/ tests/ --include='*.py'
```

Pós-v6, apenas `cancelar_mos_em_massa` em `mo.py` usa a função. Outros consumidores: usar `medir_consumo_mo_legacy` ou migrar para `dict['total']`.

## Ref

- `app/odoo/estoque/scripts/mo.py:60-72` (constantes states + TOL_CONSUMO)
- `app/odoo/estoque/scripts/mo.py:97-152` (`medir_consumo_mo` v6 + `medir_consumo_mo_legacy`)
- `app/odoo/estoque/scripts/mo.py:155-330` (`cancelar_mo` com guard G-MO-01 v6)
- `app/odoo/estoque/scripts/mo.py:540-650` (`listar_mos` com classificação)
- `tests/odoo/services/test_stock_mo_service.py` (42 pytest verdes)
- `.claude/skills/operando-mo-odoo/SKILL.md` (Contrato + Validação V6)
- `app/odoo/estoque/CLAUDE.md` §6.b (pattern de modos READ em skills WRITE)
- `app/odoo/estoque/fluxos/3.1-cancelar-mo.md` (folha L3 atualizada v6)
- Logs PROD 2026-05-27:
  - `scripts/inventario_2026_05/auditoria/log_skill4_mo_real_20260527_084819.json` (cancel 314 limpas via skill v5 + filtro consumo zero)
  - `/tmp/audit_cancel_mo_20260527_090547.json` (cancel 28 reserva fantasma via workaround pré-v6)
