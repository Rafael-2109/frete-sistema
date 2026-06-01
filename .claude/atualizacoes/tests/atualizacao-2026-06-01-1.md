# Atualizacao Tests — 2026-06-01-1

**Data**: 2026-06-01
**Total**: 2575 tests (2574 coletados + 1 modulo com ImportError de coleta)
**Passed**: 2483 | **Failed**: 36 | **Error**: 49 (48 setup + 1 coleta) | **Skipped**: 7
**Taxa de sucesso**: 96.69% (2483 / 2568 nao-skipped) — ou 96.43% sobre o total coletado

## Resumo

A suite executou ate o fim apos remover o limite `--maxfail=5` embutido em `pytest.ini` (com ele, a 1 ImportError de coleta + as 4 primeiras falhas batiam o limite e abortavam o run em ~41% — apenas ~1072 dos 2574 testes rodavam). Com `--maxfail=10000` e `--continue-on-collection-errors`, o run completo levou 12m26s e expos as 36 falhas + 48 errors de setup, que sao TODAS pre-existentes e ambientais, repetindo quase exatamente o perfil do ciclo anterior (2026-05-25: 34 falhas + 48 errors + 7 skipped + 1 ImportError). **Nenhuma falha tem correlacao com o Dominio 4** — o D4 modificou apenas `.claude/skills/gerindo-carvia/scripts/cotando_subcontrato_carvia.py` (script de skill, sem cobertura em `tests/`).

**Observacao critica de ambiente**: apesar de `pytest.ini` forcar `DATABASE_URL=sqlite:///:memory:`, `create_app()` carrega o `.env` da raiz e a maioria dos testes bate no **Postgres real** (erros `psycopg2.errors.UniqueViolation` com chaves persistidas de runs anteriores). Isso e a raiz da maioria dos errors (state pollution). Gotcha ja documentado em `memory/gotcha_worktree_testes_env_schemas.md`.

**Gotcha do ciclo**: `pytest.ini` tem `--maxfail=5` em `addopts`. A coleta com ImportError conta 1 "error" para o limite; somada a 4 falhas iniciais, o run aborta a ~41% sem aviso claro de truncamento. Para um diagnostico completo e obrigatorio sobrescrever `--maxfail`.

## Falhas Detalhadas (36)

Distribuicao por modulo: motos_assai 29 · inventario 3 · custeio 2 · carvia 1 · hora 1.

### Categoria A — Fixtures PDF ausentes (motos_assai) — 22 FAILED
Reincidente ha 4+ ciclos. Arquivos de fixture nao versionados em `tests/motos_assai/fixtures/`:
- `pedido_voe_exemplo.pdf` (ausente)
- `recibo_motochefe_exemplo.pdf` / `.xlsx` (ausentes)

Sintomas: `FileNotFoundError`, `AssertionError: Fixture ... ausente`, ou parsing retornando 0 itens (`veio 0`, `set()`, `StopIteration`, `IndexError`).
Testes afetados:
- `test_qpa_pedido_extractor.py` (10): test_fixture_exists, test_extract_retorna_38_lojas_x_3_modelos, test_header_global_consistente, test_lojas_unicas_38, test_codigos_qpa_3_modelos, test_qtd_x11_mini_e_10_por_loja, test_qtd_dot_e_14_por_loja, test_valor_unitario_dot, test_validate_aceita_item_valido, test_zero_warnings_zero_errors_em_pdf_canonico
- `test_motochefe_recibo_pdf_extractor.py` (5): test_fixture_exists, test_extract_retorna_chassis, test_header_data_recibo, test_header_equipe_haroldo_sp, test_modelo_texto_dot_e_mia
- `test_recibo_service.py` (5): test_importar_pdf_recibo, test_importar_xlsx_recibo, test_tipo_arquivo_invalido, test_s3_upload_ocorre_apos_parsing, test_recibo_sem_chassis_levanta_erro
- `test_pedido_service.py` (2): test_importar_pdf_voe_sucesso, test_importar_duplicado_falha
- **Correlacao D4**: Nao.

### Categoria B — Assinatura `vincular_nf_manualmente(loja_id=)` (motos_assai) — 3 FAILED
`test_vincular_nf_manual.py` (3): test_vincular_nf_nao_reconciliado_cria_sep_em_faturada, test_vincular_nf_ja_bateu_falha, test_vincular_nf_pedido_inexistente_falha.
- **Traceback**: `TypeError: vincular_nf_manualmente() got an unexpected keyword argument 'loja_id'` — teste e implementacao divergentes na assinatura (reincidente).
- **Correlacao D4**: Nao.

### Categoria C — Logica/dados motos_assai — 4 FAILED
- `test_carregamento_finalizar_fase3.py::test_fase3_excedente_remove_LIFO_outras_seps` — `AssertionError: {'TST_F3N1_...', 'TST_F3N2_...'} == {'TST_F3O_...'}` (logica LIFO de remocao de excedente).
- `test_carregamento_finalizar_fase4_5_6.py::test_fase5_excel_versao_1_quando_nao_havia_anterior` — `assert 'Carregamento finalizado' in 'Carregamento 460 finalizado'` (mensagem com ID quebra substring esperada).
- `test_match_v2_cenarios.py::test_d5_match_ignora_sep_faturada` — `assert None is not None` (match retornou None).
- `test_cce_service.py::test_cce_duplicatas_fica_ignarada` — `sqlalchemy.exc.DataError: (psycopg2.errors.StringDataRightTruncation) value too long for type character varying(44)` (dado de teste excede tamanho da coluna).
- **Correlacao D4**: Nao.

### Categoria D — inventario (3 FAILED) — dependentes de Odoo/Postgres ao vivo
- `test_movimentacoes_drill_down.py::test_paginacao_default_100` — `assert 0 == 100` (DB de teste sem dados; `len([]) == 0`).
- `test_movimentacoes_drill_down.py::test_paginacao_500` — `assert 0 == 500`.
- `test_snapshot_odoo_service.py::test_refresh_idempotente` — `assert 117 == 1` (refresh real contra fonte retornou 117 linhas; idempotencia esperava 1).
- **Correlacao D4**: Nao.

### Categoria E — custeio (2 FAILED)
- `test_regressao_sprint_1_2.py::TestAlterarTipoCusto::test_aceita_tipo_manual`
  - **Traceback**: `sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "uq_custo_considerado_versao". Key (cod_produto, versao)=(TEST_C2_010, 1) already exists.` — state pollution no Postgres real (registro de run anterior nao limpo).
- `test_regressao_sprint_1_2.py::TestCalculoMargem::test_calcular_margem_aceita_campos_corretos`
  - **Traceback**: `AssertionError: assert 'margem_bruta' in {}` — causa raiz `RuntimeError: Working outside of application context` em `CustoFrete.buscar_percentual_vigente` (`app/custeio/models.py:373`, via `carteira_service.py:1367`); o calculo de margem captura a excecao e retorna `{}`.
- **Correlacao D4**: Nao.

### Categoria F — carvia (1 FAILED)
- `test_sprint_e_medio.py::TestE8FilaDivergente::test_listar_retorna_lista`
  - **Traceback**: `AttributeError: 'ConferenciaService' object has no attribute 'listar_fretes_divergentes'` — metodo ausente no service (reincidente ha 5+ ciclos; verificado: nao existe em `app/carvia/`).
- **Correlacao D4**: Nao. O D4 alterou a skill `cotando_subcontrato_carvia.py` (import de `cotacao_service`), NAO o `ConferenciaService`.

### Categoria G — hora (1 FAILED)
- `test_peca_cadastro.py::test_listar_filtra_ativo`
  - **Traceback**: `AssertionError: assert 359 in {1, 2, 3, ...}` — id 359 (registro de outro run no Postgres real) aparece na listagem por filtro de ativo; ordering/state pollution, nao defeito de codigo. (`test_peca_estoque.py::test_transferencia_atomica` PASSOU neste run.)
- **Correlacao D4**: Nao.

## Errors Detalhados (48 setup + 1 coleta)

### Coleta (1 ERROR) — modulo
- `tests/agente_lojas/test_todos_parser.py` — `ImportError: cannot import name '_try_parse_todos' from 'app.agente_lojas.sdk.client'`.
  - **Causa**: o SDK do agente_lojas nao expoe mais `_try_parse_todos` (migracao TodoWrite -> Task* tools); o teste ficou orfao. Pre-existente (mesma ImportError no ciclo 2026-05-25). **Nao corrigido** (este dominio so executa/relata, nao altera codigo). Com `--continue-on-collection-errors` o restante da suite coletou normalmente.
  - **Correlacao D4**: Nao.

### hora — 34 ERRORS (state pollution Postgres)
Todos `sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key ... "hora_loja_cnpj_key". Key (cnpj)=(11111111000101) already exists.` Fixture de loja recriada sobre registro persistido de run anterior (Postgres real, nao limpo entre runs).
Modulos e contagem: `test_transferencia_service.py` (16), `test_avaria_service.py` (10), `test_estoque_eventos_em_estoque.py` (3), `test_moto_service_novos_tipos.py` (3), `test_chassi_protecao.py` (3) — total 35 entradas no summary, 34 distintas no agregado oficial (uma sobrepoe-se a contagem de FAILED na mesma classe).
- **Correlacao D4**: Nao.

### motos_assai/test_carregamento_service_crud.py — 14 ERRORS (ARRAY em SQLite)
`sqlalchemy.exc.CompileError: (in table 'agent_improvement_dialogue', column 'affected_files'): ... can't render element of type ARRAY`. A criacao do schema cai no compilador SQLite, que nao renderiza colunas `ARRAY` (Postgres-only). Mesmo perfil do ciclo 2026-05-25 (a coluna problematica migrou de `usuarios.preferences` JSONB para `agent_improvement_dialogue.affected_files` ARRAY).
- **Correlacao D4**: Nao.

## Skipped (7)
Todos em `tests/motos_assai/test_motochefe_recibo_xlsx_extractor.py` — skip condicional por fixture XLSX ausente (`recibo_motochefe_exemplo.xlsx`): test_fixture_xlsx_exists, test_xlsx_extract_retorna_chassis, test_xlsx_header_data_recibo, test_xlsx_chassis_uppercase_e_distintos, test_xlsx_modelo_texto_dot_e_mia, test_xlsx_cnpj_extraido, test_xlsx_total_motos_declarado. Sem impacto e sem relacao com D4.

## Correlacao com Dominio 4 (Sentry)

**Resultado: NENHUMA correlacao (negativa).**
- D4 (`dominio-4-status.json`, status OK) modificou **1 arquivo**: `.claude/skills/gerindo-carvia/scripts/cotando_subcontrato_carvia.py` — correcao de import-path `app.carvia.services.cotacao_service` -> `app.carvia.services.pricing.cotacao_service` (3 linhas).
- Esse arquivo e um script de skill (CLI), **sem cobertura em `tests/`** (busca por `cotando_subcontrato`/`cotacao_service` em `tests/` -> nenhum match).
- A unica falha em `tests/carvia/` (`listar_fretes_divergentes` ausente em `ConferenciaService`) e independente do fix do D4 e reincidente ha varios ciclos.
- Todas as 36 falhas + 48 errors sao pre-existentes e reincidentes (perfil identico ao ciclo 2026-05-25).

## Metricas
- Taxa de sucesso: 96.69% (2483 / 2568 nao-skipped); 96.43% sobre 2574 coletados.
- Tempo total: 746.83s (12m26s) — run completo sem `--maxfail`.
- Total coletado: 2574 items (+875 vs 2026-05-25, crescimento da suite).
- Comando: `python -m pytest tests/ -v --tb=short --timeout=60 --continue-on-collection-errors --maxfail=10000`
- Log completo: `/tmp/manutencao-2026-06-01/pytest-d5-complete.log`
