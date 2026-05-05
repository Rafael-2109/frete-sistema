# Atualizacao Tests — 2026-05-05-1

**Data**: 2026-05-05
**Total**: 766 tests
**Passed**: 749 | **Failed**: 17 | **Error**: 0 | **Skipped**: 0
**Taxa de sucesso**: 97.78%
**Tempo total**: 96.13s (1m36s)

## Resumo

Suite executou ate o fim apos override do `--maxfail=5` configurado em `pyproject.toml` (rodada com `--maxfail=1000`). 17 falhas concentradas em DUAS causas: (1) **15 falhas em `tests/hora/test_pedido_workflow.py`** por coluna `modalidade_frete` ausente em `hora_venda` no banco LOCAL — migration `hora_21_venda_modalidade_frete_parcelas.sql` ainda nao aplicada localmente (migration ja foi pra producao via commit `8c6a483a`); (2) **2 falhas em `tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao`** — patch path incorreto do `resolver_ctrc_ssw` faz worker chamar SSW REAL em vez de mock (mesma falha do ciclo 2026-04-27, NAO foi corrigida). Sem correlacao com D4 (D4 tocou apenas `app/templates/hora/base.html`, sem relacao com schema ou worker carvia).

## Falhas Detalhadas

### Grupo A: tests/hora/test_pedido_workflow.py — 15 falhas (schema desatualizado local)

Todas as 15 falhas tem o mesmo erro raiz:

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn)
column "modalidade_frete" of relation "hora_venda" does not exist
```

Testes afetados:
- `test_criar_venda_manual_cria_cotacao_e_reserva_chassi`
- `test_criar_pedido_chassi_indisponivel_falha`
- `test_confirmar_venda_transiciona_para_confirmado`
- `test_confirmar_venda_ja_confirmada_falha`
- `test_cancelar_venda_cotacao_devolve_chassi`
- `test_cancelar_venda_motivo_curto_falha`
- `test_cancelar_venda_idempotente`
- `test_editar_observacoes_em_qualquer_status_exceto_cancelado`
- `test_editar_cliente_em_confirmado_falha`
- `test_editar_cancelado_falha`
- `test_adicionar_item_em_cotacao`
- `test_adicionar_item_em_confirmado_falha`
- `test_remover_item_devolve_chassi`
- `test_remover_ultimo_item_falha`
- `test_editar_item_troca_chassi`

**Diagnostico**: o modelo `app/hora/models/venda.py` declara `modalidade_frete VARCHAR(1)` mas a migration `scripts/migrations/hora_21_venda_modalidade_frete_parcelas.sql` (introduzida no commit `8c6a483a`) nao foi aplicada no banco LOCAL (provavelmente foi aplicada apenas no Render). O `conftest.py` parece reusar o banco existente em vez de recriar do zero.

**Correlacao D4**: Nao. D4 modificou apenas `app/templates/hora/base.html` (template). Schema e codigo de servico HORA nao foram tocados.

**Fix sugerido**: rodar migration local:
```bash
psql $DATABASE_URL_LOCAL -f scripts/migrations/hora_21_venda_modalidade_frete_parcelas.sql
```
ou executar o equivalente Python.

### Grupo B: tests/carvia/test_a3_ctrnc_cte_comp.py — 2 falhas (mock SSW bypass)

**test_ctrc_confirmado_retorna_ok**
- **Assertion**: `assert 'CORRIGIDO' == 'OK'`
- **Tempo**: 22.09s (chamada SSW real via Playwright)
- **Saida real do worker**: `verificar_ctrc_cte_comp_job: CTe Comp 42 — CTRC corrigido CAR-110-9 -> CAR-164-3, pdf=mantido (via 101 --cte 161)`

**test_ctrc_divergente_corrigido**
- **Assertion**: `assert 'CAR-164-3' == 'CAR-113-9'`
- **Tempo**: 21.77s (chamada SSW real via Playwright)
- **Diagnostico**: o teste esperava que `resolver_ctrc_ssw` fosse mockado para retornar `CAR-113-9`, mas o mock NAO foi aplicado e o worker consultou o SSW real (retornando `CAR-164-3`, dado vivo). Mesmo problema documentado no ciclo `2026-04-27-1`. Patch path incorreto persiste.

**Correlacao D4**: Nao. D4 nao tocou `app/carvia/workers/verificar_ctrc_ssw_jobs.py` nem o teste.

**Fix sugerido**: revisar o `monkeypatch.setattr(...)` do teste — patch path provavelmente deveria mockar o `resolver_ctrc_ssw` no namespace do worker (`app.carvia.workers.verificar_ctrc_ssw_jobs.resolver_ctrc_ssw`) em vez do modulo origem.

## Metricas

- Tempo total: 96.13s
- Suite size: 766 tests (vs 737 em 2026-04-27, +29 testes; vs 569 em 2026-04-20)
- Taxa: 97.78% (queda de 99.73% para 97.78%, regressao causada por schema local desatualizado)
- Tests mais lentos: `test_ctrc_confirmado_retorna_ok` (22.09s), `test_ctrc_divergente_corrigido` (21.77s) — ambos batendo SSW real
- Maxfail: forcado override `--maxfail=1000` (config `pyproject.toml` tem `--maxfail=5`)

## Observacoes

- **Ruido nao-fatal**: erro de logging `ValueError: I/O operation on closed file` no shutdown do interpreter (pytest finalizacao). Nao afeta resultados, apenas poluicao no stderr.
- **Cache prejudicial**: rodar com `-p no:cacheprovider` foi necessario para o segundo run nao reordenar pelas falhas anteriores e voltar a parar em 5.
- **Falhas Grupo A nao sao bug de codigo** — sao deficit de migration no banco local. Em producao (Render) os mesmos testes passariam.
- **Falhas Grupo B sao bug real de teste** — mocks incorretos permitem chamadas SSW de producao a partir do test runner local.
