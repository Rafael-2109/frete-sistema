# Atualizacao Tests — 2026-06-29-1

**Data**: 2026-06-29
**Total**: 5456 tests (5417 passed + 4 failed + 35 skipped)
**Passed**: 5417 | **Failed**: 4 | **Error**: 0 | **Skipped**: 35
**Taxa de sucesso**: 99.93% (non-skipped: 5417/5421 = 99.93%)
**Tempo total**: 942.47s (15m42s)

## Resumo

Suite executou COMPLETA pela primeira vez em varios ciclos (3752 -> 4329 -> 5456 coletados; +1127 vs 2026-06-15) com perfil **drasticamente mais saudavel**: 4 falhas vs 89+48 (06-08), 36+48 (06-01), 33-34+48 (05-18/05-25). **As falhas cronicas de DB-state pollution sumiram** — hora (`hora_loja_cnpj_key`), motos_assai/carregamento (`agent_improvement_dialogue.affected_files` ARRAY em SQLite), custeio (`uq_custo_considerado_versao`), carvia (`listar_fretes_divergentes`) e a migration `separacao.equipe_vendas` NAO apareceram neste run (ambiente de teste limpo, sem state pollution Postgres). As 4 falhas restantes sao **meta-testes de toolchain/lint/flag-drift**, NAO logica de negocio: 2 de drift de env var em `feature_flags.py`, 1 timeout do `doc_audit.py` (reincidente do ciclo 06-08), 1 de doc sem TOC (C6). **Sem correlacao D4** — todos os testes que exercitam o arquivo modificado pelo D4 (`consultar_quants.py`) PASSARAM.

## Falhas Detalhadas

### test_default_da_flag_judge_source_e_off (tests/agente/services/test_directive_promotion.py:556)
- **Traceback**: `AssertionError: AGENT_DIRECTIVE_JUDGE_SOURCE deve existir com default 'false' (R3)` — `assert None where None = re.search('AGENT_DIRECTIVE_JUDGE_SOURCE\s*=\s*os.getenv("AGENT_DIRECTIVE_JUDGE_SOURCE", "false"', ff_src)`.
- **Natureza**: meta-teste — le `app/agente/config/feature_flags.py` como texto e exige que a flag `AGENT_DIRECTIVE_JUDGE_SOURCE` esteja declarada com default `"false"` no formato exato do regex. O padrao nao foi encontrado no fonte (a flag nao esta declarada com esse nome/forma, ou foi renomeada). Drift de declaracao de flag, NAO regressao de comportamento.
- **Correlacao D4**: Nao. (O grep por "quant" casou este arquivo so incidentalmente; a falha e sobre env var de directive judge, sem relacao com `consultar_quants.py`.)

### test_infra_evolution_flags_confronta_feature_flags (tests/agente/test_gerindo_agente_skill.py:500)
- **Traceback**: `AssertionError: feature_flags.py: nao achei os.getenv('AGENT_CAPABILITY_REGISTRY', 'false') — drift de env var ou default de USE_CAPABILITY_REGISTRY?`
- **Natureza**: mesmo tipo — confronta a skill `gerindo-agente` (infra evolution flags) com `feature_flags.py` e exige `os.getenv('AGENT_CAPABILITY_REGISTRY', 'false')`. A mensagem do proprio teste aponta a causa: drift de nome de env var (provavel `USE_CAPABILITY_REGISTRY` vs `AGENT_CAPABILITY_REGISTRY`). Doc/flag-drift, NAO logica.
- **Correlacao D4**: Nao.

### test_doc_audit_report_only_roda (tests/audits/test_artefato_cli.py:7)
- **Traceback**: `Failed: Timeout (>60.0s) from pytest-timeout.`
- **Natureza**: roda `scripts/audits/doc_audit.py --report-only --path docs/superpowers/specs` como subprocesso; o passo de near-duplicate (O(n^2), sem `--skip-dup`) excede o `--timeout=60`. **Reincidente** — o ciclo 2026-06-08 ja registrou `doc_audit.py` estourando 60s (3m21s naquele run). Ambiental/performance do script de auditoria, NAO regressao de produto.
- **Correlacao D4**: Nao.

### test_c6_zerado_apos_isencao_skill_md (tests/audits/test_onda4a_toolchain.py:31)
- **Traceback**: `AssertionError: C6 deve estar zerado (SKILL.md isento); achou 3:` — `['C6 block .claude/skills/baixando-credores-lote-odoo/DESIGN.md:1 arquivo 109 linhas sem TOC', 'C6 block app/agente/services/CLAUDE.md:1 arquivo 216 linhas sem TOC', 'C6 block docs/roteirizacao/ESTADO.md:1 arquivo 182 linhas sem TOC']`.
- **Natureza**: o check C6 do toolchain de auditoria (arquivos longos sem indice/TOC) deveria estar zerado apos isentar `SKILL.md`, mas 3 docs NAO-SKILL.md (DESIGN.md, CLAUDE.md de services do agente, ESTADO.md de roteirizacao) ultrapassaram o limite de linhas sem TOC. **Doc-drift** (docs novos/crescidos sem indice), NAO codigo de aplicacao.
- **Correlacao D4**: Nao.

## Correlacao com Dominio 4 (Sentry)

- D4 (`/tmp/manutencao-2026-06-29/dominio-4-status.json`, status OK) modificou **1 arquivo**: `.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py` (fix Z8 — `json.dumps` com chave-tupla, achatada em `'cod|empresa'` so no ramo JSON).
- Testes que exercitam esse arquivo / skill, **todos PASSARAM**:
  - `tests/skills/test_cli_json_alias.py::test_quants_json_alias_forca_json` PASSED (exercita diretamente o CLI de `consultar_quants.py`)
  - `tests/skills/test_cli_json_alias.py::test_quants_default_tabela` / `test_quants_formato_explicito_preservado` PASSED
  - `tests/odoo/services/test_stock_quant_query_service.py` (21 testes) PASSED
  - `tests/agente/test_permissions_estoque_restricao.py` (33 testes, inclui `test_user_5_pode_consultar_quant`) PASSED
- **Conclusao**: ZERO correlacao positiva. O fix do D4 nao introduziu regressao detectavel pela suite; as 4 falhas sao independentes (flag-drift + doc-toolchain).

## Skips (35) — todos ambientais

- `tests/motos_assai/test_motochefe_recibo_pdf_extractor.py` (11) + `test_motochefe_recibo_xlsx_extractor.py` (7) + `test_qpa_pedido_extractor.py` (11) + `test_pedido_service.py` (2) + `test_recibo_service.py` (3): fixtures PDF/XLSX ausentes no ambiente de teste (reincidente desde 2026-05-11; dir `tests/motos_assai/fixtures/` nao populado local).
- `tests/embeddings/test_memory_search_cold_filter.py::test_busca_fallback_exclui_memoria_fria` (1): skip de embeddings/cold filter (dependencia de ambiente).

## Metricas

- Taxa de sucesso (sobre executados, excl. skips): **99.93%** (5417/5421)
- Taxa sobre coletados: **99.27%** (5417/5456)
- Falhas: 4 (0.07% dos executados) — 0 ERROR
- Tempo total: **942.47s (15m42s)**
- Coletados: 5456 (+1127 vs 2026-06-15 que coletou 4329)
- Log completo: `/tmp/manutencao-2026-06-29/pytest-full-output.log`

## Acoes recomendadas (nao bloqueantes — todas fora de produto)

1. **flag-drift** (2 testes): reconciliar `app/agente/config/feature_flags.py` — declarar `AGENT_DIRECTIVE_JUDGE_SOURCE` e `AGENT_CAPABILITY_REGISTRY` com default `"false"`, OU atualizar os 2 testes se as flags foram renomeadas (a 2a mensagem sugere `USE_CAPABILITY_REGISTRY`).
2. **doc_audit timeout** (1 teste, reincidente): passar `--skip-dup` no comando do teste OU subir o `--timeout` so para `tests/audits/test_artefato_cli.py` (o near-dup O(n^2) e o gargalo conhecido).
3. **C6 / doc sem TOC** (1 teste): adicionar TOC aos 3 docs (`baixando-credores-lote-odoo/DESIGN.md`, `app/agente/services/CLAUDE.md`, `docs/roteirizacao/ESTADO.md`) OU revisar a regra de isencao C6.
