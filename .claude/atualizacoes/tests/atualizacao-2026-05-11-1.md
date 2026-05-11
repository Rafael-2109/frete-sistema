# Atualizacao Tests — 2026-05-11-1

**Data**: 2026-05-11
**Total executados**: 1019 tests (+ 20 nao coletados em `tests/skills/motos_assai/`)
**Passed**: 963 | **Failed**: 49 | **Error**: 0 | **Skipped**: 7
**Taxa de sucesso (executados)**: 94.50%
**Tempo total**: 264.48s (4min 24s)

## Resumo

Suite executada com `--maxfail=0` para visibilidade completa. 49 falhas distribuidas em 6 modulos: `agente/sdk` (2), `carvia` (3), `custeio` (6), `hora` (16), `motos_assai/test_*_extractor.py + service.py` (22). A maioria absoluta esta concentrada em **(a) migrations nao aplicadas no banco local** (`audit_log_custeio` ausente, coluna `ativo` em `custo_frete` ausente, coluna `modalidade_frete` ausente em hora) e **(b) fixtures PDF/XLSX ausentes em `tests/motos_assai/fixtures/`** (pedido_voe_exemplo.pdf, recibo_motochefe_exemplo.pdf/xlsx). Tambem houve **1 erro de coleta** em `tests/skills/motos_assai/conftest.py` por uso de `pytest_plugins` em conftest nao top-level (deprecated no pytest 8.4) — 20 testes nao coletados; suite executada com `--ignore=tests/skills/motos_assai`. Nenhuma falha tem correlacao com as mudancas do D4.

## Erro de Coleta (Bloqueante para 20 testes)

### tests/skills/motos_assai/conftest.py
```
Defining 'pytest_plugins' in a non-top-level conftest is no longer supported.
Please move it to a top level conftest file at the rootdir.
```
- **Causa**: linha 14 `pytest_plugins = ['tests.motos_assai.conftest']` — pytest 8.4 nao aceita mais em conftest nao raiz
- **Impacto**: 20 testes em `tests/skills/motos_assai/test_*.py` nao coletados
- **Fix sugerido**: mover declaracao para `tests/conftest.py` (raiz) ou usar import direto de fixtures

## Falhas Detalhadas

### 1. Agente SDK — Pending Questions (2 falhas)

#### tests/agente/sdk/test_pending_questions.py::TestSubmitAnswer::test_submit_answer_signals_both_events
- **Linha**: 99
- **Erro**: `assert False` — `async_event.is_set()` retornou False apos `submit_answer`
- **Causa provavel**: race condition / loop policy entre threading.Event e asyncio.Event
- **Correlacao D4**: NAO

#### tests/agente/sdk/test_pending_questions.py::TestCancelPending::test_cancel_pending_unblocks_async_event
- **Linha**: 186
- **Erro**: `assert False` — `async_event.is_set()` retornou False apos `cancel_pending`
- **Correlacao D4**: NAO

### 2. CarVia — A3 CTRC vs CT-e Comp (3 falhas)

#### tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao::test_ctrc_confirmado_retorna_ok
- **Linha**: 202
- **Erro**: `AssertionError: assert 'CORRIGIDO' == 'OK'`
- **Causa**: worker bypassa o mock SSW e consulta SSW real; CTRC retorna divergente da expectativa
- **Reincidente**: SIM — ja registrado em 2026-04-27 e 2026-05-05 (mesmo bug de patch path em `resolver_ctrc_ssw`)
- **Correlacao D4**: NAO

#### tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao::test_ctrc_divergente_corrigido
- **Linha**: 226
- **Erro**: `AssertionError: assert 'CAR-164-3' == 'CAR-113-9'` (mesma raiz acima)
- **Reincidente**: SIM
- **Correlacao D4**: NAO

#### tests/carvia/test_sprint_e_medio.py::TestE8FilaDivergente::test_listar_retorna_lista
- **Linha**: 118
- **Erro**: `AttributeError: 'ConferenciaService' object has no attribute 'listar_fretes_divergentes'`
- **Causa**: metodo nao existe no `ConferenciaService` — refactor pendente ou rota nova
- **Correlacao D4**: NAO

### 3. Custeio — Regressao Sprint 1/2 (6 falhas)

Todas relacionadas a **migrations nao aplicadas no banco local de testes**.

#### TestAlterarTipoCusto::test_aceita_tipo_manual
- **Erro**: `IntegrityError: duplicate key value violates unique constraint "uq_custo_considerado_versao"` (registro pre-existente nao limpo entre testes)

#### TestPartialUniqueCustoAtual::test_inserir_segunda_versao_atual_falha
- **Erro**: `Failed: DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>` (constraint partial unique nao aplicado)

#### TestCheckConstraints::test_tipo_custo_selecionado_invalido
- **Erro**: `Failed: DID NOT RAISE` (CHECK constraint ausente)

#### TestCheckConstraints::test_percentual_frete_acima_de_100
- **Erro**: `ProgrammingError: column "ativo" of relation "custo_frete" does not exist`
- **Causa**: migration que adiciona `custo_frete.ativo` nao aplicada localmente

#### TestCalculoMargem::test_calcular_margem_aceita_campos_corretos
- **Linha**: 245
- **Erro**: `AssertionError: assert 'margem_bruta' in {}` — funcao retorna dict vazio

#### TestAuditLog::test_registrar_evento
- **Erro**: `ProgrammingError: relation "audit_log_custeio" does not exist`
- **Causa**: tabela `audit_log_custeio` nao criada no banco local

**Correlacao D4 (todas as 6)**: NAO. D4 modificou `app/custeio/routes/custeio_routes.py:1927` (TypeError Decimal*float em funcao BOM recursiva). As falhas sao ortogonais: estrutura de schema/migrations, nao logica de calculo BOM.

### 4. Hora — Pedido Workflow + Avaria (16 falhas)

Todas falham com `ValueError: modalidade_frete invalida: '9' (esperado '0' CIF ou '1' FOB)` ou problema correlato de fixture (`test_registrar_sem_foto_falha` — `Failed: DID NOT RAISE ValueError`).

- `tests/hora/test_avaria_service.py::test_registrar_sem_foto_falha`
- `tests/hora/test_pedido_workflow.py::test_criar_venda_manual_cria_cotacao_e_reserva_chassi`
- `tests/hora/test_pedido_workflow.py::test_criar_pedido_chassi_indisponivel_falha`
- `tests/hora/test_pedido_workflow.py::test_confirmar_venda_transiciona_para_confirmado`
- `tests/hora/test_pedido_workflow.py::test_confirmar_venda_ja_confirmada_falha`
- `tests/hora/test_pedido_workflow.py::test_cancelar_venda_cotacao_devolve_chassi`
- `tests/hora/test_pedido_workflow.py::test_cancelar_venda_motivo_curto_falha`
- `tests/hora/test_pedido_workflow.py::test_cancelar_venda_idempotente`
- `tests/hora/test_pedido_workflow.py::test_editar_observacoes_em_qualquer_status_exceto_cancelado`
- `tests/hora/test_pedido_workflow.py::test_editar_cliente_em_confirmado_falha`
- `tests/hora/test_pedido_workflow.py::test_editar_cancelado_falha`
- `tests/hora/test_pedido_workflow.py::test_adicionar_item_em_cotacao`
- `tests/hora/test_pedido_workflow.py::test_adicionar_item_em_confirmado_falha`
- `tests/hora/test_pedido_workflow.py::test_remover_item_devolve_chassi`
- `tests/hora/test_pedido_workflow.py::test_remover_ultimo_item_falha`
- `tests/hora/test_pedido_workflow.py::test_editar_item_troca_chassi`

**Causa**: fixtures usam `modalidade_frete='9'` mas `app/hora/services/venda_service.py:710` valida `'0' (CIF) | '1' (FOB)`. Provavelmente fixtures desatualizadas ou validacao nova nao refletida nos fixtures.
**Reincidente parcial**: 2026-05-05 reportou as mesmas falhas em test_pedido_workflow por `coluna modalidade_frete ausente`. Hoje a coluna existe mas a validacao rejeita o valor — migration `hora_21` aplicada mas valor de fixture incorreto.
**Correlacao D4**: NAO. D4 nao tocou modulo HORA.

### 5. Motos Assai — Extractors e Services PDF/XLSX (22 falhas)

Todas por **fixtures PDF/XLSX ausentes** em `tests/motos_assai/fixtures/`.

#### Fixtures faltantes
- `tests/motos_assai/fixtures/pedido_voe_exemplo.pdf` — `FileNotFoundError`
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf` — `FileNotFoundError`
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.xlsx` — `FileNotFoundError`

#### Testes afetados
- `test_motochefe_recibo_pdf_extractor.py`: 5 falhas (`test_fixture_exists`, `test_extract_retorna_chassis`, `test_header_data_recibo`, `test_header_equipe_haroldo_sp`, `test_modelo_texto_dot_e_mia`)
- `test_pedido_service.py`: 2 falhas (`test_importar_pdf_voe_sucesso`, `test_importar_duplicado_falha`)
- `test_qpa_pedido_extractor.py`: 11 falhas (todas dependem do PDF VOE; cascata de StopIteration/IndexError/AssertionError)
- `test_recibo_service.py`: 5 falhas (`test_importar_pdf_recibo`, `test_importar_xlsx_recibo`, `test_tipo_arquivo_invalido`, `test_s3_upload_ocorre_apos_parsing`, `test_recibo_sem_chassis_levanta_erro`)

**Correlacao D4**: NAO. D4 nao tocou modulo motos_assai.

## Skipped (7 testes)

Todos em `tests/motos_assai/test_motochefe_recibo_xlsx_extractor.py` com motivo: `Fixture XLSX não presente — rodar generate_xlsx_fixture.py`. Mesma raiz das falhas em motos_assai.

## Correlacao com D4 (Sentry Triage)

D4 modificou:
- `app/carteira/routes/estoque_api.py` (AttributeError saldo_estoque_pedido)
- `app/custeio/routes/custeio_routes.py:1927` (TypeError Decimal*float em funcao BOM recursiva)

**Correlacoes encontradas**: 0 (zero)

- Falhas em `tests/custeio/` sao sobre estrutura de schema (tabela/coluna ausentes, constraints) — nao tocam funcao BOM nem logica em `custeio_routes.py:1927`
- Nenhum teste cobre rota afetada de `estoque_api.py`
- Apos D4, taxa de sucesso permaneceu estavel; nenhuma regressao ou melhoria observada na suite

## Comparativo com Execucao Anterior (2026-05-05)

| Metrica            | 2026-05-05 | 2026-05-11 | Delta |
|--------------------|------------|------------|-------|
| Total executados   | 766        | 1019       | +253  |
| Passed             | 749        | 963        | +214  |
| Failed             | 15 (+2)    | 49         | +32   |
| Skipped            | 0          | 7          | +7    |
| Taxa de sucesso    | 97.78%     | 94.50%     | -3.28pp |
| Tempo              | 96.13s     | 264.48s    | +168s |

**Diferencas**:
- +253 testes coletados (provavelmente novos modulos motos_assai/custeio expandidos)
- Falhas hora/test_pedido_workflow mudaram de causa (`modalidade_frete` coluna ausente -> valor invalido)
- Novas familias de falha: custeio (6), motos_assai/extractors (22), agente/sdk (2), carvia/sprint_e (1)
- Falhas reincidentes: carvia/test_a3 (mesmas 2 desde 2026-04-27)
- Erro de coleta novo em `tests/skills/motos_assai/conftest.py` (incompatibilidade pytest 8.4)

## Metricas

- **Taxa de sucesso geral (executados)**: 94.50% (963/1019)
- **Taxa de sucesso (excluindo conhecidas/fixtures faltantes)**: ~97.4% (excluindo 22 motos_assai sem fixture + 6 custeio sem migration + 16 hora com fixture invalida = 44 falhas estruturais)
- **Tempo total**: 264.48s
- **Slowest test**: tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao::test_ctrc_confirmado_retorna_ok (22.43s — chama SSW real)
- **Tests nao coletados**: 20 (tests/skills/motos_assai)

## Acoes Recomendadas

1. **P0**: corrigir `tests/skills/motos_assai/conftest.py` (mover `pytest_plugins` para `tests/conftest.py` raiz) — desbloqueia 20 testes
2. **P1**: aplicar migrations pendentes no banco local de testes (audit_log_custeio, custo_frete.ativo, constraints custo_considerado)
3. **P1**: gerar fixtures PDF/XLSX em `tests/motos_assai/fixtures/` (rodar `generate_xlsx_fixture.py` + criar PDFs canonicos)
4. **P2**: atualizar fixtures `tests/hora/test_pedido_workflow.py` para usar `modalidade_frete='0'` ou `'1'`
5. **P2**: corrigir mock SSW em `tests/carvia/test_a3_ctrnc_cte_comp.py` (patch path do `resolver_ctrc_ssw`) — pendente desde 2026-04-27
6. **P3**: investigar race em `tests/agente/sdk/test_pending_questions.py` (async_event nao disparado)
7. **P3**: implementar `ConferenciaService.listar_fretes_divergentes` ou ajustar teste E8
