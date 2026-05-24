# `_validados/operando-mo-odoo/` — scripts SUPERADOS pela Skill 4

Estes scripts ad-hoc foram **superados** pela skill `operando-mo-odoo` em 2026-05-24 v5 (service `app/odoo/estoque/scripts/mo.py`). Permanecem executáveis como **museum vivo** — bate exato com a CLI nova.

**SKILL.md:** `.claude/skills/operando-mo-odoo/SKILL.md`
**CLI:** `.claude/skills/operando-mo-odoo/scripts/operar_mo.py`
**Service:** `app/odoo/estoque/scripts/mo.py` (StockMOService)
**Constituição:** `app/odoo/estoque/CLAUDE.md` (§6 catálogo, §7 invariantes de execução)
**Folha de fluxo:** `app/odoo/estoque/fluxos/3.1-cancelar-mo.md`
**Validação:** `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §10 (criada nesta sessão)

---

## Mapeamento script-fonte → átomo da Skill 4

| Script-fonte | Caso de uso | Substituído por | Mapeamento de args |
|--------------|-------------|------------------|--------------------|
| `cancelar_mos.py` | Cancelar MOs por critério parametrizável (data, states, empresas, consumo) | `cancelar_mos_em_massa(criterio, max_n, motivo, dry_run)` | `--create-de` → `create_de`; `--create-ate` → `create_ate`; `--states` → `states`; `--empresas` → `empresas`; `--consumo` → `consumo`; `--limite` → `max_n`; `--dry-run` → `dry_run=True`; `--confirmar` → `dry_run=False` |
| `14_cancelar_mos_antigas_fb.py` | Cancelar MOs FB confirmed antigas (>6 meses) com MIGRAÇÃO em Pre-Prod, consumo=0 | `cancelar_mos_em_massa(empresas=[1], create_ate=hoje-180d, states=['confirmed'], consumo='zero')` | `--dias-corte 180` → `--create-ate $(date -d '-180 days')`; `--ate-data` → `--create-ate`; `--incluir-qty-done` → `--consumo qualquer` (CUIDADO — bypass G-MO-01) |

---

## Validação C6 (dry-run vs PROD)

**Sessão 2026-05-24 v5** (`/tmp/log_skill4_C6_validacao_dry_run.json`):

| Caso | Args | Status | Exit | Validação |
|------|------|--------|------|-----------|
| C1 | `--mo-id 4192` (FB/OP/BALDE/00009 state=cancel) | `DRY_RUN_NOOP` | 4 | Idempotência confirmada AO VIVO; service não chama Odoo novamente. |
| C2 | `--mo-id 19985` (FB/OP/BALDE/03330 state=confirmed consumo=0) | `DRY_RUN_OK` | 4 | Caminho feliz validado; plano correto. |
| C3 | `--mo-id 19984` (FB/OP/MANUAL/01777-002 state=confirmed consumo=1410.05) | `DRY_RUN_FALHA_FURO_CONTABIL` | 4 | Guard G-MO-01 bloqueia; mensagem sugere mrp.unbuild. |
| C4 | `--create-ate 2025-06-01 --empresas 1 --consumo zero --limite 5` | batch (vazio: 1 pré-filtro, 1 filtrada por consumo, 0 candidatas) | 4 | Filtros funcionam; ordenação FIFO testada via pytest. |

**Execução real `--confirmar` em PROD nesta sessão:** 0 vezes (demanda-driven). Histórico relacionado: 120 MOs zumbi 2024-2025 canceladas em 2026-05-20 via `cancelar_mos.py` original (script-fonte deste validados/ — pattern validado em produção).

---

## Cobertura pytest

`tests/odoo/services/test_stock_mo_service.py` — **29 testes** cobrindo:

- `medir_consumo_mo`: vazio, soma por MO, filtro state != cancel, quantity None.
- `cancelar_mo`: EXECUTADO (caminho feliz), NOOP (idempotente state=cancel), DRY_RUN_NOOP, FALHA_FURO_CONTABIL (G-MO-01), DRY_RUN_FALHA_FURO_CONTABIL, forcar_consumo bypass, consumo <= TOL não bloqueia, FALHA_STATE_NAO_CANCELAVEL (state=done), DRY_RUN_FALHA_STATE_NAO_CANCELAVEL, FALHA_STATE_INESPERADO, FALHA exceção, MO inexistente, DRY_RUN_OK não chama action_cancel, consumo_total passado evita query.
- `cancelar_mos_em_massa`: filtra consumo zero default, consumo qualquer inclui todas (mas guard bloqueia por MO), max_n limite, dry_run não executa, consumo inválido raise, ordenação FIFO por create_date, domain inclui filtros.
- `TOL_CONSUMO` export checked (0.0001).

**Baseline total Skill 4:** 29/29 verdes em 0.78s (3 testes adicionais cobrindo code-review fixes: `mo_deletada_apos_cancel_eh_executado`, `consumo_qualquer_sem_forcar_emite_warning`, `search_read_usa_order_create_date_asc`).

---

## Status

✅ **C9 fechado 2026-05-24 v5**: 2 scripts movidos via `git mv`; sys.path corrigido `parents[2]→parents[4]`; header `[arquivado 2026-05-24 v5]` adicionado mantendo executabilidade.

✅ **C10 fechado**: MAPA_SCRIPTS + ROADMAP_SKILLS atualizados; Skill 4 marcada como 🟡 mín viável.

**Limitação documentada**: cancelar MO COM consumo > 0 (fluxo 3.1.c) NÃO COBERTO pela skill — operador deve usar `mrp.unbuild` via fluxo cross-skill (ver memória `[[reaproveitar-semiacabado-orfao-mo-cancelada]]`). Implementar skill `mrp-unbuild-odoo` se padrão repetir 2+ casos reais.
