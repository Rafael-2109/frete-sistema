# Atualizacao Tests — 2026-06-08-1

**Data**: 2026-06-08
**Total**: 3752 coletados / 3752 executados (run completo `--maxfail` desligado)
**Passed**: 3608 | **Failed**: 89 | **Error**: 48 | **Skipped**: 7
**Taxa de sucesso**: 96.50% (3608 / 3745 nao-skipped)
**Tempo total**: 1116.76s (18m36s)

## Resumo

A suite executou ate o fim (3752 testes) e 96.5% passou. As 89 falhas + 48 errors
sao quase TODAS ambientais/reincidentes (schema drift do DB local, residuo de dados,
fixtures binarias ausentes, ARRAY/Postgres em SQLite) e NAO regressoes de codigo. O
unico driver NOVO deste ciclo e a coluna `separacao.equipe_vendas` ausente no Postgres
local (migration nao aplicada — alembic local em `unify_permission_system`, head =
`7e880edbf40a`), que sozinha cascateia 45 falhas em `motos_assai`. Sem correlacao com
o Dominio 4 (Sentry): o D4 deste ciclo nao modificou nenhum arquivo de codigo
(`arquivos_modificados: []`).

> NOTA DE PROCEDIMENTO: o comando do manual (`pytest tests/ -v --tb=short --timeout=60`)
> aborta a ~50% (1888 passed + 4 failed + 1 error em 622s) por causa de `--maxfail=5`
> em `addopts` do `pytest.ini`. Para o run completo foi preciso sobrescrever addopts
> (sem `--maxfail`). Mesma gotcha registrada no ciclo 2026-06-01.

## Distribuicao das Falhas (FAILED + ERROR = 137)

| Modulo | Qtd | Causa-raiz dominante |
|--------|-----|----------------------|
| `tests/motos_assai` | 91 | schema drift `equipe_vendas` (45) + fixtures PDF ausentes (6+) + ARRAY/SQLite + logica FASE |
| `tests/hora` | 35 | residuo `hora_loja_cnpj_key`=11111111000101 (69 hits) — state pollution |
| `tests/resolvedores` | 3 | separacao (provavel `equipe_vendas`) |
| `tests/inventario` | 3 | testes batem fonte ao vivo (drill-down vazio, snapshot Odoo nao-idempotente 123!=1) |
| `tests/custeio` | 2 | residuo `uq_custo_considerado_versao` TEST_C2_010 + app-context margem `{}` |
| `tests/carvia` | 1 | `listar_fretes_divergentes` ausente em ConferenciaService (reincidente 6 ciclos) |
| `tests/audits` | 1 | `doc_audit.py` leva 3m21s > timeout 60s (O(n^2) near-dup, sem `--skip-dup`) |
| `tests/agente` | 1 | `test_correction_loop_fase2::test_promocao_e_idempotente` |

## Causas-Raiz (contagem de hits no log)

- **`column separacao.equipe_vendas does not exist`** — 45 hits. **NOVO no ciclo.**
  Model `Separacao` define `equipe_vendas`; Postgres local NAO tem a coluna. Migration
  pendente (alembic local desatualizado). Toda operacao que espelha separacao em Nacom
  (`separacao_service.py:502`) quebra. Resolve-se com `flask db upgrade` no DB local.
- **`hora_loja_cnpj_key` (11111111000101) duplicado** — 69 hits. Residuo de dados:
  ha 1 row leftover em `hora_loja` no Postgres local (confirmado via query). Suite HORA
  comita fora do savepoint (gotcha `gotcha_testes_hora_residuo`). Reincidente.
- **`SQLiteTypeCompiler has no attribute visit_ARRAY`** — 14 hits. Coluna ARRAY
  (`agent_improvement_dialogue.affected_files`) nao compila em SQLite; alguns testes de
  `carregamento_service_crud` caem no SQLite do `pytest.ini` em vez do Postgres.
- **Fixtures PDF ausentes** — 6+ hits. Diretorio `tests/motos_assai/fixtures/` NAO
  existe localmente (`pedido_voe_exemplo.pdf`, `recibo_motochefe_exemplo.pdf`). Binarios
  nao versionados. Reincidente desde 2026-05-11.
- **`uq_custo_considerado_versao` TEST_C2_010** — 1 hit. Residuo: 2 rows leftover em
  `custo_considerado` no Postgres local (confirmado via query). Reincidente.
- **app-context margem** — `_calcular_margem_bruta` chama `CustoFrete.query` fora de
  app-context no teste -> retorna `{}`. Reincidente.

## Falhas Detalhadas (representativas por categoria)

### tests/motos_assai/* (45 via equipe_vendas) — ex. test_cancelar_separacao_carregada
- **Traceback**: `SeparacaoValidationError: Falha ao espelhar separacao em Nacom:
  (psycopg2.errors.UndefinedColumn) column separacao.equipe_vendas does not exist`
  (`app/motos_assai/services/separacao_service.py:502`)
- **Categoria**: Schema drift do DB local (migration pendente). NAO regressao.
- **Correlacao D4**: Nao.

### tests/hora/test_avaria_service.py (10 ERROR) + test_transferencia_service.py + outros
- **Traceback**: `psycopg2.errors.UniqueViolation: duplicate key value violates unique
  constraint "hora_loja_cnpj_key" DETAIL: Key (cnpj)=(11111111000101) already exists.`
- **Categoria**: Residuo de dados no Postgres local (state pollution). NAO regressao.
  Verificado: `SELECT count(*) FROM hora_loja WHERE cnpj='11111111000101'` = 1.
- **Correlacao D4**: Nao.

### tests/motos_assai/test_carregamento_service_crud.py (14 ERROR)
- **Traceback**: `AttributeError: 'SQLiteTypeCompiler' object has no attribute
  'visit_ARRAY'`
- **Categoria**: Ambiental (ARRAY Postgres em SQLite). NAO regressao.
- **Correlacao D4**: Nao.

### tests/motos_assai/test_qpa_pedido_extractor.py / test_recibo_service.py / test_pedido_service.py (PDF)
- **Traceback**: `FileNotFoundError: ... tests/motos_assai/fixtures/pedido_voe_exemplo.pdf`
  / `AssertionError: Fixture ... ausente` / `Esperava >=50 chassis (canon: 115), veio 0`
- **Categoria**: Fixtures binarias ausentes localmente. NAO regressao.
- **Correlacao D4**: Nao.

### tests/custeio/test_regressao_sprint_1_2.py (2)
- **Traceback**: (1) `IntegrityError uq_custo_considerado_versao (TEST_C2_010, 1)` —
  residuo (2 rows leftover, confirmado via query). (2) `AssertionError: assert
  'margem_bruta' in {}` — `Working outside of application context` em
  `_calcular_margem_bruta`.
- **Categoria**: Residuo + isolamento de teste. NAO regressao.
- **Correlacao D4**: Nao.

### tests/carvia/test_sprint_e_medio.py::TestE8FilaDivergente::test_listar_retorna_lista
- **Traceback**: `AttributeError: 'ConferenciaService' object has no attribute
  'listar_fretes_divergentes'`
- **Categoria**: Teste/codigo divergente — metodo nunca implementado (verificado:
  `ConferenciaService` so tem `calcular_opcoes_conferencia`,
  `_buscar_opcoes_transportadora`, `resumo_conferencia_fatura`). Reincidente 6 ciclos.
  E uma falha de teste genuina (teste aspiracional), nao quebra de funcionalidade.
- **Correlacao D4**: Nao.

### tests/inventario/* (3)
- **Traceback**: `assert 0 == 100` / `assert 0 == 500` (drill-down vazio) e
  `assert 123 == 1` (snapshot Odoo nao-idempotente).
- **Categoria**: Testes batendo fonte de dados ao vivo / DB local vazio. NAO regressao.
- **Correlacao D4**: Nao.

### tests/audits/test_artefato_cli.py::test_doc_audit_report_only_roda
- **Traceback**: `Failed: Timeout (>60.0s) from pytest-timeout`
- **Categoria**: Performance/ambiental. O subprocess `doc_audit.py --report-only --path
  docs/superpowers/specs` leva 3m21s standalone (medido) por scan near-dup O(n^2) sem
  `--skip-dup`. Com o `timeout=300` default do pytest.ini passaria; so o `--timeout=60`
  do procedimento o derruba. NAO regressao.
- **Correlacao D4**: Nao.

## Correlacao com Dominio 4 (Sentry)

NENHUMA. O `dominio-4-status.json` deste ciclo registra `arquivos_modificados: []` —
a triagem Sentry nao alterou codigo (apenas docs). As 4 falhas reais de teste/codigo
(carvia `listar_fretes_divergentes`, custeio app-context margem, inventario fonte-viva)
sao independentes e reincidentes de ciclos anteriores, sem relacao com o D4.

## Metricas

- Taxa de sucesso: 96.50% (3608 / 3745 nao-skipped) ou 96.16% sobre o total coletado
- Tempo total: 1116.76s (18m36s)
- Testes coletados: 3752 (+1178 vs 2026-06-01 que coletou 2574)
- Top lentos: `doc_audit_report_only` (60s timeout), `doc_audit_enforce_new` (20.3s),
  `sped_audit` e2e (~9.6s), `gerindo_agente_snapshots` (~7-8s cada)

## Working Tree (contexto)

`git status` traz 4 arquivos modificados em `app/estoque/transferencia_estoque*` +
`tests/estoque/test_transferencia_estoque_routes.py`. Nenhuma das 137 falhas toca
`tests/estoque/` — as mudancas locais nao introduziram nem mascararam falhas.

## Acoes Recomendadas (nao executadas — fora de escopo do test runner)

1. `flask db upgrade` no Postgres local para criar `separacao.equipe_vendas` (elimina ~45-48 falhas motos_assai/resolvedores).
2. Limpar residuo local: `hora_loja` cnpj 11111111000101 + `custo_considerado` TEST_C2_010 (elimina ~70 errors HORA + 1 custeio).
3. Versionar/gerar fixtures de `tests/motos_assai/fixtures/` (elimina 6+ falhas extractor).
4. Tratar isolamento das suites HORA/motos_assai (commit fura savepoint) — gotcha cronico.
