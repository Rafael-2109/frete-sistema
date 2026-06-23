# Atualizacao Sentry — 2026-06-22-1

**Data**: 2026-06-22
**Org/Projeto**: `nacom` / `python-flask` (regionUrl `https://us.sentry.io`)
**Issues avaliadas**: 28 (todas `is:unresolved environment:production`)
**Issues corrigidas**: 2 (Y1, Z2)
**Issues ignoradas / fora de escopo**: 26

## Resumo

Triagem das 28 issues nao resolvidas em producao. Dois bugs tecnicos simples
corrigidos com fix minimo e marcados `resolved` no Sentry: **Y1** (str+int em
f-string de conciliacao OFX) e **Z2** (`Decimal` estourando `ConversionSyntax`
ao importar um PDF de Carta de Correcao no endpoint de NF Q.P.A.). O maior
cluster de eventos (YN/YM/YS/YR/YQ/YP, 57 eventos somados) e **uma unica
causa-raiz: migration pendente** `2026_06_16_veiculo_parametros_custo` (coluna
`veiculos.custo_km` + custos) ainda nao aplicada em producao — fora de escopo
(migration). O restante e infra externa (Anthropic billing/overload, Odoo
XML-RPC), output de LLM ja tratado, ou feature incompleta dependente de migration.

## Issues Corrigidas

### PYTHON-FLASK-Y1: TypeError str + int em conciliacao OFX
- **Frequencia**: 2 eventos, 1 usuario (`financeiro.comprovantes_api_upload_ofx`)
- **Causa raiz**: `app/financeiro/services/ofx_vinculacao_service.py:863` montava
  a mensagem de conciliacao pre-existente com `'/' + titulo['parcela']`. O
  `titulo['parcela']` vem do titulo Odoo e e **INTEGER** (gotcha A10 do modulo
  financeiro: `parcela` e VARCHAR em `Contas*` mas INTEGER em `Extrato*`/`Baixa*`
  e nos dicts de titulo). `str + int` -> `TypeError`.
- **Fix**: coercao explicita `str(titulo['parcela'])` na f-string (linha 863).
  Erro handled (logger), nao causava 500, mas abortava a criacao do lancamento
  pre-conciliado.
- **Arquivo**: `app/financeiro/services/ofx_vinculacao_service.py`
- **Sentry**: marcada `resolved` + comentario de rastreio.

### PYTHON-FLASK-Z2: InvalidOperation (ConversionSyntax) em import NF Q.P.A.
- **Frequencia**: 5 eventos, 1 usuario (`motos_assai.faturamento_upload_nf`)
- **Causa raiz**: `app/motos_assai/services/parsers/nf_qpa_adapter.py` fazia
  `Decimal(str(resultado.get('valor_total', 0)))` (e o gemeo em
  `criar_nf_qpa_de_dados`, `Decimal(str(dados.get('valor_total') or 0))`). Quando
  o usuario subiu um **PDF de Carta de Correcao** (`1737 - CARTA DE CORRECAO.pdf`)
  no endpoint de upload de NF, o parser DANFE devolveu um `valor_total`
  nao-numerico (CCe nao tem total de NF) -> `Decimal()` levantou
  `decimal.InvalidOperation` (ConversionSyntax) -> 500.
- **Fix**: helper module-level `_to_decimal_safe(valor, default='0')` que captura
  `InvalidOperation/ValueError/TypeError` e retorna `Decimal('0')` em valor
  invalido/ausente. Aplicado nos 2 call sites (`importar_nf_qpa` linha 357 e
  `criar_nf_qpa_de_dados` linha 159). Com valor 0, o match segue como
  `NAO_RECONCILIADO` em vez de quebrar — comportamento ja esperado para um
  documento que nao e NF. Mantem retrocompat com o `or 0`/`, 0` anteriores e
  blinda o `nf.valor_total / n_veiculos` da distribuicao por veiculo.
- **Arquivo**: `app/motos_assai/services/parsers/nf_qpa_adapter.py`
- **Validacao**: `py_compile` OK; suite inline do helper (None/vazio/numero
  valido/string-lixo/Decimal) OK.
- **Sentry**: marcada `resolved` + comentario de rastreio.

## Issues Fora de Escopo

### Migration pendente `2026_06_16_veiculo_parametros_custo` (CAUSA-RAIZ de 6 issues, 57 eventos)
A migration `scripts/migrations/2026_06_16_veiculo_parametros_custo.{py,sql}`
adiciona `custo_km`, `custo_motorista_dia`, `custo_fixo_dia`, `depreciacao_mensal`
etc. a `veiculos`. O **model** (`app/veiculos/models.py`) e o **schema JSON** ja
declaram as colunas, mas a migration **NAO esta no `build.sh`** e nao foi aplicada
em producao. Resultado:
- **YP** (2 ev, `pedidos.lista_pedidos`) e **YQ** (4 ev, `monitoramento.listar_entregas`):
  `UndefinedColumn: column veiculos_1.custo_km does not exist` — a causa-raiz direta.
- **YN** (36 ev, `portaria.historico`), **YM** (7 ev, `portaria.dashboard`),
  **YS** (4 ev) e **YR** (4 ev, ambos `monitoramento.listar_entregas`):
  `InFailedSqlTransaction` — **cascatas** do mesmo `UndefinedColumn` (a 1a query
  com `custo_km` aborta a transacao; queries seguintes no mesmo request falham).
- **Acao requerida (humano/dev)**: aplicar a migration em producao (e adiciona-la
  ao `build.sh`). NAO corrigida pelo cron (regra: migrations sao fora de escopo).

### Feature incompleta — `cadastro_pendente` em CarviaModeloMoto (YT)
- **YT** (2 ev, `carvia.api_anexar_nf_cotacao`):
  `'cadastro_pendente' is an invalid keyword argument for CarviaModeloMoto`.
- O route `app/carvia/routes/cotacao_v2_routes.py` (linhas 2083/2983) instancia
  `CarviaModeloMoto(..., cadastro_pendente=True)`, mas o **model**
  (`app/carvia/models/config_moto.py`) NAO declara a coluna e o **schema JSON**
  de `carvia_modelos_moto` nao a tem. Existe a migration
  `scripts/migrations/adicionar_placeholder_carvia_cotacao_moto.{py,sql}` que
  adicionaria `cadastro_pendente`, porem nao aplicada + model nunca atualizado.
- **Fora de escopo**: nao e null/type/import simples — exige aplicar migration
  **e** mapear a coluna no model (completar feature). Documentado para o dev.

### Output de LLM ja tratado (Z4)
- **Z4** (4 ev, `carvia.importar`): `Erro na extracao de veiculos LLM
  (claude-sonnet-4-6): Extra data: line 1 column 5` — `json.loads` falhando em
  saida nao-JSON do modelo. Ja e **handled** (logger, nao 500, com fallback).
  Robustez de parse de saida LLM = mudanca de estrategia, nao bug tecnico simples.

### Infra externa / billing Anthropic (Y2, Y4, Z5, R5)
- **Y2** (30 ev), **Y4** (23 ev), **Z5** (7 ev): `Error code 400 — credit balance
  too low` (workers `step_judge`/`triage_shadow`/`plan_verifier` — shadow do agente).
  Billing da conta Anthropic, nao acionavel por codigo.
- **R5** (8 ev, `analyze_patterns_job`): `OverloadedError 529` — transiente da API.

### Odoo XML-RPC / schema CIEL IT (YV)
- **YV** (10 ev): `Fault Odoo — Invalid field 'product_code' on model
  l10n_br_ciel_it_account.dfe.line` — schema do ERP externo (CIEL IT), infra.

### Comportamento do agente / MEMORY_MCP (E7)
- **E7** (15 ev, 11 us): `Path deve comecar com /memories, recebido
  /tmp/subagent-findings/...` — validacao do MEMORY_MCP; comportamento do agente,
  ja documentado em triagens anteriores. Fora de escopo.

### Transientes / baixa frequencia / negocio / scripts ad-hoc
- **YX** (6 ev, `carvia.simulador_carga_rota`): `403 Forbidden` — recurso
  read-protected; provavel permissao/asset, sem stacktrace de codigo acionavel.
- **RH** (17 ev, `hora.pedidos_importar_xlsx_confirmar`): `ModeloPendenteError`
  levantado **intencionalmente** (modelo 'MIA AM' nao reconhecido -> pendencia
  aguardando decisao). Regra de negocio, nao bug.
- **YY** (16 ev, `hora.nfs_upload_lote`): `PendingRollbackError` apos
  `UniqueViolation` (duplicate key) — upload de NF ja existente; fluxo de dados,
  nao type/null simples.
- **J8** (4 ev, `carvia.api_buscar_cnpj`): `Erro HTTP 400` de API externa de CNPJ.
- **Z3** (2 ev, `carvia.api_ctes_para_custo`): N+1 Query (perf, refactor).
- **Z1** (2 ev, `adhoc_capture_job`): `StringDataRightTruncation varchar(64)` —
  valor longo demais; corrigir = ALTER COLUMN (migration) ou truncar no negocio.
- **M6** (2 ev, `carvia.pagar_fatura_cliente`): `ValueError: Total alocado excede
  saldo` — validacao de negocio funcionando.
- **Z0** (1 ev) e **YZ** (1 ev): `Command failed exit code 1` no SDK do
  Agente Lojas (`stream_response` / message reader) — subprocesso do agente,
  transiente.
- **YW** (1 ev): autoflush prematuro ao processar CTe 44332 — esporadico.
- **XY** (1 ev): `.msg` ausente em `/tmp` (`fretes.criar_despesa_extra_frete`) —
  arquivo temporario efemero do Render.
- **WA** (1 ev): `invalid tessdata path` no OCR de PDF (`comprovantes_api_upload`)
  — config de ambiente OCR, ja documentado.

## Metricas

- Issues abertas (unresolved/production) antes: 28
- Issues corrigidas e marcadas resolved: 2 (Y1, Z2)
- Issues abertas depois: 26
- Reducao: 7.1%
- **Nota**: 6 das 26 remanescentes (57 eventos, ~maior volume) somem com 1 acao
  unica de infra: aplicar a migration `2026_06_16_veiculo_parametros_custo`.

## Arquivos Modificados (codigo)

- `app/financeiro/services/ofx_vinculacao_service.py` (Y1 — 1 linha)
- `app/motos_assai/services/parsers/nf_qpa_adapter.py` (Z2 — helper + 2 call sites)
