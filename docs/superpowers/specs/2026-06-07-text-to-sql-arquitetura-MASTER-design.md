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

| # | Subsistema | Resolve | Depende de | Sub-plano |
|---|---|---|---|---|
| S0 | Gerador idempotente | N4 (poluicao git) | — | `docs/superpowers/plans/2026-06-07-text-to-sql-S0-gerador-idempotente.md` |
| S1 | Progressive disclosure | N1, N2, F3(parcial) | S0 | `docs/superpowers/plans/2026-06-07-text-to-sql-S1-progressive-disclosure.md` |
| S2 | Qualidade de schema | N3, F2(causa de fundo) | S0 | `docs/superpowers/plans/2026-06-07-text-to-sql-S2-qualidade-schema.md` |
| S3 | Nucleo de geracao | F1-F7, separar permissao | S1 | `docs/superpowers/plans/2026-06-07-text-to-sql-S3-nucleo-geracao.md` |

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

**Gate S0 — gerador idempotente**
- [ ] Passo 0 (causa raiz da poluicao) reproduzido e registrado no rastreamento.
- [ ] Rodar `generate_schemas.py` 2x sem mudar modelo → `git status --porcelain` dos
      schemas VAZIO na 2a execucao.
- [ ] Mudar 1 descricao de 1 modelo → regenerar → mudam SO os arquivos afetados (nao 303).
- [ ] `catalog.json` e `relationships.json` ordenados por nome (estaveis entre execucoes).
- [ ] Orfao apagado SO com import 100% completo — teste cobre import parcial = NAO apaga.
- [ ] pytest de idempotencia verde.

**Gate S1 — progressive disclosure**
- [ ] `buscar_tabelas(intencao)` retorna a tabela esperada no top-N para o golden set
      (precisao@N acordada na sessao).
- [ ] `key_fields` de carteira_principal / separacao / faturamento_produto contem as
      chaves de negocio esperadas (teste).
- [ ] dominio (grupo) presente no catalog, derivado do app de origem.
- [ ] indice semantico reindexa no MESMO gatilho de S0 (freshness provada por teste).
- [ ] tool registrada no servidor MCP e visivel ao agente.
- [ ] pytest verde + idempotencia S0 preservada.

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

**Gate S3 — nucleo de geracao**
- [ ] Caminho literal: SQL valido executa SEM reescrita por LLM; campo inexistente →
      devolve schema real + hints (teste).
- [ ] admin e comum usam a MESMA via de geracao; diferenca SO em permissao — teste afirma
      que comum continua barrado em tabela bloqueada e em DML (nao-regressao do Safety).
- [ ] Contrato `sql=`/`pergunta=` na tool; `looks_like_raw_sql` fora do caminho feliz.
- [ ] Fixes F1 (truncamento), F2 (skip_haiku), F4 (template stale) com teste cada.
- [ ] Auditoria/shadow instrumentada medindo NL vs SQL (dado coletavel ANTES de remover o
      Generator).
- [ ] pytest verde.

**Gate GLOBAL — pacote completo**
- [ ] Ordem respeitada: S0 e S1 concluidos antes de S3; S2 entregue.
- [ ] As 7 invariantes inegociaveis verificadas (nenhuma regressao).
- [ ] Rastreamento append-only atualizado por cada sessao.
- [ ] Suite pytest do pipeline SQL inteira verde (zero regressao).

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
