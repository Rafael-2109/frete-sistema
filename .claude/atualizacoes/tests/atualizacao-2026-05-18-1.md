# Atualizacao Tests — 2026-05-18-1

**Data**: 2026-05-18
**Total**: 1414 tests
**Passed**: 1326 | **Failed**: 33 | **Error**: 48 | **Skipped**: 7
**Taxa de sucesso**: 93.78%
**Tempo total**: 563.72s (~9m24s)

---

## Resumo

Suite executou completa (1414 testes) com taxa de sucesso 93.78%. As 33 falhas se concentram em `motos_assai` (28: 22 por fixtures PDF/XLSX ausentes em `tests/motos_assai/fixtures/`, 3 por assinatura `vincular_nf_manualmente()` divergente, 3 por logica de negocio FASE3/FASE5/D5_match) e nucleos menores em `custeio` (2: state pollution + app context), `agente/sdk` (2: race async_event reincidente desde 2026-04-27), `carvia` (1: `listar_fretes_divergentes` ainda ausente). Os 48 errors sao state pollution suite-wide: 34 em `hora` (UniqueViolation `hora_loja_cnpj_key`) e 14 em `motos_assai/test_carregamento_service_crud.py` (CompileError SQLite vs ARRAY postgres). **Sem correlacao com D4** (Sentry triagem nao modificou nenhum arquivo).

---

## Falhas Detalhadas

### Bloco 1: motos_assai — Fixtures PDF/XLSX Ausentes (22 falhas)

Arquivos esperados (nao versionados):
- `tests/motos_assai/fixtures/pedido_voe_exemplo.pdf` (FileNotFoundError)
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf`
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.xlsx`

Testes afetados:
- `test_motochefe_recibo_pdf_extractor.py::test_fixture_exists` — `assert False`
- `test_motochefe_recibo_pdf_extractor.py::test_extract_retorna_chassis` — "Esperava >=50 chassis (canon: 115), veio 0"
- `test_motochefe_recibo_pdf_extractor.py::test_header_data_recibo` — `assert []`
- `test_motochefe_recibo_pdf_extractor.py::test_header_equipe_haroldo_sp` — `assert False`
- `test_motochefe_recibo_pdf_extractor.py::test_modelo_texto_dot_e_mia` — `assert False`
- `test_pedido_service.py::test_importar_pdf_voe_sucesso` — FileNotFoundError
- `test_pedido_service.py::test_importar_duplicado_falha` — FileNotFoundError
- `test_qpa_pedido_extractor.py::test_fixture_exists` — "Fixture .../pedido_voe_exemplo.pdf ausente"
- `test_qpa_pedido_extractor.py::test_extract_retorna_38_lojas_x_3_modelos` — "veio 0"
- `test_qpa_pedido_extractor.py::test_header_global_consistente` — "veio set()"
- `test_qpa_pedido_extractor.py::test_lojas_unicas_38` — `assert 0 == 38`
- `test_qpa_pedido_extractor.py::test_codigos_qpa_3_modelos` — `assert set() == {...}`
- `test_qpa_pedido_extractor.py::test_qtd_x11_mini_e_10_por_loja` — "veio 0"
- `test_qpa_pedido_extractor.py::test_qtd_dot_e_14_por_loja` — `assert 0 == 532`
- `test_qpa_pedido_extractor.py::test_valor_unitario_dot` — StopIteration
- `test_qpa_pedido_extractor.py::test_validate_aceita_item_valido` — IndexError
- `test_qpa_pedido_extractor.py::test_zero_warnings_zero_errors_em_pdf_canonico` — `assert 0 > 0`
- `test_recibo_service.py::test_importar_pdf_recibo` — FileNotFoundError
- `test_recibo_service.py::test_importar_xlsx_recibo` — FileNotFoundError
- `test_recibo_service.py::test_tipo_arquivo_invalido` — "Regex pattern did not match"
- `test_recibo_service.py::test_s3_upload_ocorre_apos_parsing` — FileNotFoundError
- `test_recibo_service.py::test_recibo_sem_chassis_levanta_erro` — "Regex pattern did not match"

**Correlacao D4**: Nao (D4 nao tocou em motos_assai).
**Causa**: Fixtures PDF/XLSX nao foram commitadas (.gitignore ou simplesmente ausente do repo local). Ja era falha de 2026-05-11 (22 falhas motos_assai mesmo padrao).

---

### Bloco 2: motos_assai — `vincular_nf_manualmente(loja_id=...)` (3 falhas)

- `test_vincular_nf_manual.py::test_vincular_nf_nao_reconciliado_cria_sep_em_faturada`
- `test_vincular_nf_manual.py::test_vincular_nf_ja_bateu_falha`
- `test_vincular_nf_manual.py::test_vincular_nf_pedido_inexistente_falha`

**Traceback**: `TypeError: vincular_nf_manualmente() got an unexpected keyword argument 'loja_id'`

**Correlacao D4**: Nao.
**Causa**: Service `vincular_nf_manualmente` foi refatorado e nao aceita mais `loja_id`, mas tests nao foram atualizados.

---

### Bloco 3: motos_assai — Logica de Negocio (3 falhas)

#### test_carregamento_finalizar_fase3.py::test_fase3_excedente_remove_LIFO_outras_seps
- **Traceback**: `AssertionError: assert {'TST_F3N1_C606C472', 'TST_F3N2_6FCA9450'} == {'TST_F3O_C76C9255'}`
- **Causa**: Algoritmo LIFO de remocao de excedente FASE3 esta removendo o conjunto errado de separacoes (espera-se O — antigos, vem N — novos).

#### test_carregamento_finalizar_fase4_5_6.py::test_fase5_excel_versao_1_quando_nao_havia_anterior
- **Traceback**: `AssertionError: assert 'Carregamento finalizado' in (('Carregamento 258 finalizado'))`
- **Causa**: Mensagem de retorno mudou para "Carregamento {id} finalizado" (com numero), test ainda compara string sem id.

#### test_match_v2_cenarios.py::test_d5_match_ignora_sep_faturada
- **Traceback**: `assert None is not None`
- **Causa**: Match v2 esta retornando `None` quando deveria reconciliar; provavelmente cenario D5 (sep ja faturada).

**Correlacao D4**: Nao.

---

### Bloco 4: custeio — State Pollution + App Context (2 falhas)

#### test_regressao_sprint_1_2.py::TestAlterarTipoCusto::test_aceita_tipo_manual
- **Traceback**: `psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "uq_custo_considerado_versao". Key (cod_produto, versao)=(TEST_C2_010, 1) already exists.`
- **Causa**: Test deixa registro `TEST_C2_010 v1` em run anterior sem cleanup (state pollution). Reincidente desde 2026-05-11.

#### test_regressao_sprint_1_2.py::TestCalculoMargem::test_calcular_margem_aceita_campos_corretos
- **Traceback**: `AssertionError: assert 'margem_bruta' in {}` + log: `RuntimeError: Working outside of application context. ... File "app/odoo/services/carteira_service.py", line 1367, in _calcular_margem_bruta — frete_percentual = CustoFrete.buscar_percentual_vigente(...)`
- **Causa**: Test chama `_calcular_margem_bruta` sem app context, e o helper `CustoFrete.buscar_percentual_vigente` (linha 373 de `app/custeio/models.py`) requer `db.session` ativa. Resultado retorna `{}` em vez de dict com `margem_bruta`.

**Correlacao D4**: Nao.

---

### Bloco 5: agente/sdk — Race async_event (2 falhas, reincidentes)

#### test_pending_questions.py::TestSubmitAnswer::test_submit_answer_signals_both_events
- **Traceback**: `assert pq.async_event.is_set()` falha — async_event nao chega a `set()` apesar do threading event sinalizar e o subscriber ter sido sinalizado.

#### test_pending_questions.py::TestCancelPending::test_cancel_pending_unblocks_async_event
- **Traceback**: Mesma assinatura — `async_event.is_set() == False` apos `cancel_pending()`.

**Correlacao D4**: Nao.
**Causa**: Race condition entre `threading.Event` e `asyncio.Event` em `PendingQuestion`. Reincidente desde 2026-05-11 (registrado naquela atualizacao como race async_event).

---

### Bloco 6: carvia — Service Method Ausente (1 falha, reincidente)

#### test_sprint_e_medio.py::TestE8FilaDivergente::test_listar_retorna_lista
- **Traceback**: `AttributeError: 'ConferenciaService' object has no attribute 'listar_fretes_divergentes'`
- **Correlacao D4**: Nao.
- **Causa**: Metodo `listar_fretes_divergentes` esperado pelo test nao existe (ou foi renomeado). Reincidente desde 2026-05-11.

---

## Errors Detalhados (Setup Failures — State Pollution)

### Bloco A: hora — UniqueViolation `hora_loja_cnpj_key` (34 errors)

Todos os tests `tests/hora/test_*` (avaria_service, chassi_protecao, estoque_eventos_em_estoque, moto_service_novos_tipos, transferencia_service) falham no setup com:

```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation)
duplicate key value violates unique constraint "hora_loja_cnpj_key"
```

**Causa**: State pollution suite-wide. Fixture cria loja com CNPJ unico fixo, mas um run anterior deixou a linha persistida no banco local. Reincidente desde 2026-05-11 (19 errors naquele dia, agora 34 com expansao do modulo).

Distribuicao:
- `test_avaria_service.py`: 10 errors
- `test_chassi_protecao.py`: 3 errors
- `test_estoque_eventos_em_estoque.py`: 3 errors
- `test_moto_service_novos_tipos.py`: 3 errors
- `test_transferencia_service.py`: 15 errors

**Correlacao D4**: Nao.

---

### Bloco B: motos_assai — SQLite Compiler vs JSONB (14 errors)

Todos os tests em `tests/motos_assai/test_carregamento_service_crud.py` falham no setup (`db.create_all()`) com:

```
AttributeError: 'SQLiteTypeCompiler' object has no attribute 'visit_JSONB'.
Did you mean: 'visit_JSON'?
column = Column('preferences', JSONB(astext_type=Text()), table=<usuarios>, ...)
```

Compilador SQLAlchemy gera `CompileError`: `(in table 'usuarios', column 'preferences'):
Compiler SQLiteTypeCompiler can't render element of type JSONB`.

**Causa**: Tests usam `DATABASE_URL=sqlite:///:memory:` (pytest.ini) mas `usuarios.preferences` esta declarado como `JSONB` (Postgres-only) em vez de `db.JSON` neutro. SQLite nao tem `visit_JSONB`. Mesmo padrao se aplicaria a hora/* se o setup nao falhasse antes em `hora_loja_cnpj_key` (state pollution).

Distribuicao: 14 errors, todos em `test_carregamento_service_crud.py`:
test_criar_carregamento_sucesso, test_criar_carregamento_pedido_inexistente,
test_criar_carregamento_loja_inexistente, test_criar_carregamento_dois_paralelos_mesma_loja_OK,
test_escanear_chassi_disponivel_sucesso, test_escanear_chassi_inexistente_falha,
test_escanear_chassi_em_outro_carregamento_ativo_falha, test_escanear_carregamento_finalizado_falha,
test_cancelar_item_sucesso, test_cancelar_item_carregamento_finalizado_falha,
test_cancelar_carregamento_em_carregamento_chassi_volta_anterior,
test_cancelar_carregamento_finalizado_chassis_mantem_separada,
test_cancelar_carregamento_motivo_obrigatorio, test_cancelar_carregamento_ja_cancelado_nao_idempotente.

**Correlacao D4**: Nao.

---

## Skipped (7 testes)

A saida com `console_output_style=progress` nao lista os skipped explicitamente, mas o sumario confirma 7 skipped — provavelmente os mesmos 7 que apareceram em 2026-05-11 (testes condicionais por flag/env).

---

## Correlacao com Dominio 4 (Sentry)

D4 status (`/tmp/manutencao-2026-05-18/dominio-4-status.json`):
- `issues_corrigidas: 0`
- `arquivos_modificados: []`

**Nenhuma correlacao possivel** — D4 foi triagem read-only (57 issues unresolved avaliadas, zero acionavel localmente; majoritariamente Odoo XML-RPC 500 de infra externa CIEL IT).

---

## Metricas

| Metrica | Valor |
|---------|-------|
| Tempo total | 563.72s (~9m24s) |
| Testes coletados | 1414 |
| Passed | 1326 (93.78%) |
| Failed | 33 (2.33%) |
| Error (setup/teardown) | 48 (3.39%) |
| Skipped | 7 (0.50%) |
| Slowest test | `test_e2e_search_semantic_cnpj_rule` (17.17s) |
| Slowest setup | `test_top_subagents_by_cost_aggregates_correctly` (1.78s) |

---

## Comparacao com Execucao Anterior (2026-05-11)

| Metrica | 2026-05-11 | 2026-05-18 | Delta |
|---------|------------|------------|-------|
| Total | 1019 (+20 nao coletados) | 1414 | +375 |
| Passed | 946 | 1326 | +380 |
| Failed | 47 | 33 | -14 |
| Error | 19 | 48 | +29 |
| Skipped | 7 | 7 | 0 |
| Taxa sucesso | 92.84% | 93.78% | +0.94pp |
| Tempo total | 265.46s | 563.72s | +112% |

**Observacoes**:
- +375 testes coletados (incluindo os 20 que falhavam coleta antes — pytest 8.4 conftest deprecation resolvida).
- Melhora geral em FAILED (-14): hora resolveu o `modalidade_frete=9` invalido (-16 falhas) + custeio caiu de 6 para 2.
- Piora em ERROR (+29): state pollution `hora_loja_cnpj_key` expandiu para mais arquivos do modulo (34 errors vs 19) e novo bloco `motos_assai/test_carregamento_service_crud.py` (+14 SQLite ARRAY).
- Tempo 2x maior — provavel impacto do crescimento do suite + tests motos_assai mais lentos.

---

## Acao Recomendada

1. **Cleanup state pollution `hora_loja_cnpj_key`** (urgente — bloqueia 34 testes): fixture deve usar CNPJ randomico ou `tearDown` agressivo. Prioridade ALTA.
2. **Cleanup `custeio.TEST_C2_010`**: mesma raiz — fixture nao limpa.
3. **`usuarios.preferences` JSONB->JSON**: trocar `JSONB` por `db.JSON` (neutro) no modelo `usuarios` ou condicionar tipo por dialect; quebra `db.create_all()` em SQLite e bloqueia 14 tests motos_assai/test_carregamento_service_crud.py.
4. **Fixtures PDF/XLSX motos_assai**: commitar `pedido_voe_exemplo.pdf`, `recibo_motochefe_exemplo.pdf`, `recibo_motochefe_exemplo.xlsx` em `tests/motos_assai/fixtures/` (verificar .gitignore).
5. **Race async_event** (reincidente 3 ciclos): investigar `app/agente/sdk/pending_questions.py` — `async_event.set()` precisa ser agendado via `loop.call_soon_threadsafe`.
6. **`listar_fretes_divergentes`** (reincidente 3 ciclos): implementar metodo no `ConferenciaService` ou atualizar test para nome atual.
7. **`vincular_nf_manualmente(loja_id=...)`**: atualizar tests para nova assinatura.
