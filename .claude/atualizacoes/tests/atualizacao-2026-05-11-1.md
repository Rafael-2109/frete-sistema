# Atualizacao Tests — 2026-05-11-1

**Data**: 2026-05-11
**Total executados**: 1019 tests (+ 20 nao coletados em `tests/skills/motos_assai/`)
**Passed**: 946 | **Failed**: 47 | **Error**: 19 | **Skipped**: 7
**Taxa de sucesso (executados)**: 92.84%
**Tempo total**: 265.46s (4min 25s)

## Resumo

Suite executada com `--maxfail=999` para visibilidade completa (sobreescrevendo `--maxfail=5` do `pytest.ini`). 47 falhas + 19 erros distribuidos em 6 modulos. A maioria absoluta concentra-se em: **(a) migrations nao aplicadas no banco local** (`audit_log_custeio` ausente, coluna `ativo` em `custo_frete` ausente, coluna `modalidade_frete` em `hora_venda`), **(b) fixtures PDF/XLSX ausentes em `tests/motos_assai/fixtures/`** (`pedido_voe_exemplo.pdf`, `recibo_motochefe_exemplo.pdf/xlsx`) e **(c) state pollution entre modulos** (19 ERROR em `tests/hora/` so aparecem em suite completa — quando executados em isolamento ou apenas com `tests/hora/`, passam ou viram FAIL claros). Tambem houve **1 erro de coleta** em `tests/skills/motos_assai/conftest.py` por uso de `pytest_plugins` em conftest nao top-level (deprecated em pytest 8.4) — 20 testes nao coletados; suite executada com `--ignore=tests/skills/motos_assai`. **Nenhuma falha tem correlacao com as mudancas do D4** (D4 mexeu em `app/carteira/routes/estoque_api.py` e `app/custeio/routes/custeio_routes.py:1927` — ambos arquivos sem cobertura nesta suite).

## Erro de Coleta (Bloqueante para 20 testes)

### tests/skills/motos_assai/conftest.py
```
Defining 'pytest_plugins' in a non-top-level conftest is no longer supported.
Please move it to a top level conftest file at the rootdir.
```
- **Causa**: linha 14 `pytest_plugins = ['tests.motos_assai.conftest']` — pytest 8.4 nao aceita mais em conftest nao raiz
- **Impacto**: 20 testes em `tests/skills/motos_assai/` nao coletados (suite total seria 1039)
- **Fix sugerido**: mover declaracao para `tests/conftest.py` (raiz) ou importar fixtures diretamente

## Falhas Detalhadas

### 1. Agente SDK — Pending Questions (2 falhas)

#### tests/agente/sdk/test_pending_questions.py::TestSubmitAnswer::test_submit_answer_signals_both_events
- **Linha**: 99
- **Erro**: `assert False` — `async_event.is_set()` retornou False apos `submit_answer`
- **Diagnostico**: `PendingQuestion.async_event` nao esta sendo signaled corretamente quando `event` (threading) e signaled. Race condition entre o `threading.Event` e o `asyncio.Event`.
- **Correlacao D4**: Nao

#### tests/agente/sdk/test_pending_questions.py::TestCancelPending::test_cancel_pending_unblocks_async_event
- **Linha**: 186
- **Erro**: `assert False` — `async_event.is_set()` retornou False apos `cancel_pending`
- **Diagnostico**: Mesma classe de bug do anterior — `cancel_pending` nao sinaliza `async_event`
- **Correlacao D4**: Nao

### 2. CarVia — A3 CTRC CTe Comp + Sprint E (3 falhas)

#### tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao::test_ctrc_confirmado_retorna_ok
- **Linha**: 202
- **Erro**: `AssertionError: assert 'CORRIGIDO' == 'OK'`
- **Diagnostico**: REINCIDENTE. Mock de `resolver_ctrc_ssw` nao esta sendo aplicado — o worker faz chamada SSW real e retorna CTRC corrigido (`CAR-164-3` em vez do esperado). Mesmo bug documentado em 2026-04-27 e 2026-05-05.
- **Tempo**: 22.03s (chamada SSW real)
- **Correlacao D4**: Nao

#### tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao::test_ctrc_divergente_corrigido
- **Linha**: 226
- **Erro**: `AssertionError: assert 'CAR-164-3' == 'CAR-113-9'`
- **Diagnostico**: Mesmo bug do anterior — patch path do mock incorreto
- **Tempo**: 21.52s
- **Correlacao D4**: Nao

#### tests/carvia/test_sprint_e_medio.py::TestE8FilaDivergente::test_listar_retorna_lista
- **Linha**: 118
- **Erro**: `AttributeError: 'ConferenciaService' object has no attribute 'listar_fretes_divergentes'`
- **Diagnostico**: NOVO. Teste chama metodo inexistente em `ConferenciaService`. Refatoracao no servico ou teste defasado.
- **Correlacao D4**: Nao

### 3. Custeio — Regressao Sprint 1/2 (6 falhas)

#### tests/custeio/test_regressao_sprint_1_2.py::TestAlterarTipoCusto::test_aceita_tipo_manual
- **Linha**: 102
- **Erro**: `sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint "uq_custo_considerado_versao"` (cod_produto, versao)=(TEST_C2_010, 1)
- **Diagnostico**: Teste anterior deixou registro residual com mesmo `TEST_C2_010`. Fixture sem cleanup adequado.
- **Correlacao D4**: Nao (D4 tocou em `custeio_routes.py:1927` BOM recursiva, sem relacao com tabela `custo_considerado`)

#### tests/custeio/test_regressao_sprint_1_2.py::TestPartialUniqueCustoAtual::test_inserir_segunda_versao_atual_falha
- **Linha**: 165
- **Erro**: `Failed: DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>`
- **Diagnostico**: Partial unique index `(cod_produto) WHERE custo_atual=true` nao existe no banco local. Migration nao aplicada.

#### tests/custeio/test_regressao_sprint_1_2.py::TestCheckConstraints::test_tipo_custo_selecionado_invalido
- **Linha**: 186
- **Erro**: `Failed: DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>`
- **Diagnostico**: CHECK constraint `tipo_custo_selecionado IN (...)` nao existe no banco local. Migration nao aplicada.

#### tests/custeio/test_regressao_sprint_1_2.py::TestCheckConstraints::test_percentual_frete_acima_de_100
- **Linha**: 201
- **Erro**: `psycopg2.errors.UndefinedColumn: column "ativo" of relation "custo_frete" does not exist`
- **Diagnostico**: Coluna `ativo` em `custo_frete` nao existe no banco local. Migration `add_ativo_custo_frete` ou similar nao aplicada.

#### tests/custeio/test_regressao_sprint_1_2.py::TestCalculoMargem::test_calcular_margem_aceita_campos_corretos
- **Linha**: 245
- **Erro**: `AssertionError: assert 'margem_bruta' in {}` + log warn `Working outside of application context`
- **Diagnostico**: `calcular_margem` retornou dict vazio por exception de contexto Flask em `carteira_service.py:1454`. Fixture nao envelopa em `app_context`.

#### tests/custeio/test_regressao_sprint_1_2.py::TestAuditLog::test_registrar_evento
- **Linha**: 267
- **Erro**: `psycopg2.errors.UndefinedTable: relation "audit_log_custeio" does not exist`
- **Diagnostico**: Tabela `audit_log_custeio` nao existe no banco local. Migration nao aplicada.

### 4. HORA — Pedido Workflow (15 falhas + 1 avaria)

Todas falhas em `test_pedido_workflow.py` (15 testes) tem a MESMA causa raiz:
```
File: app/hora/services/venda_service.py:710
ValueError: modalidade_frete invalida: '9' (esperado '0' CIF ou '1' FOB)
```
- **Diagnostico**: A fixture `_criar_pedido_cotacao` em `tests/hora/test_pedido_workflow.py:81` passa `modalidade_frete='9'`, mas `venda_service.criar_venda_manual` so aceita `'0'` (CIF) ou `'1'` (FOB). Codigo `'9'` parece ser legado (NF=9?). Reincidente desde 2026-05-05 com mesma natureza (modalidade_frete missing no DB), agora evoluiu para validacao explicita rejeitando o valor.
- **Testes afetados**: `test_criar_venda_manual_cria_cotacao_e_reserva_chassi`, `test_criar_pedido_chassi_indisponivel_falha`, `test_confirmar_venda_transiciona_para_confirmado`, `test_confirmar_venda_ja_confirmada_falha`, `test_cancelar_venda_cotacao_devolve_chassi`, `test_cancelar_venda_motivo_curto_falha`, `test_cancelar_venda_idempotente`, `test_editar_observacoes_em_qualquer_status_exceto_cancelado`, `test_editar_cliente_em_confirmado_falha`, `test_editar_cancelado_falha`, `test_adicionar_item_em_cotacao`, `test_adicionar_item_em_confirmado_falha`, `test_remover_item_devolve_chassi`, `test_remover_ultimo_item_falha`, `test_editar_item_troca_chassi`
- **Correlacao D4**: Nao

#### tests/hora/test_avaria_service.py::test_registrar_sem_foto_falha
- **Linha**: 33
- **Erro**: `Failed: DID NOT RAISE <class 'ValueError'>`
- **Diagnostico**: Servico nao mais valida foto obrigatoria — ou logica de validacao foi removida ou agora aceita avaria sem foto
- **Correlacao D4**: Nao

### 5. HORA — 19 ERROR de state pollution (so em suite completa)

19 ERROR em `tests/hora/test_avaria_service.py`, `test_chassi_protecao.py`, `test_estoque_eventos_em_estoque.py`, `test_moto_service_novos_tipos.py` ocorrem **apenas em suite completa**. Quando executados em isolamento (`pytest tests/hora/`), passam. Sintoma do erro principal: `sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint "hora_loja_cnpj_key"` — fixture de loja anterior nao foi limpa.

- **Testes afetados (ERROR no setup)**:
  - `test_avaria_service.py`: 10 testes (`test_registrar_avaria_cria_header_foto_e_evento`, `test_registrar_sem_foto_falha`, `test_descricao_curta_falha`, `test_chassi_inexistente_falha`, `test_multiplas_avarias_no_mesmo_chassi`, `test_resolver_avaria_muda_status`, `test_ignorar_avaria`, `test_resolver_ja_finalizada_falha`, `test_adicionar_foto_depois`, `test_chassi_ja_vendido_falha`)
  - `test_chassi_protecao.py`: 3 testes (`test_chassi_em_pedido_protegido`, `test_chassi_em_nf_entrada_protegido`, `test_motivos_protecao_lista`)
  - `test_estoque_eventos_em_estoque.py`: 3 testes
  - `test_moto_service_novos_tipos.py`: 3 testes
- **Diagnostico**: Fixture de loja em `tests/hora/conftest.py` (ou similar) usa CNPJ fixo sem cleanup pos-suite. Em suite completa, outro modulo deixou residuo. Solucao: cleanup `truncate hora_loja cascade` em teardown ou usar CNPJs unicos por teste.
- **Correlacao D4**: Nao

### 6. Motos Assai — Fixtures ausentes (22 falhas)

Todos os testes de extractors/services em `tests/motos_assai/` falham por **fixtures PDF/XLSX ausentes em `tests/motos_assai/fixtures/`**:

- `tests/motos_assai/fixtures/pedido_voe_exemplo.pdf` — ausente (afeta `test_pedido_service.py` 2 testes + `test_qpa_pedido_extractor.py` 11 testes)
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf` — ausente (afeta `test_motochefe_recibo_pdf_extractor.py` 5 testes + `test_recibo_service.py` 2 testes)
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.xlsx` — ausente (afeta `test_recibo_service.py` 1 teste)

Adicionalmente, 2 testes em `test_recibo_service.py` falham por mensagem de erro com acento divergente:
- `test_tipo_arquivo_invalido` (linha 96): regex `'não suportado'` (com acento) vs codigo emite `'nao suportado'` (sem acento)
- `test_recibo_sem_chassis_levanta_erro` (linha 178): regex `'Determinístico zero'` vs codigo emite `'Deterministico zero + LLM falhou'`

- **Testes afetados**: `test_fixture_exists`, `test_extract_retorna_chassis`, `test_header_data_recibo`, `test_header_equipe_haroldo_sp`, `test_modelo_texto_dot_e_mia`, `test_importar_pdf_voe_sucesso`, `test_importar_duplicado_falha`, `test_extract_retorna_38_lojas_x_3_modelos`, `test_header_global_consistente`, `test_lojas_unicas_38`, `test_codigos_qpa_3_modelos`, `test_qtd_x11_mini_e_10_por_loja`, `test_qtd_dot_e_14_por_loja`, `test_valor_unitario_dot`, `test_validate_aceita_item_valido`, `test_zero_warnings_zero_errors_em_pdf_canonico`, `test_importar_pdf_recibo`, `test_importar_xlsx_recibo`, `test_tipo_arquivo_invalido`, `test_s3_upload_ocorre_apos_parsing`, `test_recibo_sem_chassis_levanta_erro`
- **Correlacao D4**: Nao
- **Fix sugerido**: adicionar fixtures binarias ao repo (gitignored hoje?) ou marcar testes `@pytest.mark.skipif(not fixture_exists)`

## Skipped (7)

7 testes em `tests/motos_assai/test_motochefe_recibo_xlsx_extractor.py` (todos os `sssssss` na progress bar). Provavel skip condicional por dependencia opcional (libxl, openpyxl, etc.).

## Correlacao com D4 (Sentry Triage)

D4 modificou:
- `app/carteira/routes/estoque_api.py` — substituiu `saldo_estoque_pedido` por `projecao_completa['estoque_atual']` (AttributeError fix)
- `app/custeio/routes/custeio_routes.py:1927` — coercao Decimal*float na funcao BOM recursiva (TypeError fix)

**Nenhuma das 47 falhas / 19 erros tem correlacao**:
- Falhas `custeio/test_regressao_sprint_1_2.py` exercitam modelos `CustoConsiderado`, `CustoFrete`, `AuditLogCusteio` — nao a rota BOM tocada por D4
- Falhas `carteira/` nao existem nesta suite (modulo sem cobertura de testes propria)
- Demais falhas (agente/sdk, carvia, hora, motos_assai) sao em modulos nao tocados por D4

## Metricas

| Metrica | Valor |
|---------|-------|
| Total executados | 1019 |
| Passed | 946 (92.84%) |
| Failed | 47 (4.61%) |
| Error | 19 (1.86%) |
| Skipped | 7 (0.69%) |
| Nao coletados (conftest pytest 8.4) | 20 |
| Tempo total | 265.46s (4min 25s) |
| Teste mais lento | `test_ctrc_confirmado_retorna_ok` (22.03s — chamada SSW real) |

## Top Slowest (10)

| Teste | Tempo |
|-------|-------|
| `tests/carvia/test_a3_ctrnc_cte_comp.py::test_ctrc_confirmado_retorna_ok` | 22.03s |
| `tests/carvia/test_a3_ctrnc_cte_comp.py::test_ctrc_divergente_corrigido` | 21.52s |
| `tests/pallet/test_fluxo_nf_devolucao_vinculacao.py::test_confirmar_sugestao` | 7.33s |
| `tests/pallet/test_fluxo_nf_devolucao_vinculacao.py::test_rejeitar_sugestao` | 6.60s |
| `tests/motos_assai/test_smoke_routes.py::test_smoke_faturamento_nf_detalhe_inexistente` | 1.77s (setup) |
| `tests/motos_assai/test_recebimento_routes.py::test_finalizar_route_com_faltantes_sem_confirmar_400` | 1.67s (setup) |
| `tests/agente/models/test_top_subagents_by_cost.py::test_top_subagents_by_cost_aggregates_correctly` | 1.63s (setup) |
| `tests/motos_assai/test_separacao_service.py::test_chassi_nao_disponivel_falha` | 1.60s (setup) |
| `tests/motos_assai/test_recebimento_service.py::test_registrar_chassi_vazio_falha` | 1.57s (setup) |
| `tests/motos_assai/test_recebimento_service.py::test_finalizar_emite_evento_moto_faltando` | 1.56s (setup) |

## Comparativo Historico

| Data | Total | Passed | Failed | Error | Skipped | Taxa |
|------|-------|--------|--------|-------|---------|------|
| 2026-04-06-1 | 288 | 288 | 0 | 0 | 0 | 100% |
| 2026-04-20-1 | 569 | 569 | 0 | 0 | 0 | 100% |
| 2026-04-27-1 | 737 | 735 | 2 | 0 | 0 | 99.73% |
| 2026-05-05-1 | 766 | 749 | 17 | 0 | 0 | 97.78% |
| **2026-05-11-1** | **1019** | **946** | **47** | **19** | **7** | **92.84%** |

**Tendencia**: degradacao progressiva — +30 falhas vs 2026-05-05 e surgimento de 19 erros novos. Crescimento da suite (+253 testes) trouxe regressao em ordem-de-execucao e falta de fixtures. Falhas estruturais reincidentes (CarVia mock SSW + HORA modalidade_frete) precisam de fix definitivo.

## Acoes Recomendadas

1. **Aplicar migrations locais** para resolver 6 falhas custeio (tabela `audit_log_custeio`, coluna `ativo` em `custo_frete`, partial unique + check constraints)
2. **Adicionar fixtures** `pedido_voe_exemplo.pdf`, `recibo_motochefe_exemplo.pdf/xlsx` em `tests/motos_assai/fixtures/` (ou skip condicional)
3. **Corrigir patch path** do mock `resolver_ctrc_ssw` em `test_a3_ctrnc_cte_comp.py` (reincidente ha 3 ciclos)
4. **Corrigir fixture HORA** — passar `modalidade_frete='0'` ou `'1'` em `_criar_pedido_cotacao` em vez de `'9'` (resolve 15 testes)
5. **Corrigir state pollution** em `tests/hora/conftest.py` — usar CNPJ unico por teste ou cleanup explicito de `hora_loja`
6. **Mover `pytest_plugins`** de `tests/skills/motos_assai/conftest.py` para `tests/conftest.py` (pytest 8.4 deprecation)
7. **Investigar race** em `PendingQuestion.async_event` no SDK agente (2 falhas async)
8. **Acrescentar metodo** `listar_fretes_divergentes` em `ConferenciaService` ou atualizar teste E8

## Comando de Execucao

```bash
source .venv/bin/activate
python -m pytest tests/ -v --tb=short --timeout=60 --ignore=tests/skills/motos_assai --maxfail=999
```
