---
name: operando-mo-odoo
description: >-
  Skill WRITE (átomo C2) para CANCELAR Ordens de Produção (mrp.production)
  no Odoo: cancelar single ou batch por critério (filtros de data, states,
  empresas, consumo). Default seguro: bloqueia MOs com consumo > 0 (G-MO-01
  = furo contábil); operador deve usar mrp.unbuild via fluxo cross-skill
  para reverter consumo. Usar quando o pedido é "cancela MO X", "cancela
  MOs zumbi antigas FB/CD", "limpa MOs draft/confirmed sem consumo",
  "cancela MO travada (mas com consumo=0)". `--dry-run` é o DEFAULT;
  só efetiva com `--confirmar`.
  NÃO USAR PARA:
  - cancelar MO COM consumo (gera furo) -> use mrp.unbuild via cross-skill
    (ver memória [[reaproveitar-semiacabado-orfao-mo-cancelada]])
  - criar MO nova -> sem demanda real isolada (pipeline cria via Odoo)
  - alterar MO (mover componente, ajustar qty) -> fluxo cross-skill
    (Skill 2 transfer + write em stock.move; ver
    [[mo_componente_local_consumo]])
  - cancelar PICKING (não é MO) -> operando-picking-odoo
  - cirurgia/MLs órfãs -> operando-reservas-odoo
  - só consultar MOs (não altera) -> consultando-sql
allowed-tools: Read, Bash, Glob, Grep
---

# operando-mo-odoo (WRITE — átomo C2)

Skill **mínimo viável** (C1-C5 implementados, C6-C10 conforme uso). Construída em 2026-05-24 v5 a partir de demandas reais documentadas:

- **Cancelamento periódico de MOs antigas/zumbi** em FB e CD (caso real 2026-05-20: 120 MOs zumbi 2024-2025 canceladas via `cancelar_mos.py` / `14_cancelar_mos_antigas_fb.py`).
- **Guard G-MO-01**: scripts-fonte já bloqueavam cancelamento de MOs com consumo > 0 (preserva integridade contábil — componentes consumidos sem produto finalizado = furo).
- **Idempotência action_cancel**: validada AO VIVO 2026-05-24 em MO já cancelada (retorna `True` sem erro, state continua 'cancel').

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/mo.py` (StockMOService — criado do zero, sem service legado em `services/`; shim preventivo criado em `app/odoo/services/stock_mo_service.py`).

---

## REGRAS CRÍTICAS

1. **`--dry-run` é o DEFAULT.** Sem `--confirmar`, só calcula e mostra o plano (exit 4).
2. **G-MO-01 (FURO CONTÁBIL) é INVIOLÁVEL** por default — service retorna `FALHA_FURO_CONTABIL` para qualquer MO com consumo > 0.0001. CLI V1 **NÃO expõe** `--forcar-consumo` (parâmetro do service mantido apenas para auditoria/pipelines internos).
3. **Para MO COM consumo (e precisa reverter)**: usar `mrp.unbuild` via fluxo cross-skill — devolve componentes aos lotes originais (ver [[reaproveitar-semiacabado-orfao-mo-cancelada]] §3).
4. **`action_cancel` é IDEMPOTENTE** em MO state='cancel' (retorna True sem erro, state continua 'cancel') — atomo retorna `NOOP` sem chamar Odoo novamente.
5. **`action_cancel` NÃO funciona** em MO state='done' (não tem como reverter sem unbuild) — atomo retorna `FALHA_STATE_NAO_CANCELAVEL`.
6. **Cancelamento libera automaticamente** as reservas dos componentes (Odoo cascade). Se sobrar quant.reserved residual stale → chamar Skill 2.4 `zerar_reserved_residual` (regra inviolável 9 — pattern do orquestrador).

## Contrato — `cancelar` (átomo único V1)

```
objeto:        mrp.production (cascateia para stock.move + stock.move.line via action_cancel)
input:         --modo cancelar --mo-id <id> [--motivo "..."]
                 OU --modo cancelar (batch — todos os filtros)
                    [--create-de YYYY-MM-DD] [--create-ate YYYY-MM-DD]
                    [--states draft,confirmed,progress,to_close]
                    [--empresas 1,4,5]
                    [--consumo zero|qualquer]   (default zero = bloqueia G-MO-01)
                    [--limite N]
                    [--motivo "..."]
output (JSON): single  : {status, mo_id, name, state_antes, state_apos,
                          consumo_total, motivo, tempo_ms, acao, erro?}
               batch   : {criterio, total_pre_filtro, total_candidatas,
                          total_filtradas_por_consumo, contagem_status,
                          resultados:[<single>...], tempo_total_ms}
pré-condições: MO existe; state IN (draft, confirmed, progress, to_close)
               (se state='cancel': NOOP; se state='done': falha)
               consumo_total <= 0.0001 (G-MO-01 — bloqueio default)
pós-condições: MO.state='cancel'; moves filhas state='cancel';
               MLs filhas removidas; quant.reserved_quantity recalculado
                (Odoo cascade automático)
gotchas-invariante:
  G-MO-01 consumo > 0 = FURO CONTÁBIL → FALHA_FURO_CONTABIL (default seguro;
          mensagem sugere mrp.unbuild via fluxo cross-skill)
  G-MO-02 manual_consumption não reserva via action_assign → NÃO relevante
          para cancelar (action_cancel ignora reservas/picked)
  G-MO-03 componente em local errado → NÃO relevante para cancelar
  G-MO-04 picked=True em to_close/done → herdado de Skill 2.4 G026
          (action_cancel é seguro com picked — não mexe em quants existentes)
  G019-like: SEMPRE re-le state pós action_cancel; raise não é raise (retorna
             FALHA_STATE_INESPERADO), pois action_cancel pode falhar
             silenciosamente em casos extremos (MO referenciada por outra em
             produção, lock pessimista, regra customizada)
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        EXECUTADO · NOOP · DRY_RUN_OK · DRY_RUN_NOOP ·
               FALHA_FURO_CONTABIL · DRY_RUN_FALHA_FURO_CONTABIL ·
               FALHA_STATE_NAO_CANCELAVEL · DRY_RUN_FALHA_STATE_NAO_CANCELAVEL ·
               FALHA_STATE_INESPERADO · FALHA
```

## Receitas (caso real → args)

| Preciso de... | Modo | Args |
|---------------|------|------|
| Cancelar 1 MO específica (zumbi reportada) | single | `--modo cancelar --mo-id 19713 --motivo "zumbi 2025" --confirmar` |
| Cancelar todas zumbi FB 2024-2025 sem consumo | batch | `--modo cancelar --create-de 2024-01-01 --create-ate 2026-01-01 --empresas 1 --states draft,confirmed,progress,to_close --consumo zero --confirmar` |
| Cancelar MOs antigas FB/CD em massa (cuidado) | batch | `--modo cancelar --create-ate 2025-06-01 --empresas 1,4 --consumo zero --confirmar` |
| Canary (1 MO antes de batch) | batch | `--modo cancelar --create-ate 2025-06-01 --empresas 1 --consumo zero --limite 1 --confirmar` |
| Dry-run prévio (ver quantas seriam canceladas) | batch dry | `--modo cancelar --create-ate 2025-06-01 --empresas 1` (sem `--confirmar` = dry-run) |
| Tentar cancelar MO com consumo → bloqueia | single | `--modo cancelar --mo-id 19850` (consumo>0 → FALHA_FURO_CONTABIL) |

## Catálogo de átomos

| Átomo | Status | Demanda real |
|---|---|---|
| `cancelar_mo(mo_id, motivo, forcar_consumo, consumo_total, dry_run)` | ✅ implementado (StockMOService.cancelar_mo) | Caso real 2026-05-20 (120 MOs zumbi canceladas) |
| `cancelar_mos_em_massa(criterio, max_n, motivo, dry_run)` | ✅ implementado (StockMOService.cancelar_mos_em_massa) | Pattern de `cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` |
| `medir_consumo_mo(mo_ids)` | ✅ implementado (helper batch chunks 200) | Usado por guard G-MO-01 e por cancelar_mos_em_massa para filtro |
| `criar_mo(...)` | ⬜ NÃO previsto | Sem demanda real isolada (pipeline cria via Odoo) |
| `alterar_mo(...)` | ⬜ NÃO previsto | Caso real PROD existe (mover componente, substituir qty) MAS é fluxo cross-skill (Skill 2 transfer + write em stock.move). Ver [[mo_componente_local_consumo]] e [[reaproveitar-semiacabado-orfao-mo-cancelada]]. Implementar como FOLHA de fluxo (3.2.x), NÃO como átomo, se padrão se repetir 2+ casos. |
| `mrp_unbuild(mo_id, ...)` | ⬜ NÃO previsto | Fluxo cross-skill — caso real existe (reverter MO done) mas não é átomo isolado da Skill 4. Implementar separadamente se houver demanda. |

## Composição em FLUXOS

- **Fluxo 3.1.a — cancelar MO única (zumbi reportada)**:
  1. Identificar MO via Skill 9 (`consultando-quant-odoo` + investigação manual mrp.production).
  2. Confirmar state IN (draft/confirmed/progress/to_close) E consumo_total = 0.
  3. `operar_mo.py --modo cancelar --mo-id X --motivo "..." --confirmar`.
  4. Verificar no Odoo UI: MO state='cancel', moves filhas state='cancel', componentes liberados.
  5. **Se** havia reservas pré-cancel + alguma ML órfã sobrar → Skill 2.4 `zerar_reserved_residual` nos quant_ids afetados (regra inviolável 9).

- **Fluxo 3.1.b — batch zumbi antigas** (pattern 2026-05-20, 120 MOs):
  1. Definir critério (ex.: empresas=[1,4], create_ate='2025-06-01', states ativos, consumo=zero).
  2. Dry-run: `operar_mo.py --modo cancelar [filtros]` → vê quantas seriam canceladas + filtro de consumo.
  3. Revisar lista de MOs (log JSON dry-run); confirmar que não há MOs ativas conhecidas (excluir via `--empresas` ou outro filtro).
  4. Canary: rodar com `--limite 1 --confirmar` em 1 MO; verificar resultado direto no Odoo.
  5. Batch completo: `operar_mo.py --modo cancelar [filtros] --confirmar`.
  6. Verificar no Odoo UI: critério retorna 0 candidatas após batch (idempotente).

- **Fluxo 3.1.c — MO com consumo (NÃO COBERTO por esta skill)**:
  - DELEGAR para fluxo cross-skill `mrp.unbuild` (sem skill ainda). Ver memória [[reaproveitar-semiacabado-orfao-mo-cancelada]] para procedimento manual XML-RPC: criar `mrp.unbuild` com `mo_id` definido → `action_unbuild` → componentes voltam aos lotes originais automaticamente.

## Armadilhas

- **`action_cancel` em MO state='cancel' retorna True** (idempotente). Validado AO VIVO 2026-05-24 (FB/OP/BALDE/00009 id=4192). Service trata como `NOOP` sem chamar Odoo novamente (economiza RPC).
- **`action_cancel` em MO state='done' não funciona**. Service retorna `FALHA_STATE_NAO_CANCELAVEL` sem chamar Odoo — mensagem sugere `mrp.unbuild` via fluxo cross-skill.
- **`stock.move.action_cancel` NÃO existe** via XML-RPC (`_action_cancel` é privado). Cancelar MO via `mrp.production.action_cancel` é o caminho correto (cascade automático para moves + MLs).
- **`qty_produced` é o produto acabado finalizado, NÃO componentes consumidos.** Validado AO VIVO 2026-05-24 (MOs com qty_produced=0 e consumo_total>0 são comuns). Para guard G-MO-01, medimos `stock.move.quantity` (raw materials != cancel), não `qty_produced`.
- **Tolerância TOL_CONSUMO=0.0001** (mesma dos scripts-fonte). Consumos abaixo são tratados como zero (rounding errors do Odoo: 6 decimais).
- **Cuidado com MOs em state='progress'**: cancelar MO em produção ATIVA é perigoso (operador no chão de fábrica pode estar apontando). Default `--states draft,confirmed,progress,to_close` inclui progress por consistência com scripts-fonte, MAS recomenda-se filtrar para `confirmed,draft` em batches grandes (zumbis antigas raramente estão em progress real — geralmente são órfãs do MRP).
- **MOs de SEMI-ACABADO multi-nível**: cancelar MO de acabado pode deixar MO de semi órfã (caso real [[reaproveitar-semiacabado-orfao-mo-cancelada]]). Esta skill NÃO trata isso — operador valida manualmente após cancel; se semi gerou estoque órfão, abrir caso de unbuild ou consumo via outra MO.
- **picked=True em to_close/done**: action_cancel é seguro nesse cenário (não mexe em quants existentes — só marca state='cancel'). G-MO-04 herdado de Skill 2.4 G026.

## Exemplos

```bash
SK=.claude/skills/operando-mo-odoo/scripts/operar_mo.py

# 1) Dry-run: cancelar 1 MO específica (ver plano antes)
python "$SK" --modo cancelar --mo-id 19713

# 2) Efetivar cancelamento de 1 MO
python "$SK" --modo cancelar --mo-id 19713 --motivo "zumbi 2025" --confirmar

# 3) Dry-run batch: quantas MOs FB ativas pré-2025-06 sem consumo?
python "$SK" --modo cancelar \
  --create-ate 2025-06-01 --empresas 1 --consumo zero

# 4) Canary: cancelar 1 MO do batch (testar real)
python "$SK" --modo cancelar \
  --create-ate 2025-06-01 --empresas 1 --consumo zero \
  --limite 1 --confirmar

# 5) Batch completo (cuidado!)
python "$SK" --modo cancelar \
  --create-ate 2025-06-01 --empresas 1 --consumo zero \
  --motivo "limpeza zumbi 2024-2025" --confirmar

# 6) Tentar cancelar MO COM consumo (esperado: FALHA_FURO_CONTABIL)
python "$SK" --modo cancelar --mo-id 19850

# 7) Idempotência: cancelar MO já cancelada (esperado: NOOP)
python "$SK" --modo cancelar --mo-id 4192 --confirmar
```

## Validação

Skill **construída em 2026-05-24 v5**:
- C1: 2 scripts-fonte minerados integral (`cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py`). Investigação AO VIVO via `/tmp/investigar_mos_skill4.py` (10.000 MOs FB / 17 CD / 3367 LF; estrutura mrp.production validada; idempotência action_cancel confirmada em FB/OP/BALDE/00009).
- C2: service `app/odoo/estoque/scripts/mo.py` (NOVO — sem service legado) com shim em `services/stock_mo_service.py`. **29 testes pytest verdes** cobrindo todos os cenários (caminho feliz, NOOP idempotente, guard G-MO-01 default + bypass, state='done', state inesperado pós-cancel, exceção genérica, dry-run, helpers medir_consumo_mo, cancelar_mos_em_massa com filtros/limite/FIFO).
- C3: contrato 1 átomo único (`cancelar_mo` + composição `cancelar_mos_em_massa`) definido.
- C4: SKILL.md com receitas, 3 fluxos (3.1.a/b/c), armadilhas, exemplos.
- C5: `scripts/operar_mo.py` (CLI single OU batch, --dry-run default, exit codes 0/1/2/4).
- C6: validação dry-run vs Odoo PROD em 4 casos (idempotência NOOP, DRY_RUN_OK sem consumo, FALHA_FURO_CONTABIL com consumo=1410, batch FB ate 2025-06 consumo zero limite 5). Log em `/tmp/log_skill4_C6_validacao_dry_run.json`.
- C7-C10: cross-refs + arquivamento `_validados/operando-mo-odoo/` + atualizar ROADMAP.

Mapeamento script-fonte → átomo no `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Resultado da validação em `_validados/operando-mo-odoo/VALIDACAO.md`.
