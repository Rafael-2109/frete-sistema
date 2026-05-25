# Atualizacao Tests — 2026-05-25-1

**Data**: 2026-05-25
**Total**: 1699 tests (+1 ImportError de coleta ignorado)
**Passed**: 1610 | **Failed**: 34 | **Error**: 48 | **Skipped**: 7
**Taxa de sucesso**: 94.76% (1610 / 1699)
**Tempo total**: 571.33s (~9m31s)

---

## Resumo

Suite executou completa em 9m31s com taxa de sucesso 94.76% (1610/1699). Antes da coleta, foi necessario excluir `tests/agente_lojas/test_todos_parser.py` (ImportError: `cannot import name '_try_parse_todos' from 'app.agente_lojas.sdk.client'` — funcao removida/renomeada no client). As 34 falhas concentram-se em `motos_assai` (28: 22 fixtures PDF/XLSX ausentes, 3 `vincular_nf_manualmente(loja_id=)` assinatura, 3 logica FASE3/FASE5/D5_match), `custeio` (2: state pollution + app context), `agente/sdk` (2: race async_event reincidente), `carvia` (1: `listar_fretes_divergentes` ausente reincidente), e **novo** `hora` (1: state pollution em `test_metricas_recebimento_tudo_ok`). Os 48 errors sao state pollution suite-wide: 34 em `hora` (UniqueViolation `hora_loja_cnpj_key`) e 14 em `motos_assai/test_carregamento_service_crud.py` (CompileError SQLite vs ARRAY em `agent_improvement_dialogue.affected_files`). **Sem correlacao com D4** — D4 modificou apenas `text_to_sql.py` (skill `consultando-sql`), que nao tem testes em `tests/`.

---

## Erro de Coleta (1 modulo IGNORADO)

### tests/agente_lojas/test_todos_parser.py
```
ImportError: cannot import name '_try_parse_todos'
from 'app.agente_lojas.sdk.client'
```
**Acao**: Modulo ignorado via `--ignore` para permitir execucao do restante.
**Causa**: Funcao `_try_parse_todos` nao existe (mais) em `client.py` do agente_lojas. Test desatualizado em relacao ao refactor da SDK.
**Recomendacao**: Reexportar simbolo em `app/agente_lojas/sdk/client.py` OU remover/atualizar test.
**Correlacao D4**: Nao.

---

## Falhas Detalhadas (34)

### Grupo 1 — agente/sdk (2 FAILED) — Race async_event reincidente

#### TestSubmitAnswer.test_submit_answer_signals_both_events (tests/agente/sdk/test_pending_questions.py)
- **Traceback**: `AssertionError: assert False` — `pq.async_event.is_set() == False` apos `submit_answer()`. `threading.Event` foi setado mas `asyncio.Event` nao chega a propagar.
- **Reincidente desde 2026-04-27 (5 ciclos)**.

#### TestCancelPending.test_cancel_pending_unblocks_async_event (tests/agente/sdk/test_pending_questions.py)
- **Traceback**: Mesma assinatura — `async_event.is_set() == False` apos `cancel_pending()`.
- **Reincidente**.

**Correlacao D4**: Nao.
**Causa raiz**: Race condition entre `threading.Event` e `asyncio.Event` em `PendingQuestion` (`app/agente/sdk/pending_questions.py`). Provavel fix: `loop.call_soon_threadsafe(async_event.set)`.

---

### Grupo 2 — carvia (1 FAILED) — Metodo ausente reincidente

#### TestE8FilaDivergente.test_listar_retorna_lista (tests/carvia/test_sprint_e_medio.py:118)
- **Traceback**: `AttributeError: 'ConferenciaService' object has no attribute 'listar_fretes_divergentes'`
- **Reincidente desde 2026-04-27 (5 ciclos)**.
- **Correlacao D4**: Nao.
- **Acao**: implementar metodo no `ConferenciaService` ou atualizar test para nome atual.

---

### Grupo 3 — custeio (2 FAILED) — State pollution + app context

#### TestAlterarTipoCusto.test_aceita_tipo_manual (tests/custeio/test_regressao_sprint_1_2.py:102)
- **Traceback**: `psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "uq_custo_considerado_versao". Key (cod_produto, versao)=(TEST_C2_010, 1) already exists.`
- **Reincidente desde 2026-05-11**. Fixture nao limpa registro.

#### TestCalculoMargem.test_calcular_margem_aceita_campos_corretos (tests/custeio/test_regressao_sprint_1_2.py:245)
- **Traceback**: `AssertionError: assert 'margem_bruta' in {}` + log:
  ```
  RuntimeError: Working outside of application context.
    File "app/odoo/services/carteira_service.py", line 1367, in _calcular_margem_bruta
      frete_percentual = CustoFrete.buscar_percentual_vigente(incoterm, cod_uf)
    File "app/custeio/models.py", line 373, in buscar_percentual_vigente
      custo = CustoFrete.query.filter(...)
  ```
- **Reincidente**. Service usa `flask_sqlalchemy` mas teste nao push app context.

**Correlacao D4**: Nao.

---

### Grupo 4 — motos_assai (28 FAILED)

#### 4a) Fixtures PDF/XLSX ausentes (22 falhas, reincidente 4 ciclos)
Path comum: `tests/motos_assai/fixtures/`
- `pedido_voe_exemplo.pdf`
- `recibo_motochefe_exemplo.pdf`
- `recibo_motochefe_exemplo.xlsx`

Distribuicao por arquivo:
- `test_motochefe_recibo_pdf_extractor.py` (5): test_fixture_exists, test_extract_retorna_chassis, test_header_data_recibo, test_header_equipe_haroldo_sp, test_modelo_texto_dot_e_mia
- `test_pedido_service.py` (2): test_importar_pdf_voe_sucesso, test_importar_duplicado_falha
- `test_qpa_pedido_extractor.py` (10): test_fixture_exists, test_extract_retorna_38_lojas_x_3_modelos, test_header_global_consistente, test_lojas_unicas_38, test_codigos_qpa_3_modelos, test_qtd_x11_mini_e_10_por_loja, test_qtd_dot_e_14_por_loja, test_valor_unitario_dot, test_validate_aceita_item_valido, test_zero_warnings_zero_errors_em_pdf_canonico
- `test_recibo_service.py` (5): test_importar_pdf_recibo, test_importar_xlsx_recibo, test_tipo_arquivo_invalido, test_s3_upload_ocorre_apos_parsing, test_recibo_sem_chassis_levanta_erro

**Causa**: Fixtures nao versionadas no repositorio. Reincidente desde 2026-05-11.
**Correlacao D4**: Nao.

#### 4b) `vincular_nf_manualmente(loja_id=...)` assinatura (3 falhas, reincidente 2 ciclos)
- `test_vincular_nf_manual.py::test_vincular_nf_nao_reconciliado_cria_sep_em_faturada`
- `test_vincular_nf_manual.py::test_vincular_nf_ja_bateu_falha`
- `test_vincular_nf_manual.py::test_vincular_nf_pedido_inexistente_falha`

**Traceback**: `TypeError: vincular_nf_manualmente() got an unexpected keyword argument 'loja_id'`
**Causa**: Service refatorado, tests nao atualizados desde 2026-05-18.

#### 4c) Bugs de logica (3 falhas, reincidente 2 ciclos)

##### test_carregamento_finalizar_fase3.py::test_fase3_excedente_remove_LIFO_outras_seps
- **Traceback**: `AssertionError: assert {'TST_F3N2_34551AA2', 'TST_F3N1_D9B39001'} == {'TST_F3O_D4918E53'}`
- LIFO removeu 2 seps mais novas em vez da mais antiga.

##### test_carregamento_finalizar_fase4_5_6.py::test_fase5_excel_versao_1_quando_nao_havia_anterior
- **Traceback**: `AssertionError: assert 'Carregamento finalizado' in (('Carregamento 410 finalizado'))`
- Texto da mensagem mudou (inclui id).

##### test_match_v2_cenarios.py::test_d5_match_ignora_sep_faturada
- **Traceback**: `assert None is not None`
- Match v2 retorna `None` quando deveria reconciliar (cenario D5 — sep ja faturada).

**Correlacao D4**: Nao.

---

### Grupo 5 — hora (1 FAILED — NOVO em 2026-05-25)

#### test_recebimento_reprocessamento.py::test_metricas_recebimento_tudo_ok (linha 326)
- **Traceback**: `sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "hora_loja_cnpj_key". Key (cnpj)=(11111111000101) already exists.`
- **NOVO**: Mesmo padrao dos 34 ERRORs do bloco hora (state pollution `hora_loja_cnpj_key`), porem classificado como FAILED em vez de ERROR — assertion ocorre apos setup parcial.
- **Correlacao D4**: Nao.

---

## Errors Detalhados (48 — falhas de setup/teardown)

### Grupo A — hora (34 ERROR) — `hora_loja_cnpj_key` UniqueViolation

Todos os tests `tests/hora/test_*` (avaria_service, chassi_protecao, estoque_eventos_em_estoque, moto_service_novos_tipos, transferencia_service) falham no setup com:

```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation)
duplicate key value violates unique constraint "hora_loja_cnpj_key"
DETAIL:  Key (cnpj)=(11111111000101) already exists.
```

**Causa**: Fixture cria loja com CNPJ unico fixo (`11111111000101`); run anterior deixou linha persistida.
**Reincidente desde 2026-05-11**.

Distribuicao (identica a 2026-05-18):
- `test_avaria_service.py`: 10 errors
- `test_chassi_protecao.py`: 3 errors
- `test_estoque_eventos_em_estoque.py`: 3 errors
- `test_moto_service_novos_tipos.py`: 3 errors
- `test_transferencia_service.py`: 15 errors

**Correlacao D4**: Nao.

---

### Grupo B — motos_assai/test_carregamento_service_crud.py (14 ERROR) — ARRAY incompativel com SQLite

```
sqlalchemy.exc.CompileError:
(in table 'agent_improvement_dialogue', column 'affected_files'):
Compiler SQLiteTypeCompiler can't render element of type ARRAY
```

**Causa**: Coluna `affected_files` declarada como `ARRAY` (Postgres-only). Tests configurados com `DATABASE_URL=sqlite:///:memory:` (pytest.ini).
**MUDANCA vs 2026-05-18**: Antes o erro apontava `usuarios.preferences` JSONB; agora aponta `agent_improvement_dialogue.affected_files` ARRAY. JSONB foi resolvido entre execucoes, mas novo problema emergiu em outra tabela.

Distribuicao: 14 errors, todos em `test_carregamento_service_crud.py`:
test_criar_carregamento_sucesso, test_criar_carregamento_pedido_inexistente, test_criar_carregamento_loja_inexistente, test_criar_carregamento_dois_paralelos_mesma_loja_OK, test_escanear_chassi_disponivel_sucesso, test_escanear_chassi_inexistente_falha, test_escanear_chassi_em_outro_carregamento_ativo_falha, test_escanear_carregamento_finalizado_falha, test_cancelar_item_sucesso, test_cancelar_item_carregamento_finalizado_falha, test_cancelar_carregamento_em_carregamento_chassi_volta_anterior, test_cancelar_carregamento_finalizado_chassis_mantem_separada, test_cancelar_carregamento_motivo_obrigatorio, test_cancelar_carregamento_ja_cancelado_nao_idempotente.

**Correlacao D4**: Nao.

---

## Skipped (7 testes)

Output `console_output_style=progress` nao lista explicitamente — sumario confirma 7 skipped, mesma quantidade desde 2026-04-27 (testes condicionais por flag/env).

---

## Correlacao com Dominio 4 (Sentry)

D4 status (`/tmp/manutencao-2026-05-25/dominio-4-status.json`):
- `issues_corrigidas: 1` (PYTHON-FLASK-M5)
- `arquivos_modificados`:
  - `.claude/skills/consultando-sql/scripts/text_to_sql.py`
  - `.claude/atualizacoes/sentry/atualizacao-2026-05-25-1.md`
  - `.claude/atualizacoes/sentry/historico.md`

**Verificacao**:
- Busca em todos os FAILED/ERROR por strings `consultando-sql`, `text_to_sql`, `SQLDeterministic`: **0 matches**
- `tests/skills/` contem apenas testes SPED ECD e motos_assai — sem cobertura para `text_to_sql.py`

**Conclusao: Nenhuma correlacao**. Fix do D4 nao tem testes automatizados associados; validacao foi via suite inline (6 casos) conforme documentado no relatorio D4.

---

## Metricas

| Metrica | Valor |
|---------|-------|
| Tempo total | 571.33s (~9m31s) |
| Testes coletados | 1699 (+ 1 ImportError ignorado) |
| Passed | 1610 (94.76%) |
| Failed | 34 (2.00%) |
| Error (setup/teardown) | 48 (2.82%) |
| Skipped | 7 (0.41%) |
| Slowest test 1 | `test_e2e_parse_v21` agente/sped (9.17s) |
| Slowest test 2 | `test_e2e_audit_balance_v21` agente/sped (9.04s) |
| Slowest test 3 | `test_rejeitar_sugestao` pallet (8.43s) |
| Slowest test 4 | `test_confirmar_sugestao` pallet (7.60s) |
| Slowest test 5 | `test_listar_abertos` skills/motos_assai (7.54s) |

---

## Comparacao com Execucao Anterior (2026-05-18)

| Metrica | 2026-05-18 | 2026-05-25 | Delta |
|---------|------------|------------|-------|
| Total | 1414 | 1699 | +285 |
| Passed | 1326 | 1610 | +284 |
| Failed | 33 | 34 | +1 |
| Error | 48 | 48 | 0 |
| Skipped | 7 | 7 | 0 |
| Taxa sucesso | 93.78% | 94.76% | +0.98pp |
| Tempo total | 563.72s | 571.33s | +1.4% |

**Observacoes**:
- +285 testes coletados — crescimento natural da suite (provavelmente skills motos_assai, agente_lojas).
- Failed praticamente estavel (+1 — novo `hora.test_metricas_recebimento_tudo_ok` state pollution).
- Errors mantidos em 48 (34 hora + 14 motos_assai), porem o bloco motos_assai trocou de natureza (JSONB->ARRAY em outra tabela).
- Taxa de sucesso +0.98pp graças ao crescimento da base com tests novos passando.
- Tempo praticamente identico (+1.4%).
- 1 novo ImportError de coleta (`tests/agente_lojas/test_todos_parser.py`).

---

## Acao Recomendada

1. **P0** — Fix `tests/agente_lojas/test_todos_parser.py` (1 linha — re-exportar simbolo `_try_parse_todos` em `app/agente_lojas/sdk/client.py` OU remover test). NOVO em 2026-05-25.
2. **P0** — Cleanup state pollution `hora_loja_cnpj_key` (35 testes — 34 ERRORs + 1 FAILED): fixture deve usar CNPJ randomico ou `tearDown` agressivo. Reincidente 3 ciclos.
3. **P0** — Fix ARRAY/SQLite em `agent_improvement_dialogue.affected_files` (14 errors): trocar por `db.JSON` neutro ou condicionar tipo por dialect.
4. **P0** — Limpar DB local: `DELETE FROM custo_considerado WHERE cod_produto='TEST_C2_010'` (1 falha custeio).
5. **P1** — Versionar fixtures PDF/XLSX em `tests/motos_assai/fixtures/` (22 falhas). Reincidente 4 ciclos.
6. **P1** — Atualizar `tests/motos_assai/test_vincular_nf_manual.py` para nova assinatura sem `loja_id` (3 falhas).
7. **P2** — Race async_event em `pending_questions.py` — usar `loop.call_soon_threadsafe(async_event.set)` (2 falhas reincidentes 5 ciclos).
8. **P2** — Implementar `ConferenciaService.listar_fretes_divergentes` ou atualizar test (1 falha reincidente 5 ciclos).
9. **P2** — Adicionar `app.app_context()` em `TestCalculoMargem` ou marcar como `@pytest.mark.integration` (1 falha custeio).
10. **P2** — Bugs logica motos_assai (LIFO FASE3, mensagem FASE5, match v2 D5) — investigar 3 reincidentes.
