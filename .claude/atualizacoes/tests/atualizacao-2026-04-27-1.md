# Atualizacao Tests — 2026-04-27-1

**Data**: 2026-04-27
**Total**: 737 tests
**Passed**: 735 | **Failed**: 2 | **Error**: 0 | **Skipped**: 0
**Taxa de sucesso**: 99.73%
**Status**: PARCIAL (sandbox bloqueou `.claude/atualizacoes/tests/`, relatorio salvo em `/tmp/manutencao-2026-04-27/`)

## Resumo

Suite pytest executou 737 testes em 102.19s com 735 passed e 2 failed (99.73%). As duas falhas estao concentradas em `tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao` (Caso B: VERIFICACAO) — o `patch('app.db')` nao intercepta corretamente o uso de `db` dentro de `verificar_ctrc_cte_comp_job`, fazendo o worker chamar o SSW real e retornar `CAR-164-3` (CTRC vivo no SSW) em vez do mock `CAR-113-9`. Crescimento de +168 testes desde 2026-04-20 (era 569). Sem correlacao com D4 (Sentry), que modificou apenas `app/portaria/`.

## Ambiente

- Python (.venv) + pytest com `--timeout=60`
- Plugins ativos: timeout, asyncio
- Tempo total: 102.19s

## Falhas Detalhadas

### test_ctrc_confirmado_retorna_ok (tests/carvia/test_a3_ctrnc_cte_comp.py)

- **Linha**: 202
- **Assertion**: `assert resultado['status'] == 'OK'` -> recebido `'CORRIGIDO'`
- **Traceback**:
  ```
  tests/carvia/test_a3_ctrnc_cte_comp.py:202: in test_ctrc_confirmado_retorna_ok
      assert resultado['status'] == 'OK'
  AssertionError: assert 'CORRIGIDO' == 'OK'
    - OK
    + CORRIGIDO
  ```
- **Causa raiz**: O teste mocka `resolver_ctrc_ssw` para retornar `None` (sem divergencia) mas tambem mocka `app.db` com `patch('app.db')`. O worker `verificar_ctrc_cte_comp_job` aparentemente ignora o mock `resolver_ctrc_ssw` (ou o caminho de import nao casa com o callsite real) e executa contra o SSW real via `consultar_ctrc_101` — logs mostram `CTe Comp 42 — CTRC corrigido CAR-110-9 -> CAR-164-3, pdf=mantido (via 101 --cte 161)`. Como o SSW retorna `CAR000164-3` divergente do mock `CAR-110-9`, o resultado vira `CORRIGIDO`.
- **Correlacao D4**: Nao — D4 modificou `app/portaria/models.py` e `app/portaria/routes.py`. Falha esta em `app/carvia/workers/verificar_ctrc_ssw_jobs.py`.

### test_ctrc_divergente_corrigido (tests/carvia/test_a3_ctrnc_cte_comp.py)

- **Linha**: 226
- **Assertion**: `assert resultado['ctrc_novo'] == 'CAR-113-9'` -> recebido `'CAR-164-3'`
- **Traceback**:
  ```
  tests/carvia/test_a3_ctrnc_cte_comp.py:226: in test_ctrc_divergente_corrigido
      assert resultado['ctrc_novo'] == 'CAR-113-9'
  AssertionError: assert 'CAR-164-3' == 'CAR-113-9'
    - CAR-113-9
    + CAR-164-3
  ```
- **Causa raiz**: Mesmo problema do teste anterior. Mock de `resolver_ctrc_ssw` configurado para retornar `'CAR-113-9'` (divergencia esperada) mas o worker executa SSW real e retorna `CAR000164-3` (formato real do SSW), batendo no `ctrc_novo` errado.
- **Correlacao D4**: Nao — mesma justificativa.

## Diagnostico

Ambas as falhas tem a mesma origem: o `patch('app.carvia.services.cte_complementar_persistencia.resolver_ctrc_ssw')` nao esta interceptando a chamada real dentro de `verificar_ctrc_cte_comp_job`. O worker importa `resolver_ctrc_ssw` em outro modulo/contexto (provavelmente `app.carvia.workers.verificar_ctrc_ssw_jobs` faz import direto e o `patch` aponta pro local errado), entao a chamada real ao SSW acontece via `consultar_ctrc_101`. Isso e bug de patching path no proprio teste — nao regressao de codigo de producao, mas mascara o teste real.

## Acao Recomendada

Ajustar `patch` para apontar ao caminho onde `resolver_ctrc_ssw` e USADO (no worker), nao onde e definido. Tipicamente:
- Trocar `patch('app.carvia.services.cte_complementar_persistencia.resolver_ctrc_ssw')`
- Por `patch('app.carvia.workers.verificar_ctrc_ssw_jobs.resolver_ctrc_ssw')` (ou caminho equivalente onde o worker importa o symbol).

## Cobertura dos 737 testes

- `tests/agente/` — routes, models, SDK, hooks, pattern analyzer, memory injection
- `tests/carvia/` — A1/A2 linking, A3 CTRNC CTe complementar (2 falhas Caso B)
- `tests/chat/` — routes, stream, smoke, users eligible
- `tests/financeiro/` — CNAB, DAC, parcela utils
- `tests/hora/` — Lojas Motochefe (B2C)
- `tests/pallet/` — devolucoes, vinculacoes
- `tests/pessoal/`
- `tests/test_cte_evento_parser.py`
- `tests/test_graph_client.py`

## Testes Mais Lentos (top 10)

| # | Tempo | Teste |
|---|-------|-------|
| 1 | 22.44s | TestCasoBVerificacao::test_ctrc_confirmado_retorna_ok (FALHOU) |
| 2 | 21.38s | TestCasoBVerificacao::test_ctrc_divergente_corrigido (FALHOU) |
| 3 | 6.49s | TestSugestaoVinculacao::test_rejeitar_sugestao |
| 4 | 5.53s | TestSugestaoVinculacao::test_confirmar_sugestao |
| 5 | 1.73s | test_top_subagents_by_cost_aggregates_correctly |
| 6 | 1.28s | test_smoke_e2e_fluxo_completo |
| 7 | 1.23s | test_lista_elegiveis_exclui_self |
| 8 | 1.15s | test_build_user_rules_escapes_xml_special_chars_in_path |
| 9 | 1.14s | test_unread_endpoint_zero |
| 10 | 1.12s | test_send_message_via_route |

> Os 2 testes mais lentos sao justamente os que falham — o tempo extra (~22s cada) e gasto chamando o SSW real via Playwright, confirmando o diagnostico de patch path errado.

## Correlacao D4

**Nao aplicavel**. D4 (Sentry Triage) modificou apenas `app/portaria/models.py` e `app/portaria/routes.py` (cast Integer->String em `ilike` de `Embarque.numero`). As 2 falhas estao em `app/carvia/workers/verificar_ctrc_ssw_jobs.py` — dominio totalmente distinto. Nenhum teste de portaria esta na suite (modulo nao tem cobertura de testes ainda).

## Metricas

- Taxa de sucesso: **99.73%** (735/737)
- Tempo total: **102.19s**
- Crescimento vs 2026-04-20: **+168 testes** (de 569 para 737)
- Falhas novas: **2** (mesmo arquivo, mesma causa raiz)
