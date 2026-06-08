<!-- doc:meta
tipo: explanation
camada: L3
sot_de: arquitetura Text-to-SQL do Agente Web (achados + decomposicao S0-S3)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-07
-->

# Text-to-SQL do Agente Web — Arquitetura (MASTER)

> **Papel:** documento-cerebro que persiste os achados da investigacao do pipeline
> Text-to-SQL e a decomposicao do conserto em 4 subsistemas (S0-S3). Cada subsistema tem
> um sub-plano proprio, executado por uma sessao dedicada com o autor desta investigacao
> avaliando plano + execucao. Leia este MASTER antes de qualquer sub-plano.

## Indice

- [Contexto](#contexto)
- [Como usar este pacote](#como-usar-este-pacote)
- [Achados — o pipeline atual ponta a ponta](#achados-o-pipeline-atual-ponta-a-ponta)
- [Achados — caminhos por perfil de usuario](#achados-caminhos-por-perfil-de-usuario)
- [Achados — furos catalogados](#achados-furos-catalogados)
- [Tese arquitetural](#tese-arquitetural)
- [Decomposicao S0-S3](#decomposicao-s0-s3)
- [Invariantes inegociaveis](#invariantes-inegociaveis)
- [Pre-mortem global](#pre-mortem-global)
- [Protocolo de execucao por sessao](#protocolo-de-execucao-por-sessao)
- [Checkpoints de completude (gate por subsistema)](#checkpoints-de-completude-gate-por-subsistema)
- [Sub-planos](#sub-planos)
- [Rastreamento de execucao (append-only)](#rastreamento-de-execucao-append-only)

## Contexto

O Agente Web (Claude Agent SDK, Opus) responde perguntas sobre o banco via a tool MCP
`consultar_sql`, que delega ao pipeline `.claude/skills/consultando-sql/scripts/
text_to_sql.py`. O usuario relatou que o Generator (etapa NL→SQL) "so atrapalha" e o
desligou para admin (via SQL-first). A investigacao confirmou um problema mais profundo:
o pipeline tem DUAS mentes gerando SQL (o Opus, que ja sabe SQL, e um Generator Haiku
inferior tratado como autor), um progressive disclosure de schema quebrado, schemas
rasos e um gerador de schemas que polui o git. Este MASTER consolida o diagnostico com
fontes e decompoe o conserto.

Quem chama a tool e SEMPRE o Opus — o usuario fala em portugues com o agente; o agente
decide chamar `consultar_sql` passando NL ou SQL pronto. Isso e central para todo o
diagnostico.

## Como usar este pacote

- **1 MASTER (este) + 4 sub-planos**, um por subsistema. Cada sub-plano e auto-contido:
  contexto herdado, escopo, arquivos-alvo com fontes, abordagens com recomendacao,
  edge-cases, pre-mortem, decisoes em aberto e testes.
- **Execucao**: 4 sessoes dedicadas, uma por subsistema. Cada sessao le este MASTER +
  o seu sub-plano, refina o design fino (brainstorming proprio sobre as "decisoes em
  aberto"), implementa com TDD e registra no rastreamento abaixo.
- **Papel do autor**: avaliar plano e execucao de cada sessao (detentor dos achados).
- **Ordem**: `S0 → S1 → S3`, com `S2` em paralelo a partir de S0.

## Achados — o pipeline atual ponta a ponta

`consultar_sql` (`app/agente/tools/text_to_sql_tool.py:447`) resolve `user_id` e perfil
(`:479-491`), resolve o modo SQL-first (`:517`, `feature_flags.py:1073`) e chama
`pipeline.run(...)`. Em `text_to_sql.py:run()` (`:1907`):

1. **3 entradas mutuamente exclusivas para obter o SQL:**
   - **SQL-first** (`:2021`): se modo `on` e `looks_like_raw_sql()` (`:326`) → executa o
     SQL do agente LITERAL; pula Generator + Evaluator + sanitizacao.
   - **Template** (`:2033`): embedding com similaridade >= 0.92 → usa SQL salvo; pula
     Generator.
   - **Generator** (`:2051-2076`): caso geral (NL) → Haiku gera SQL a partir do catalogo
     leve, com `max_tokens=500` (`:862`).
2. **1b retrieval** (`:2083`): extrai tabelas e carrega schema detalhado.
3. **1c validador deterministico** (`SQLDeterministicValidator`, `:925`): regex+schema;
   so campo inexistente e bloqueante; se aprova + SELECT puro + nao-admin → `skip_haiku`
   (`:1022`).
4. **2 Evaluator Haiku** (`:1303`): corrige campos/tipos/filtros, ate 2 retries; pulado
   se `is_sql_first OR skip_haiku OR admin_dml_bypass` (`:2190`).
5. **2b/2c** sanitizacao + deteccao UUID-em-numerico.
6. **3 Safety** (`:2364`): admin → `validate_admin` (bloqueia DDL/multi-stmt/funcoes;
   DML passa); comum → `validate` (SELECT/WITH + tabelas bloqueadas).
7. **4 Executor** (`:1521`): admin → read_write (commit); comum → `SET TRANSACTION READ
   ONLY` (rollback); `LIMIT 500` forcado (`:1535`).

O catalogo leve (`SchemaProvider.get_catalog_text`, `:470`) alimenta SO o Generator
Haiku. O Opus descobre schema 1 tabela por vez via `mcp__schema__consultar_schema`
(`app/agente/tools/schema_mcp_tool.py:328`), tendo de adivinhar o nome da tabela antes.

## Achados — caminhos por perfil de usuario

```
ADMIN (USUARIOS_SQL_ADMIN): admin_mode=True
  Opus manda SQL + SQL_AGENT_SQL_FIRST=admin/on -> SQL-FIRST literal (sem Generator)
  Opus manda NL                                 -> GENERATOR Haiku roda (mesmo admin!)
       DML    -> admin_dml_bypass (pula Evaluator)
       SELECT -> Evaluator roda (admin nao pega skip_haiku)

COMUM: admin_mode=False
  modo "admin" vira "shadow" p/ comum -> SEMPRE Generator Haiku
       SELECT puro aprovado no deterministico -> skip_haiku -> Evaluator PULADO
```

Conclusao: como o AUTOR do SQL e sempre o Opus, o Generator e o MESMO downgrade para
admin e comum. A diferenca entre perfis e de PERMISSAO, nao de competencia de SQL. O
"desligamento" atual para admin e PARCIAL (so quando o Opus manda SQL bruto; com NL, o
Generator volta a rodar).

## Achados — furos catalogados

| # | Furo | Fonte |
|---|---|---|
| F1 | Generator truncado a `max_tokens=500` → CTE/JOIN longo cortado | `text_to_sql.py:862,101,117,137` |
| F2 | `skip_haiku` pula Evaluator; deterministico e cego a campo existente-mas-errado | `text_to_sql.py:1022` + `:997-1012` |
| F3 | regra 4 do Generator manda adivinhar campo por descricao, com exemplos-ancora | `text_to_sql.py:842` |
| F4 | template >= 0.92 nao e revalidado contra schema (stale executa) | `text_to_sql.py:2033` |
| F5 | `looks_like_raw_sql` fragil → SQL legitimo vira NL → Generator | `text_to_sql.py:326` |
| F6 | validador deterministico nao ve JOIN/FK/agregacao errada | `text_to_sql.py:945-1029` |
| F7 | Generator+Evaluator+2 retries = custo/latencia por consulta | `text_to_sql.py:2207-2265` |

Achados novos de estrutura:
- **N1 Opus cego**: o catalogo (mapa das 303 tabelas) nao chega ao Opus; ele adivinha
  nomes de tabela. → S1.
- **N2 key_fields = lixo**: catalogo usa as 3 PRIMEIRAS colunas como "chave"
  (`generate_schemas.py:538-545`). → S1.
- **N3 schemas rasos**: `business_rules`/`query_hints` so nas 9 core; descricao de campo
  50-88% nas demais (amostra real). → S2.
- **N4 gerador polui git**: reescreve os 303 arquivos sempre, sem comparar
  (`generate_schemas.py:742,787,805`). → S0.

## Tese arquitetural

**Uma so mente escreve o SQL — o Opus. O pipeline deixa de ser um segundo autor e vira
executor seguro + corretor. A distincao admin/comum e SO de permissao, nunca da forma de
gerar SQL.** Quando o Opus erra, a correcao e DETERMINISTICA (devolver campos reais +
hints para auto-correcao) ou, se for usar Haiku, com TESTE (revalidacao deterministica /
`EXPLAIN`), nunca as cegas. Validada pelo usuario.

## Decomposicao S0-S3

| # | Subsistema | Resolve | Depende de | Status | Sub-plano |
|---|---|---|---|---|---|
| S0 | Gerador idempotente | N4 (poluicao git) | — | ✅ PROD `2d92fee57` (+ S0b auto-descoberta) | `docs/superpowers/plans/2026-06-07-text-to-sql-S0-gerador-idempotente.md` |
| S1 | Progressive disclosure | N1, N2, F3(parcial) | S0 ✅ | ✅ PROD `5aec0b3ae`/merge `8f863ee30` (migration aplicada + 327 embeddings `voyage-4-large` @ 2026-06-08) | `docs/superpowers/plans/2026-06-07-text-to-sql-S1-progressive-disclosure.md` |
| S2 | Qualidade de schema | N3, F2(causa de fundo) | S0 ✅ | ✅ PROD `dc1c8573e` | `docs/superpowers/plans/2026-06-07-text-to-sql-S2-qualidade-schema.md` |
| S3 | Nucleo de geracao | F1-F7, separar permissao | S1 ✅ | 🟡 **S3-A** worktree `worktree-text-to-sql-S3` (contrato sql=+F1+F4+entry_kind+default on; NAO pushado) · **S3-B** (remover Generator) ⬜ apos medir auditoria | `docs/superpowers/plans/2026-06-07-text-to-sql-S3-nucleo-geracao.md` |

Dependencias: S0 destrava S1 e S2 (diffs limpos). S1 destrava S3 (Opus precisa do mapa
para ser autor confiavel). S2 corre em paralelo desde S0 e alimenta S1/S3 (melhores
descricoes elevam precisao). S3 e o fecho (coracao da geracao).

## Invariantes inegociaveis

Toda sessao DEVE preservar:
1. **Permissao != geracao**: admin e comum geram SQL pela MESMA via; admin difere so em
   DML/tabelas/campos permitidos.
2. **Sem confiar em LLM as cegas para corrigir**: correcao e deterministica ou
   Haiku-com-teste.
3. **Determinismo do gerador** (apos S0): nenhuma mudanca pode reintroduzir poluicao de
   git.
4. **Curadoria duravel** (S2): conteudo curado nunca em arquivo gerado; sempre em
   overlay.
5. **Safety nunca regride**: read-only para comum, bloqueio de TABELA (sem bloqueio de
   campo — decisao 2026-06-07), DDL barrado; qualquer caminho novo passa por Safety +
   Executor.
6. **Sem evals LLM caros** como gate de skill: cobertura por pytest deterministico (regra
   do projeto).
7. **Migrations**: qualquer DDL gera 2 artefatos (Python + SQL idempotente).

## Pre-mortem global

> "3 meses depois, o conserto inteiro falhou. Por que?"
1. **Sessoes executaram fora de ordem** (S3 sem S1) e o Opus, ainda cego, gerou SQL pior
   → reforcar a ordem S0→S1→S3 no protocolo; S3 so inicia com S1 entregue.
2. **Cada sessao redesenhou a arquitetura** divergindo da tese → este MASTER + as
   invariantes sao o contrato; o autor avalia cada plano antes da execucao.
3. **Mediram-se metricas-proxy** (ex.: "menos linhas") em vez de correcao real → criterio
   de sucesso de cada sub-plano e comportamental e verificavel.
4. **Removeu-se o Generator cedo** sem medir NL residual → S3 exige shadow antes de B.
5. **Perda de contexto entre sessoes** → o rastreamento append-only abaixo + os achados
   com fonte garantem retomada.

## Protocolo de execucao por sessao

1. Sessao le este MASTER (achados + tese + invariantes) e o seu sub-plano.
2. Resolve as "decisoes em aberto" do sub-plano com o usuario (brainstorming fino).
3. Implementa com TDD (pytest deterministico; sem evals LLM caros).
4. Verifica contra o "criterio de sucesso" do sub-plano (evidencia, nao afirmacao).
5. Registra no rastreamento abaixo (append-only): o que mudou, decisoes tomadas, fontes.
6. Autor avalia plano (antes) e execucao (depois).

## Checkpoints de completude (gate por subsistema)

Gate binario e verificavel. Uma sessao so declara o subsistema COMPLETO quando TODOS os
itens do seu gate passam com EVIDENCIA (comando/teste), nunca por afirmacao. O autor
valida o gate antes de fechar.

**Gate S0 — gerador idempotente** ✅ (S0 + S0b, PROD `2d92fee57`)
- [x] Passo 0 (causa raiz) reproduzido: ordem de iteracao de `table.indexes` (`set`) → 163/304
      tables mudavam entre execucoes (registrado no rastreamento).
- [x] Rodar `generate_schemas.py` 2x sem mudar modelo → `--check` 0 drift (327 schemas, 0 escritos).
- [x] Mudar 1 descricao de 1 modelo → regenerar → mudam SO os afetados (ex.: `pedido_compras`
      + `catalog` na integracao S2, 2 escritos).
- [x] `catalog.json` e `relationships.json` ordenados por nome (estaveis entre execucoes).
- [x] Orfao apagado SO com import 100% completo + allow-list `ORFAOS_VIVOS_PRESERVAR` (S0b);
      teste cobre import parcial = NAO apaga.
- [x] pytest de idempotencia verde (27: 18 S0 + 9 S0b).

**Gate S1 — progressive disclosure** ✅ (2026-06-07, PROD `5aec0b3ae`/merge `8f863ee30`; migration aplicada, 327 embeddings `voyage-4-large` @ 2026-06-08T00:23)
- [x] `buscar_tabelas(intencao)` retorna a tabela esperada no top-N para o golden set.
      → precisao@3 = **100%** (20/20) no golden set justo (gate acordado = top-3 >=90%);
      flagship top-1 (carteira/faturamento/separacao). `TestGoldenSetGate`
      (`tests/agente/test_buscar_tabelas.py`). Casos PURAMENTE semanticos (palavra do
      conceito ausente da intencao) sao da camada de embeddings (fusao testada via mock).
- [x] `key_fields` de carteira_principal / separacao / faturamento_produto contem as
      chaves de negocio esperadas. → `TestCatalogReal` (`test_key_fields_dominio.py`):
      carteira={num_pedido,cod_produto,cnpj_cpf,data_pedido,status_pedido}; idem sep/fat.
- [x] dominio (grupo) presente no catalog, derivado do app de origem.
      → `_dominio_from_module` (app.carteira.models -> "Carteira"); `test_todas_entries_tem_dominio`.
- [x] indice semantico reindexa no gatilho de freshness (freshness provada por teste).
      → **PREMISSA REVISTA (decisao do usuario)**: o gatilho LITERAL do S0 (hook dev
      `generate_schemas.py`) NAO toca banco; embeddings vivem no banco PROD. Solucao
      HIBRIDA: (a) camada TEXTUAL le o catalog.json FRESCO (S0) — cobre tabela nova na
      hora; (b) camada SEMANTICA reindexa no scheduler diario (`reindexacao_embeddings.py`,
      11o step) com content_hash (so re-embeda o que mudou). `TestFreshnessScheduler` +
      `test_content_hash_*` (`test_table_catalog_indexer.py`).
- [x] tool registrada no servidor MCP e visivel ao agente. → `buscar_tabelas_server`
      (Enhanced MCP) + `_register_mcp("buscar_tabelas", ..., set_user_id)` em `client.py`
      (glob `mcp__buscar_tabelas__*`, mesmo mecanismo do schema_server).
- [x] pytest verde + idempotencia S0 preservada. → 196 passed (consultando_sql + agente +
      embeddings + pipeline); `generate_schemas.py --check` = 0 drift (328 schemas).

**Gate S2 — qualidade de schema** ✅ (2026-06-07, integrado sobre S0b)
- [x] Descricao curada na fonte (modelo) APARECE no `tables/<t>.json` gerado E em
      `consultar_schema`. → `TestDescricaoNaFonteAparece`; `pedido_compras` docstring na fonte
      (`manufatura/models.py`) → `tables/pedido_compras.json` (regenerado pelo gerador S0b).
- [x] Overlay de `business_rules`/`query_hints` aplicado e exibido. → `_merge_overlay_into_schema`
      + `_enrich_schema` (RUNTIME, no SchemaProvider); `TestSchemaProviderOverlayCuradoria` +
      `TestOverlayRealFretes`; exibido em `_format_schema` e `get_tables_schema_text`.
- [x] Top-40 por uso: descricao + regras/hints presentes. → **40/40** (`TestGateS2Top40`);
      criterio calibrado de ">=90% campos" para "desc-tabela + business_rules + query_hints +
      campos-chave nos BR" (auditoria: gargalo e regra/JOIN de negocio, nao nome de campo).
- [x] Idempotencia S0 preservada com overlays aplicados. → overlays RUNTIME-only (gerador NAO
      materializa — `TestGeradorNaoMaterializaCuradoria`); `--check` 0 drift apos regeneracao.
- [x] pytest verde. → suite `consultando_sql` + nao-regressao do pipeline SQL/agente.

**Gate S3 — nucleo de geracao** — 🟡 **S3-A** entregue (worktree, NAO pushado); **S3-B** (remover Generator) ⬜ apos medir auditoria
- [x] Caminho literal: SQL valido executa SEM reescrita por LLM; campo inexistente →
      devolve schema real + hints (teste). → `TestExplicitSqlContract` + `TestSqlFirstSchemaFeedback`
      (`test_text_to_sql_s3.py` + `test_text_to_sql_sql_first.py`).
- [x] admin e comum usam a MESMA via de geracao; diferenca SO em permissao — teste afirma
      que comum continua barrado em tabela bloqueada e em DML (nao-regressao do Safety).
      → `TestPermissionVsGeneration` (mesma via literal; rw=[False,True]; tabela bloqueada e DML barram).
- [x] Contrato `sql=`/`pergunta=` na tool; `looks_like_raw_sql` fora do caminho feliz.
      → param `sql=` na enhanced_tool + `_resolve_tool_input` + `run(sql_literal=...)` (bypassa
      heuristica); `TestResolveToolInput` + `TestToolForwardsSqlLiteral`.
- [x] F1 (truncamento): `max_tokens` 500 → `TEXT_TO_SQL_GEN_MAX_TOKENS` (default 2000),
      lido fresh. → `TestGeneratorMaxTokens`.
- [x] F4 (template stale): template ≥0.92 revalidado contra schema; campo inexistente →
      descarta direct-hit (`template_stale_discarded`) e cai no fluxo. → `TestTemplateFieldsValidation`.
- [x] F2 (skip_haiku): resolvido pela TESE, nao por Haiku-as-cegas (invariante #2). O
      guard-rail DETERMINISTICO (bloqueio de campo inexistente + feedback) e' o caminho
      DEFAULT com SQL-first on; o skip_haiku legado do Generator e' vestigial e some com
      o Generator em S3-B. NAO foi adicionado Evaluator cego (regrediria IMP-2026-05-13-003,
      falso-positivo de data). → `TestSqlFirstSchemaFeedback`.
- [x] Auditoria instrumentada medindo NL vs SQL (`entry_kind`: sql_explicit | sql_heuristic |
      nl) + `_log_sql_first_shadow` (would_block). Dado coletavel ANTES de remover o Generator.
      → `TestEntryKindAudit`.
- [x] SQL-first default 'on' no codigo (decisao #5; env PROD inalterada). → `TestResolveSqlFirstDefaultOn`.
- [x] pytest verde. → **215 passed** (sql_first 50 + admin_dml 12 + S3 25 + consultando_sql 128); zero regressao.
- [ ] **S3-B**: remover o Generator (tool exige `sql=`; NL retorna erro pedindo SQL) APOS a
      auditoria `entry_kind` provar NL→~0 em PROD; aposentar a flag `SQL_AGENT_SQL_FIRST`.

**Gate GLOBAL — pacote completo** — 🟡 S3-A entregue; package FECHA com S3-B
- [x] Ordem respeitada: S0 e S1 concluidos (PROD) antes de S3; S2 entregue (PROD).
- [x] As 7 invariantes inegociaveis verificadas (nenhuma regressao) — S3-A 2026-06-08:
      (1) permissao!=geracao `TestPermissionVsGeneration`; (2) sem Haiku as cegas (guard-rail
      deterministico, NAO Evaluator cego); (3) determinismo gerador `--check` 0 drift (329);
      (4)/(5) S0/S2 intocados; (6) so pytest deterministico; (7) sem DDL em S3-A.
- [x] Rastreamento append-only atualizado (correcao S1->PROD + linha S3-A).
- [x] Suite pytest do pipeline SQL verde (zero regressao): 246 SQL/S3/consultando_sql/tools
      + 263 sdk + 10 Teams + 99 embeddings + 9 capability.
- [ ] **Falta S3-B p/ fechar o package**: remover o Generator apos a auditoria `entry_kind`
      (`[SQL_AUDIT]` nos logs PROD) provar NL->~0; aposentar `SQL_AGENT_SQL_FIRST`.

## Sub-planos

- S0 — `docs/superpowers/plans/2026-06-07-text-to-sql-S0-gerador-idempotente.md`
- S1 — `docs/superpowers/plans/2026-06-07-text-to-sql-S1-progressive-disclosure.md`
- S2 — `docs/superpowers/plans/2026-06-07-text-to-sql-S2-qualidade-schema.md`
- S3 — `docs/superpowers/plans/2026-06-07-text-to-sql-S3-nucleo-geracao.md`

## Rastreamento de execucao (append-only)

| Data | Subsistema | Sessao fez | Decisoes | Estado |
|---|---|---|---|---|
| 2026-06-07 | — | Investigacao + decomposicao + 5 docs criados | tese validada; ordem S0→S1→S3, S2 paralelo | planos prontos, execucao nao iniciada |
| 2026-06-07 | todos | 17 decisoes fechadas com o usuario; gatilho do hook diagnosticado (global settings) | S0: apagar orfaos(+salvaguarda), ordenar globais por nome. S1: semantica+fallback+freshness+golden, key_fields minimo, dominio auto, tool nova. S2: curar na fonte+overlay so regras/hints, top-40, LLM+revisao. S3: REMOVER Generator (a menos que auditoria prove), SEM bloqueio de campo, mesma tool, SQL-first vira padrao | sub-planos com decisoes fechadas |
| 2026-06-07 | S0 ✅ | Gerador idempotente implementado+validado (worktree `feat`, NAO commitado): `_dump_canonical` (write-if-changed + newline final) + ordenacao canonica de indices/unique_constraints/foreign_keys; flag `--check` (drift); orfaos com LOG+salvaguarda via `--prune-orphans`; filtro do hook ampliado em `_is_model_file`; 18 pytest novos | Passo 0 PROVOU causa raiz = ordem de iteracao de `table.indexes` (`set`) → 163/304 tables mudavam entre execucoes; `catalog.json`/`relationships.json` JA eram estaveis (decisao 4 e DEFENSIVA, nao corretiva); SEM 2a fonte (app NAO regenera no startup — corrige suposicao da memoria gotcha-worktree). **Decisao 1 REVISTA com usuario**: 4/5 "orfaos" sao tabelas VIVAS nao-importadas (carvia_sessao_demandas, carvia_sessoes_cotacao, teams_tasks, claude_session_store); so `carvia_aprovacoes_subcontrato` e remocao real (renomeada). Logo prune NAO-automatico (so `--prune-orphans` + import 100% completo); fluxo automatico/hook so LOGA. Hook perdia `*_models.py` (email_models, frota_models) | Gate S0 VERDE c/ evidencia: idempotencia 2x = 0 escritos (git 306→306); 1 desc = 2 arquivos; `--check` 0/1; 18 pytest S0 + 88 nao-regressao (text_to_sql 79, capability 4, artefato 5). AGUARDANDO revisao do usuario; NAO commitado |
| 2026-06-07 | S0b ✅ | Auto-descoberta de modulos + allow-list de orfaos vivos + fix do bug getdoc (worktree `worktree-text-to-sql-s0b-autodiscovery`, NAO commitado): `_discover_model_modules` varre app/ por NOME E confirma por CONTEUDO (`__tablename__`), unida a legado de garantia; `ORFAOS_VIVOS_PRESERVAR` (4 tabelas) bloqueia prune; `extract_class_docstring` usa `__doc__` (nao `inspect.getdoc`, que herdava docstring de `db.Model`); log de orfaos particiona preservados x a-revisar; 9 pytest novos | CAUSA da nao-atualizacao = lista `model_modules` HARDCODED esquecia modulos (ex: app.teams.models -> teams_tasks defasada). PROD (MCP Render 2026-06-07) confirmou: as 5 "orfas" EXISTEM no banco (claude_session_store 67.216, teams_tasks 1.181, carvia 2/2/0) -> NENHUMA apagada. teams_tasks deixou de ser orfa (gerada); +19 tabelas cobertas (embeddings 12 ORM, seguranca, etc.); bug getdoc JA afetava 5 tabelas na MAIN (recursos_producao, pedido_compras, usuarios, previsao_demanda, requisicao_compras) — fix limpa | Gate VERDE c/ evidencia: descoberta 114 mods (superset do legado, 0 falsos positivos apos filtro de conteudo); idempotencia `--check` 0 drift (327 schemas, 0 escritos na 2a); 27 pytest (18 S0 + 9 S0b) + 112 nao-regressao; 0 import_errors. AGUARDANDO merge do usuario |
| 2026-06-07 | S2 ✅ + integracao S0b | Qualidade de schema: overlay RUNTIME (`_merge_overlay_into_schema` + `_enrich_schema` no SchemaProvider) serve `business_rules`/`query_hints` a QUALQUER tabela; descricao curada na FONTE (`col.info['description']` + docstring de classe, ex: `pedido_compras` em `manufatura/models.py`); 46 overlays (209 business_rules, 122 query_hints) por 6 subagentes; SEED_TEMPLATES corrigido (12 campos errados que executavam SQL invalido) + guard `test_seed_templates_campos`. Reconstruido limpo sobre main+S0b: conflito real SO em `generate_schemas.py` e neste MASTER; resto do S2-puro (text_to_sql.py, 46 overlays, manufatura/models.py, sql_template_indexer.py, 2 testes) NAO colidiu | **Conflitos avaliados 1-a-1 (a pedido do usuario)**: `generate_schemas.py` = versao S0b mantida (superior em 5/6 regioes: allow-list orfaos + autodescoberta); getdoc s0b (`__doc__`) == S2 (`__dict__.get`) FUNCIONALMENTE (None.__doc__=None comprovado, sem bug). Cobertura carvia/hora/motos_assai NAO via `MODEL_MODULES` (lista manual DESCARTADA) e sim pela AUTO-DESCOBERTA do S0b (superconjunto). Teste `test_model_modules_inclui_carvia_hora_assai` ADAPTADO -> `test_autodescoberta_cobre_carvia_hora_assai` | Gate S2 VERDE: top-40 = 40/40 (runtime); regenerar = 2 escritos (catalog + pedido_compras pela curadoria-fonte), `--check` 0 drift depois; 0 campos inventados em 122 hints; suite consultando_sql + nao-regressao verdes. MERGE: S0b ff->main (`2d92fee57`); S2 reconstruido. AGUARDANDO push do usuario |
| 2026-06-07 | S1 ✅ | Progressive disclosure (worktree `worktree-text-to-sql-S1`, NAO pushado). **Gerador**: `_select_key_fields` (chaves de negocio + ate 2 filtros, teto 5, sem id/auditoria, deterministico — resolve N2) + `_dominio_from_module` (app de origem -> label; resolve grupo). `generate_catalog_entry` agora emite `key_fields`+`dominio`; `get_catalog_text` exibe ambos. `table_catalog_embeddings` -> BLOCKED_TABLES (infra). **Tabela pgvector** `table_catalog_embeddings` (`TableCatalogEmbedding`, upsert por `table_name`) + migration DUPLA (`scripts/migrations/2026_06_07_table_catalog_embeddings.{py,sql}`). **Indexer** `table_catalog_indexer.py` (content_hash) + `EmbeddingService.search_table_catalog` (pgvector+fallback) + 11o step no scheduler (`reindexacao_embeddings.py`) + flag `TABLE_CATALOG_SEMANTIC`/`THRESHOLD_TABLE_CATALOG`. **Tool** `buscar_tabelas_tool.py` (busca HIBRIDA textual∪semantica via RRF; permissao = mesma matriz do executor) registrada em `client.py` (`mcp__buscar_tabelas__*`). system_prompt: fluxo intencao→buscar_tabelas→consultar_schema→SQL | (1) busca **hibrida** (decisao do usuario): textual deterministica e a base do gate; semantica e enhancement de recall. (2) **Freshness**: premissa do plano ("mesmo gatilho do S0") era inviavel (S0=hook dev sem banco; embeddings=banco PROD) -> resolvida por textual-fresca + reindex diario com content_hash. (3) **Gate** acordado top-3 >=90%; golden set JUSTO (vocabulario da tabela), casos puramente semanticos delegados aos embeddings. (4) ranking textual = (cobertura, name_extra, desc_cov, peso): name_extra distingue tabela-base (contas_a_receber) de derivadas; desc_cov favorece a tabela cuja descricao fala da intencao (carteira em "pedidos pendentes"). (5) matching por raiz comum >=5 (plural/conjugacao). Migration NAO rodada (DDL bloqueado pelo classificador local; valida em PROD/local com OK) | Gate S1 VERDE c/ evidencia: golden top-3 = 100% (20/20); flagship top-1; key_fields/dominio testados; freshness (textual fresca + 11o step content_hash); tool registrada; **196 passed** (consultando_sql+agente+embeddings+pipeline); `--check` 0 drift (328 schemas). AGUARDANDO validacao + push do usuario (push = deploy PROD; migration a rodar) |
| 2026-06-07 | S1 (prova semantica + fix fusao) | A pedido do usuario, PROVEI o valor da semantica com Voyage REAL (A/B, cosine em memoria = fallback real do sistema): em 15 intencoes COLOQUIAIS (vocabulario do usuario != nome/descricao da tabela) top-8 textual=60% vs semantica=86% (top-1 20%->60%, 3x). A PROVA expos um DEFEITO no meu design: a fusao RRF inicial DILUIA a semantica (top-8 73% < semantica pura 86%) — a cauda textual (tabelas de token comum) contaminava o topo. CORRIGIDO: `_fundir` (RRF, pesos iguais) -> `_combinar` (SEMANTICA PRIMARIA + textual append), fiel a decisao 1 do plano. Output expoe agora `origem` (semantica/textual) + `similaridade` (transparencia). 2 testes novos (semantica primaria; textual append). | Estrategia validada em AMBOS conjuntos: COLOQUIAL top-8 86% (vs RRF 73%, textual 60%) + GOLDEN top-8 100%. Gate determin. INTACTO: embeddings off -> textual pura -> golden 100% (a fusao so muda o caminho PROD com Voyage). Peso do RRF era irrelevante (0.2..1.0 davam o mesmo) -> append e mais simples E melhor. THRESHOLD_TABLE_CATALOG=0.30 (sims coloquiais reais ~0.3-0.5, voyage-4-lite). | Confirmado no CODIGO DE PRODUCAO (B.buscar real c/ Voyage): "clientes que compraram no mes passado"->faturamento_produto #1 (sim .50); "a fabrica cumpriu o planejado"->programacao_producao #1; "mercadoria parada no deposito"->movimentacao_estoque #1 — todos a textual perdia. 118 pytest verdes. NAO commitado/pushado |
| 2026-06-07 | S1 (modelo voyage-4-large no catalogo) | Usuario perguntou se outra versao do Voyage ajudaria. A/B REAL de modelos (15 coloquiais/15 golden, doc confirmou voyage-4-* existem, 1024D): voyage-4-lite top-3 coloquial 73% -> voyage-4 80% -> **voyage-4-large 93%** (golden 100%). Reranking (rerank-2.5-lite sobre pool lite+textual) NAO ajudou (=73%/86% do lite — limitado ao recall do pool + tier lite nao supera cosine no PT coloquial). ADOTADO voyage-4-large ISOLADO p/ o catalogo: nova config `VOYAGE_TABLE_CATALOG_MODEL` (default voyage-4-large) usada no indexer (embed model= + grava model_used + filtra `existing` por model_used p/ RE-EMBEDAR ao trocar modelo — espacos vetoriais incompativeis) e em `search_table_catalog` (query no mesmo espaco). | Decisao do usuario (trade-off custo/qualidade): large vale o +20pp top-3 coloquial; catalogo pequeno (~310 tabelas, indexacao 1x/dia trivial; 1 embedding/busca). Default global `VOYAGE_DEFAULT_MODEL`=voyage-4-lite INALTERADO -> os outros 12 dominios NAO reindexam. Rerank DESCARTADO (sem ganho aqui; reavaliar com rerank-2.5 full se necessario). 1024D = drop-in (sem nova migration). | 53 pytest verdes (3 novos travam o isolamento modelo-dedicado por source-check; default global continua lite). voyage-4-large validado no A/B real (embedou 309 tabelas + queries). NAO commitado/pushado |
| 2026-06-08 | S1 — CORRECAO DE STATUS (auditoria) | Auditoria do estado real (git+PROD) reconcilia o MASTER: S1 NAO esta "em worktree nao pushado" — esta EM PROD. `main`: `5aec0b3ae` (feat S1) + merge `8f863ee30` + `3f9fb8bd7`. Fixes tardios CONFIRMADOS em main: `_combinar` (semantica primaria) + `VOYAGE_TABLE_CATALOG_MODEL=voyage-4-large`. PROD (MCP Render): `table_catalog_embeddings` = **327 rows, 327 com embedding, voyage-4-large, @2026-06-08T00:23** — migration aplicada + reindex efetivado (nota "0 rows @03:14" era snapshot transitorio). | Sem decisao nova — so reconciliacao. Linha S1 + Gate S1 atualizados worktree/nao-pushado -> PROD. | S0/S1/S2 = TODOS em PROD. S3 era o unico pendente. |
| 2026-06-08 | S3-A 🟡 | Nucleo de geracao — fatia segura (worktree `worktree-text-to-sql-S3`, NAO pushado). TDD RED→GREEN. **G1 contrato `sql=`**: param `sql` na enhanced_tool + `_resolve_tool_input` (sql> pergunta) + `run(sql_literal=...)` que FORCA literal sem a heuristica looks_like_raw_sql (mata F5). **G2/F1**: `max_tokens` 500 -> `TEXT_TO_SQL_GEN_MAX_TOKENS` (default 2000, fresh). **G3/F4**: `_sql_fields_valid` revalida template ≥0.92; stale -> `template_stale_discarded` + cai no Generator. **G5**: `entry_kind` (sql_explicit\|sql_heuristic\|nl) p/ auditoria. **G6/decisao #5**: default do codigo `SQL_AGENT_SQL_FIRST` off->on (env PROD inalterada). **G7**: tool desc reescrita (contrato sql=, "permissao!=geracao") + system_prompt (`consultar_sql(sql=...)`, net-zero vs baseline). | **F2 (skip_haiku) — decisao do implementador**: a linha do Design "Evaluator sempre ativo no fallback" colide com a invariante #2 ("sem Haiku as cegas") e regrediria IMP-2026-05-13-003 (falso-positivo de data). Resolvido pela TESE: o guard-rail DETERMINISTICO (bloqueio de campo + feedback) e' o caminho default com SQL-first on; o skip_haiku legado e' vestigial e some com o Generator em S3-B. NAO adicionei Evaluator cego. **Generator NAO removido** (decisao #1: medir `entry_kind` em PROD antes) = S3-B. | Gate S3 = S3-A VERDE c/ evidencia: **215 passed** (sql_first 50 + admin_dml 12 + S3 25 + consultando_sql 128), 0 regressao; prompt net-zero (781L); 25 testes novos em `test_text_to_sql_s3.py`. AGUARDANDO validacao + push do usuario (push = deploy PROD). S3-B (remover Generator) pendente de medicao. |
