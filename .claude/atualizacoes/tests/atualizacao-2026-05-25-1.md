# Atualizacao Tests — 2026-05-25-1

**Data**: 2026-05-25
**Total coletado**: 1699 testes (1 collection error em `tests/agente_lojas/test_todos_parser.py` — ignorado na execucao); 1699 efetivos
**Passed**: 1611 | **Failed**: 33 | **Error**: 48 | **Skipped**: 7
**Taxa de sucesso**: 94.82% (1611 / (1611 + 33 + 48))
**Tempo total**: 561.63s (~9min 21s)

## Resumo

Suite executou completa apos ignorar 1 modulo com collection error (`test_todos_parser.py`
importa `_try_parse_todos` que nao existe em `app/agente_lojas/sdk/client.py`). Resultado e
**reproducao quase identica do baseline 2026-05-18** — mesmos 33 FAILED + 48 ERROR + 7 SKIPPED.
Nenhuma correlacao com D4 (Sentry triagem so modificou `text_to_sql.py` do skill
`consultando-sql`, que nao tem testes em `tests/`). Falhas persistentes sao state pollution
em fixtures (`hora_loja_cnpj_key`, `uq_custo_considerado_versao`), incompatibilidade
SQLite x ARRAY/JSONB em `agent_improvement_dialogue.affected_files`, fixtures PDF/XLSX
ausentes em `motos_assai`, e bugs de logica reincidentes (FASE3/FASE5/D5 carregamento, race
async_event em pending_questions).

## Collection Error (Pre-execucao)

### tests/agente_lojas/test_todos_parser.py
- **Causa**: `ImportError: cannot import name '_try_parse_todos' from 'app.agente_lojas.sdk.client'`
- **Acao**: Modulo ignorado via `--ignore` para permitir execucao do restante da suite
- **Recomendacao**: Reexportar `_try_parse_todos` em `app/agente_lojas/sdk/client.py` OU
  remover/atualizar o teste

## Falhas Detalhadas (33)

### Grupo 1 — agente/sdk (2 FAILED) — Race condition async_event reincidente

#### TestSubmitAnswer.test_submit_answer_signals_both_events (tests/agente/sdk/test_pending_questions.py:101)
- **Traceback**: `AssertionError: assert pq.async_event.is_set() == False`
- **Detalhe**: Resposta marcada em `threading.Event` mas `asyncio.Event` nao foi
  sinalizado (subscriber thread terminou antes de propagar). Reincidente desde 2026-05-11.
- **Correlacao D4**: Nao

#### TestCancelPending.test_cancel_pending_unblocks_async_event (tests/agente/sdk/test_pending_questions.py:189)
- **Traceback**: Mesmo padrao acima — cancel sinaliza `threading.Event` mas nao
  `asyncio.Event`. Reincidente.
- **Correlacao D4**: Nao

### Grupo 2 — carvia (1 FAILED) — Metodo ausente reincidente

#### TestE8FilaDivergente.test_listar_retorna_lista (tests/carvia/test_sprint_e_medio.py:118)
- **Traceback**: `AttributeError: 'ConferenciaService' object has no attribute 'listar_fretes_divergentes'`
- **Detalhe**: Metodo removido/renomeado, teste nao atualizado. Reincidente desde 2026-05-11.
- **Correlacao D4**: Nao

### Grupo 3 — custeio (2 FAILED) — State pollution + app context

#### TestAlterarTipoCusto.test_aceita_tipo_manual (tests/custeio/test_regressao_sprint_1_2.py:102)
- **Traceback**: `IntegrityError: duplicate key value violates unique constraint "uq_custo_considerado_versao"` — Key `(cod_produto, versao)=(TEST_C2_010, 1) already exists`
- **Detalhe**: Fixture nao limpa registros entre execucoes; depende de transacao rollback. Reincidente.
- **Correlacao D4**: Nao

#### TestCalculoMargem.test_calcular_margem_aceita_campos_corretos (tests/custeio/test_regressao_sprint_1_2.py:245)
- **Traceback**: `AssertionError: assert 'margem_bruta' in {}` — `_calcular_margem_bruta` levanta
  `RuntimeError: Working outside of application context` ao chamar `CustoFrete.query` sem
  `app.app_context()`
- **Detalhe**: Service usa `flask_sqlalchemy` mas teste nao push app context. Reincidente.
- **Correlacao D4**: Nao

### Grupo 4 — motos_assai (28 FAILED) — Fixtures PDF/XLSX ausentes (22) + logica (6)

#### Fixtures ausentes (22)
Path comum: `tests/motos_assai/fixtures/{pedido_voe_exemplo.pdf,recibo_motochefe_exemplo.{pdf,xlsx}}`

- test_motochefe_recibo_pdf_extractor.py (5): test_fixture_exists, test_extract_retorna_chassis, test_header_data_recibo, test_header_equipe_haroldo_sp, test_modelo_texto_dot_e_mia
- test_pedido_service.py (2): test_importar_pdf_voe_sucesso, test_importar_duplicado_falha
- test_qpa_pedido_extractor.py (10): test_fixture_exists, test_extract_retorna_38_lojas_x_3_modelos, test_header_global_consistente, test_lojas_unicas_38, test_codigos_qpa_3_modelos, test_qtd_x11_mini_e_10_por_loja, test_qtd_dot_e_14_por_loja, test_valor_unitario_dot, test_validate_aceita_item_valido, test_zero_warnings_zero_errors_em_pdf_canonico
- test_recibo_service.py (5): test_importar_pdf_recibo, test_importar_xlsx_recibo, test_tipo_arquivo_invalido, test_s3_upload_ocorre_apos_parsing, test_recibo_sem_chassis_levanta_erro

**Detalhe**: PDFs/XLSX canonicos nao estao versionados no repositorio. Reincidente desde 2026-05-11.
**Correlacao D4**: Nao

#### Bugs de logica (6)

- test_carregamento_finalizar_fase3.py::test_fase3_excedente_remove_LIFO_outras_seps
  - `AssertionError: assert {'TST_F3N1_324E64F2', 'TST_F3N2_B2EFB21D'} == {'TST_F3O_2DAC2D36'}`
  - LIFO removeu 2 seps mais novas em vez da mais antiga. Reincidente.

- test_carregamento_finalizar_fase4_5_6.py::test_fase5_excel_versao_1_quando_nao_havia_anterior
  - `AssertionError: assert 'Carregamento finalizado' in (('Carregamento 385 finalizado'))`
  - Texto da mensagem mudou. Reincidente.

- test_match_v2_cenarios.py::test_d5_match_ignora_sep_faturada
  - `assert None is not None` — match nao retornou sep esperada. Reincidente.

- test_vincular_nf_manual.py (3): test_vincular_nf_nao_reconciliado_cria_sep_em_faturada, test_vincular_nf_ja_bateu_falha, test_vincular_nf_pedido_inexistente_falha
  - `TypeError: vincular_nf_manualmente() got an unexpected keyword argument 'loja_id'`
  - Assinatura divergente entre teste e producao. Reincidente.

**Correlacao D4**: Nao

## Errors (48 — falhas de setup/teardown)

### Grupo A — hora (34 ERROR) — `hora_loja_cnpj_key` UniqueViolation
Arquivos afetados: test_avaria_service.py (10), test_chassi_protecao.py (3),
test_estoque_eventos_em_estoque.py (3), test_moto_service_novos_tipos.py (3),
test_transferencia_service.py (15).

- **Causa**: Fixture cria `hora_loja` com CNPJ ja existente; rollback de testes anteriores nao limpa
- **Detalhe**: Bug de setup compartilhado em `tests/hora/conftest.py` ou fixture session-scope
- **Reincidente desde 2026-05-11**
- **Correlacao D4**: Nao

### Grupo B — motos_assai/test_carregamento_service_crud.py (14 ERROR) — ARRAY incompativel com SQLite

- **Causa**: `CompileError: (in table 'agent_improvement_dialogue', column 'affected_files'): Compiler SQLiteTypeCompiler can't render element of type ARRAY`
- **Detalhe**: Coluna `affected_files` declarada como `ARRAY` (Postgres), nao tem fallback p/ SQLite.
  Tests configurados em `pytest.ini` com `DATABASE_URL=sqlite:///:memory:`.
- **Reincidente desde 2026-05-18**
- **Correlacao D4**: Nao

## Correlacao com Dominio 4 (Sentry Triagem)

Arquivo modificado pelo D4: `.claude/skills/consultando-sql/scripts/text_to_sql.py`
(fix em `SQLDeterministicValidator._check_qualified_fields` para resolver aliases SQL).

**Verificacao**:
- Busca em todos os FAILED/ERROR por strings `consultando-sql`, `text_to_sql`, `SQLDeterministic`: **0 matches**
- `tests/skills/` contem apenas testes SPED ECD (parseando/auditando/comparando) — sem cobertura para `text_to_sql.py`
- Conclusao: **Sem correlacao**. Fix do D4 nao tem testes automatizados associados; validacao foi via
  suite inline (6 casos) conforme documentado no relatorio D4.

## Metricas

- **Taxa de sucesso**: 94.82% (1611 / 1699 efetivos)
- **Reincidencia**: 100% das falhas/errors ja estavam presentes em 2026-05-18 (mesmo perfil)
- **Tempo total**: 561.63s
- **Top 3 testes mais lentos**:
  - test_e2e_audit_balance_v21 (agente/sped): 8.39s
  - test_e2e_parse_v21 (agente/sped): 7.87s
  - test_e2e_search_semantic_cnpj_rule (agente/sped): 1.73s

## Recomendacoes (prioridade)

1. **P0** — Fix collection error em `tests/agente_lojas/test_todos_parser.py` (1 linha — re-exportar simbolo ou remover teste)
2. **P0** — Fix `hora_loja_cnpj_key` state pollution em `tests/hora/conftest.py` (destrava 34 errors)
3. **P0** — Fix ARRAY/SQLite em `agent_improvement_dialogue.affected_files` (destrava 14 errors em motos_assai/carregamento)
4. **P1** — Versionar fixtures PDF/XLSX em `tests/motos_assai/fixtures/` ou marcar testes como `@pytest.mark.skip` (destrava 22 falhas)
5. **P1** — Atualizar `tests/motos_assai/test_vincular_nf_manual.py` para nova assinatura sem `loja_id` (3 falhas)
6. **P2** — Investigar race async_event em `pending_questions` (2 falhas reincidentes ha 2+ ciclos)
7. **P2** — Remover/renomear `ConferenciaService.listar_fretes_divergentes` (1 falha reincidente)
8. **P2** — Adicionar `app.app_context()` em `TestCalculoMargem` ou marcar como `@pytest.mark.integration`
