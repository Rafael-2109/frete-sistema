# Atualizacao Tests — 2026-06-15-1

**Data**: 2026-06-15
**Total coletado**: 4329 tests (+577 vs 2026-06-08 que coletou 3752)
**Executados (registrados no log)**: 676 PASSED | 0 FAILED | 0 ERROR | 0 SKIPPED
**Taxa de sucesso (sobre o executado)**: 100% (676/676) — **run NAO concluido**
**Tempo total**: indeterminado (run interrompido ~15%, sem linha de sumario)

## Resumo

A suite foi disparada em background com `addopts` sobrescrito (sem `--maxfail`,
conforme gotcha cronica) e coletou 4329 itens. O processo pytest foi **encerrado
antes de concluir**: o log (`/tmp/manutencao-2026-06-15/pytest-d5-output.log`,
76908 bytes, finalizado 10:22) para em **15% de progresso**, com a ultima linha
cortada no meio de um teste (`test_signature_fallback_organico.py::test_correcao_sem_signature_recebe_assinatura_gerada`,
sem veredicto PASSED/FAILED). Nao existe a linha de sumario final do pyted
(`X passed, Y failed ... in Ns`) nem secao "short test summary info" no arquivo.
Dos 676 testes que chegaram a registrar veredicto, **TODOS passaram (0 falhas,
0 errors, 0 skips)**. Como nao ha como inferir o resultado dos ~3653 testes que
nao chegaram a rodar, este ciclo e classificado **PARCIAL**: a suite executou,
mas foi interrompida — NAO ha evidencia de regressao nem de aprovacao total.

## Por que o run nao concluiu

- O pytest rodou em background (`run_in_background`). A sessao/turno do agente
  encerrou e o `EXIT_CODE=` que seria gravado pelo `echo` encadeado **nunca foi
  escrito** — sinal de que o processo foi morto, nao que terminou normalmente.
- Confirmacao: nenhum processo pytest ativo no momento da retomada; log estatico
  em 76908 bytes desde 10:22; ultima linha truncada sem `\n` final.
- O ciclo 2026-06-08 (referencia) levou **18m36s** para 3752 testes; com +577
  testes coletados, o tempo esperado e ~21min. O log foi cortado bem antes disso.

## Falhas Detalhadas

NENHUMA falha registrada no trecho executado (676 PASSED, 0 FAILED, 0 ERROR).
Os modulos cobertos ate 15% foram exclusivamente `tests/agente/*` (config,
services: capability_registry, error_signature_helper, ontology_bootstrap,
pattern_analyzer, regression_gate, routing, signature_fallback, etc.) — todos
verdes. As areas que historicamente concentram as falhas ambientais/reincidentes
(`tests/motos_assai`, `tests/hora`, `tests/inventario`, `tests/custeio`,
`tests/carvia`) **nao foram alcancadas** antes do corte, portanto seu status
deste ciclo e DESCONHECIDO.

> Expectativa baseada em ciclos anteriores (NAO verificada neste run): as falhas
> de 2026-06-08 (137 = 89 FAILED + 48 ERROR) eram quase todas ambientais —
> schema drift `separacao.equipe_vendas`, residuo `hora_loja_cnpj_key`,
> ARRAY/SQLite, fixtures PDF ausentes — sem regressao de codigo. Provavel que
> persistam, mas isso so se confirma com um run completo.

## Correlacao com Dominio 4 (Sentry)

NENHUMA (correlacoes_d4 = 0). O `/tmp/manutencao-2026-06-15/dominio-4-status.json`
registra `arquivos_modificados: []` e `issues_corrigidas: 0` — a triagem Sentry
deste ciclo nao alterou nenhum arquivo de codigo (a unica issue tecnica real, XZ
TypeError float-Decimal em `carvia/faturas_cliente/detalhe.html`, ja estava
corrigida em main por commit anterior; D4 apenas marcou resolved no Sentry, 0
mudanca de codigo). Logo nao ha como nenhuma falha de teste se correlacionar com
o D4 — alem de nenhuma falha ter sido registrada no trecho executado.

## Metricas

- Taxa de sucesso sobre o executado: 100% (676/676), mas cobertura = ~15.6% do
  coletado (676/4329) — **NAO representativa da suite**.
- Tempo total: indeterminado (run morto antes do sumario final).
- Testes coletados: 4329 (+577 vs 2026-06-08).
- Gotcha de procedimento (reincidente, 3o ciclo): `pytest.ini` tem `--maxfail=5`
  em `addopts` — run completo exige `-o addopts=""`. Aplicado corretamente.

## Working Tree (contexto)

`git status` traz ~18 arquivos modificados, TODOS docs/CLAUDE.md/references de
outros dominios deste mesmo ciclo de manutencao (`.claude/atualizacoes/*/historico.md`,
`.claude/references/*.md`, `CLAUDE.md`, `app/*/CLAUDE.md`, `docs/superpowers/specs/INDEX.md`).
Nenhuma mudanca toca `app/` (codigo) nem `tests/` — nao podem introduzir nem
mascarar regressao de teste.

## Acoes Recomendadas (nao executadas — fora de escopo do test runner)

1. **Re-executar a suite completa em foreground ou com monitoramento ativo do
   PID** para obter resultado representativo (este run foi truncado a 15%).
2. Garantir que o processo background nao seja morto no fim do turno — usar wait
   explicito ate o `EXIT_CODE=` aparecer no log antes de encerrar.
3. Aplicar as correcoes ambientais cronicas antes do proximo run completo
   (`flask db upgrade` para `separacao.equipe_vendas`; limpar residuo
   `hora_loja` cnpj 11111111000101 e `custo_considerado` TEST_C2_010; versionar
   fixtures `tests/motos_assai/fixtures/`).
