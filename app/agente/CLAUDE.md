<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-15
-->
# Agente Logistico Web — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Agente Web — wrapper do Claude Agent SDK que serve o chat web (SSE) e o bot do Teams (async). Abra antes de editar `app/agente/`.

## Indice

- [Mapa de Navegacao](#mapa-de-navegacao)
- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Arquitetura de Prompts (v3 — 28/03/2026)](#arquitetura-de-prompts-v3-28032026)
- [Regras Criticas (R1-R10)](#regras-criticas)
- [Hierarquia de Timeouts](#hierarquia-de-timeouts)
- [Gotchas](#gotchas)
- [Pipeline SSE — Contrato de 3 Camadas](#pipeline-sse-contrato-de-3-camadas)
- [Avaliador de Efetividade de Skill (resumo)](#avaliador-de-efetividade-de-skill--inbox-de-aprovacao-fase-1)
- [Versao SDK atual](#versao-sdk-atual)
- [Export critico: Teams](#export-critico-teams)

## Mapa de Navegacao

> **Progressive disclosure.** Este guia carrega inteiro ao tocar `app/agente/` e concentra o que vale SEMPRE (regras criticas, timeouts, SSE, estrutura, arquitetura de prompts). O detalhe de baixa-frequencia vive em arquivos vizinhos — **siga o gatilho em vez de assumir**.

| Preciso de... | Vou para |
|---|---|
| Detalhe de **Artifacts**, **Telemetria de subagent**, **Memoria compartilhada**, **Avaliador de skill** ou o **inventario de eventos SSE** | [`SUBSISTEMAS.md`](SUBSISTEMAS.md) |
| **Fast-paths deterministicos** (reducao de custo: tarefa rotineira+estruturada resolvida SEM LLM/subagente — `baseline_fastpath.py` p/ baseline do Marcus, `vinculacao_fastpath.py` p/ vincular/desvincular NF×PO da Gabriella). Mecanica: detector regex N0 → executor deterministico; fallback Haiku N1 / LLM N2. Flags `AGENT_BASELINE_FASTPATH`, `AGENT_VINCULACAO_FASTPATH` | planos `docs/superpowers/plans/2026-06-06-reducao-custo-agente-fast-path.md` (F1/F2) e `2026-06-08-fastpath-vinculacao-nf-po.md` (F3) |
| **Historico do SDK** — features por versao, breaking changes, bug fixes (0.1.49 → 0.2.101) | `SDK_CHANGELOG.md` |
| **Estado VIVO da evolucao** — flywheel Ondas 0-4, gates, log append-only | `docs/blueprint-agente/EXECUCAO.md` |
| **Design dos 5 eixos** do flywheel (visao + grafo de dependencias) | `docs/blueprint-agente/BLUEPRINT_MESTRE.md` |
| Migracao `query()` → `ClaudeSDKClient` (roadmap, riscos, rollback) | `.claude/references/ROADMAP_SDK_CLIENT.md` |
| Criar/editar **subagent** (frontmatter, secoes obrigatorias, gotchas Claude 4.x) | `.claude/references/AGENT_DESIGN_GUIDE.md` + `AGENT_TEMPLATES.md` |
| **Prompt injection** — defesa em profundidade (5 camadas) | `.claude/references/PROMPT_INJECTION_HARDENING.md` |
| **Protocolo de memoria** — ciclo de vida, decay, paths, qualidade | `.claude/references/MEMORY_PROTOCOL.md` |
| **Capacidades MCP** — Enhanced wrapper, structured output | `.claude/references/MCP_CAPABILITIES_2026.md` |
| Confiabilidade de subagentes (findings via JSONL) | `.claude/references/SUBAGENT_RELIABILITY.md` |
| Regras de output do agente (I1, I5, I6) | `.claude/references/REGRAS_OUTPUT.md` |

## Contexto

Encapsula o Claude Agent SDK: chat web (SSE) + Teams bot (async); ~56.4K LOC em 108 arquivos. Para o roteiro de onde achar cada detalhe, ver **Mapa de Navegacao** acima.

**LOC**: ~56.4K | **Arquivos**: 108 | **Atualizado**: 15/06/2026

> **EVOLUCAO DO AGENTE (flywheel/blueprint Ondas 0-4)**: o rastreador VIVO e o
> `docs/blueprint-agente/EXECUCAO.md` (estado de cada item, gates, log append-only); o design
> por eixo em `eixos/*.md` + revisao em `critica/*.md`, sintetizados em `BLUEPRINT_MESTRE.md`.
> **Regra inviolavel: ANTES de mexer em qualquer item do flywheel (judge/verify/triage/
> eval-gate A3/promocao A4), LER a spec do eixo + a critica** — licao da sessao A3 (drift por
> nao reler). A4 V1 **LIVE em PROD** (2026-06-01). Proxima fase: **VALIDACAO + medicao de
> resultados** das Ondas 0-4 — ver `docs/blueprint-agente/PROMPT_PROXIMA_SESSAO_VALIDACAO.md`
> (regra inviolavel: **VERIFICAR o estado real em PROD, nao assumir**). Historico anti-drift
> A4: `docs/blueprint-agente/PROMPT_PROXIMA_SESSAO_A4.md`.
>
> **AVALIACAO DE MEMORIA (2026-06-02)**: `docs/blueprint-agente/RECONCILIACAO_MEMORIA.md` mapeia
> o sistema de memoria aos eixos (NAO duplicar D=KG / E=qualidade / A4=diretriz empresa) e
> localiza as lacunas em `eixos/C-vigilancia.md` (vigilancia proativa / bi-temporal) e
> `eixos/G-memoria-pessoal.md`. Frente acionavel (loop corretivo pessoal — "expliquei e fez
> certo, depois errou de novo"): `docs/superpowers/plans/2026-06-02-loop-corretivo-pessoal.md`.

---

## Estrutura

```
app/agente/                          # Root — 7 arquivos
├── __init__.py                      # Blueprint import de routes/ + init_app()
├── CLAUDE.md                        # Este arquivo (guia dev)
├── SUBSISTEMAS.md                   # Detalhe de Artifacts/telemetria subagent/memoria compartilhada/avaliador skill + inventario SSE (ver Mapa de Navegacao)
├── SDK_CHANGELOG.md                 # Historico SDK 0.1.49 -> 0.2.101 (features, breaking, fixes) — inclui revisao retroativa do 0.2.82 (2 breakings omitidas)
├── ROLLBACK_SESSION_STORE.md        # Procedimento rollback PostgresSessionStore (Fase B)
├── historia.md                      # Referencia historica (legado, 76K)
├── models.py                        # SQLAlchemy models (AgentSession, AgentMemory, etc.)
├── routes/                          # Flask routes modularizadas — 21 arquivos
│   ├── __init__.py                  # agente_bp + imports sub-modulos + re-exports Teams
│   ├── _constants.py                # Constantes (timeouts, thresholds, upload)
│   ├── _helpers.py                  # Helpers compartilhados (Teams + cross-module)
│   ├── chat.py                      # Core SSE: api_chat, streaming, interrupt, user_answer
│   ├── sessions.py                  # CRUD sessoes: list, messages, delete, rename, summaries
│   ├── admin_learning.py            # Admin: session messages, generate/save correction
│   ├── admin_metrics.py             # Dashboard admin telemetria subagent (Fase A — 10 endpoints)
│   ├── admin_session_store.py       # Admin: PostgresSessionStore introspection (Fase B)
│   ├── admin_teams.py               # Dashboard observabilidade canal Teams (F2 — admin, 7 APIs)
│   ├── admin_subagents.py           # Admin forense: list/messages + smoketest (SDK 0.1.60 fase 2)
│   ├── subagents.py                 # API UI-inline: summary/messages lazy-fetch
│   ├── artifacts.py                 # 5 rotas: 3 publicas (page/bundle/status) + API list/by-uuid/url
│   ├── files.py                     # Upload/download/list/delete + helpers arquivo
│   ├── health.py                    # api_health com cache
│   ├── feedback.py                  # api_feedback 4 tipos
│   ├── insights.py                  # pagina_insights + APIs dados
│   ├── intelligence_report.py       # D7 cron bridge, csrf.exempt
│   ├── improvement_dialogue.py      # D8 cron bridge + admin, csrf.exempt
│   ├── memories.py                  # CRUD memorias + users + review
│   ├── briefing.py                  # api_get_briefing
│   └── user_preferences.py          # Preferences API (thinking display, etc.)
├── config/                          # Configuracao e controle de acesso — 8 arquivos
│   ├── __init__.py
│   ├── agent_loader.py              # Carregamento dinamico do agente
│   ├── capability_registry.py       # Registro de capacidades/tools por contexto (gating)
│   ├── empresa_briefing.md          # Briefing institucional injetado no prompt
│   ├── feature_flags.py             # Feature flags e timeouts configuraveis
│   ├── permissions.py               # ContextVar session_id, event_queue, thread-safety
│   ├── settings.py                  # Constantes e configuracoes do SDK
│   └── skills_whitelist.py          # Allow-list de skills expostas ao agente (budget truncamento)
├── hooks/                           # Hooks do Agent SDK — 2 arquivos
│   ├── __init__.py
│   └── README.md
├── prompts/                         # Prompts do agente web — 4 arquivos
│   ├── __init__.py
│   ├── preset_operacional.md        # Preset customizado (substitui claude_code preset)
│   ├── prompt_inventario.md         # Prompt operacional inventario 2026-05 (NACOM/LF)
│   └── system_prompt.md             # System prompt do agente (usuarios finais)
├── sdk/                             # Integracao com Claude Agent SDK — 26 arquivos
│   ├── __init__.py
│   ├── _sanitization.py             # Helpers de sanitizacao PII cross-modulo
│   ├── baseline_fastpath.py         # Fast-path deterministico do baseline (Marcus user_id=18, sem loop LLM)
│   ├── vinculacao_fastpath.py       # Fast-path deterministico vinculacao NF×PO (Gabriella; N0 regex + N1 Haiku; sem subagente gestor-recebimento)
│   ├── client.py                    # Client principal (streaming, build_options, parse)
│   ├── client_pool.py               # Pool de clients reutilizaveis
│   ├── context_enrichment.py        # Enriquecimento de contexto per-request (blueprint agente)
│   ├── cost_tracker.py              # Rastreamento de custos por sessao
│   ├── hooks.py                     # 8 SDK hook closures (build_hooks() factory)
│   ├── memory_injection.py          # Pipeline multi-tier de injecao de memorias
│   ├── memory_injection_rules.py    # Regras declarativas de injecao (paths + filtros)
│   ├── model_router.py              # Routing de modelo per-request (per-user/preset)
│   ├── pending_questions.py         # AskUserQuestion (dual event: sync + async)
│   ├── plan_state.py                # Estado de plano/super-loop (PlanState + Tasks, shadow)
│   ├── plan_triage.py               # Triagem de plano (B-TRIAGE shadow, blueprint A/B)
│   ├── pricing.py                   # Tabela precos por modelo (input/output/cache_creation/cache_read)
│   ├── session_archive.py           # Archive tar.gz S3 de sessoes expiradas
│   ├── session_persistence.py       # Persistencia JSONL de sessoes SDK
│   ├── session_store_adapter.py     # Adapter PostgresSessionStore (Fase B cutover)
│   ├── shutdown_state.py            # Flag global atexit (suprime Sentry de RuntimeError shutdown)
│   ├── sticky_session.py            # Afinidade de sessao por processo (R-SPLIT-NGINX / Pattern 2)
│   ├── stream_parser.py             # Dataclasses + classificacao de erros de tool
│   ├── subagent_reader.py           # Wrapper list_subagents + get_subagent_messages (SDK 0.1.60)
│   ├── turn_context_registry.py     # Resolve falante do turno em grupos Teams (client do pool reusado NAO reaplica hooks — Fase B)
│   ├── verifiers.py                 # Verificadores B2 (verify shadow do super-loop)
│   └── vincular_teams_fastpath.py   # Fast-path meta-comando `vincular ABC123` (pareamento identidade Teams, sem LLM/sessao)
├── services/                        # Servicos de inteligencia — 25 arquivos (ver services/CLAUDE.md)
│   ├── __init__.py
│   ├── CLAUDE.md                    # Sub-guia com regras R1-R5 dos services
│   ├── _utils.py                    # Helpers compartilhados (parse_llm_json_response)
│   ├── adhoc_capture_service.py     # Captura ad-hoc de conhecimento/correcao fora do ciclo pos-sessao
│   ├── approval_inbox_service.py    # Inbox de aprovacao (AgentMemory shadow + ImprovementDialogue proposed)
│   ├── artifact_service.py          # Service de artifacts (rate limit, spec validation, S3)
│   ├── directive_promotion_service.py # Promocao automatica de diretriz (A4 flywheel Distill→Deploy)
│   ├── regression_gate.py           # Gate puro de regressao (eval_gate — sobrevivente do A3 aposentado, R2 2026-06-12)
│   ├── friction_analyzer.py         # Analise de friccao de uso
│   ├── improvement_suggester.py     # Dialogo D8 melhoria (batch + real-time)
│   ├── insights_service.py          # Gerador de insights pos-sessao
│   ├── intersession_briefing.py     # Briefing entre sessoes
│   ├── knowledge_graph_service.py   # Grafo de conhecimento (memorias)
│   ├── memory_consolidator.py       # Consolidacao de memorias redundantes
│   ├── memory_format.py             # Serializador canonico de memorias (meta JSONB + sentinela) — PURO sem DB
│   ├── metrics_dashboard_service.py # Dashboard telemetria subagent (Fase A1+A3)
│   ├── ontology_bootstrap.py        # Bootstrap da ontologia (knowledge graph / ontology_query)
│   ├── pattern_analyzer.py          # Extracao de padroes e conhecimento
│   ├── recommendations_engine.py    # Motor de recomendacoes
│   ├── sentiment_detector.py        # Deteccao de sentimento
│   ├── session_summarizer.py        # Resumo automatico de sessoes
│   ├── skill_effectiveness_service.py # Avaliador de efetividade de skill pos-sessao (Fase 1, flag AGENT_SKILL_EVAL)
│   ├── sql_evaluator_falses_service.py # Detector de falsos negativos em SQL evaluator
│   ├── suggestion_generator.py      # Gerador de sugestoes proativas
│   ├── teams_observability_service.py # KPIs observabilidade canal Teams (teams_tasks + agent_step, read-only)
│   └── tool_skill_mapper.py         # Mapeamento tool → skill
├── templates/agente/                # Templates Jinja2 — 7 arquivos
│   ├── admin_metrics.html           # Dashboard telemetria subagent (Chart.js 3.9.1, admin)
│   ├── admin_session_store.html     # Dashboard admin SessionStore (R6 observability)
│   ├── admin_teams.html             # Dashboard observabilidade canal Teams (F2, admin)
│   ├── artifact.html                # Pagina render bundle artifact (sandboxed iframe)
│   ├── chat.html                    # Interface de chat web
│   ├── insights.html                # Dashboard de insights
│   └── memorias.html                # Tela admin de gestao de memorias (/agente/memorias)
├── tools/                           # MCP tools (NAO callables) — 15 arquivos
│   ├── __init__.py
│   ├── _mcp_enhanced.py             # Wrapper Enhanced (outputSchema + structuredContent)
│   ├── artifact_tool.py             # build_artifact MCP tool (Enhanced v1.0)
│   ├── buscar_tabelas_tool.py       # buscar_tabelas: descoberta de tabela por intencao (S1, Enhanced v1.0)
│   ├── memory_mcp_tool.py           # 13 operacoes de memoria (Enhanced v2.2.0)
│   ├── ontology_query_tool.py       # Query da ontologia/knowledge graph (MCP tool)
│   ├── playwright_mcp_tool.py       # Browser automation (13 tools, SSW + Atacadao)
│   ├── resolver_mcp_tool.py         # Resolvedores deterministicos (app.resolvedores) — fonte-que-prova entidade
│   ├── render_logs_tool.py          # Consulta logs Render
│   ├── routes_search_tool.py        # Busca em rotas Flask
│   ├── schema_mcp_tool.py           # Consulta schemas de tabelas
│   ├── session_search_tool.py       # 5 operacoes de busca em sessoes (Enhanced v4.1.0)
│   ├── sql_session_context.py       # Helpers de contexto SQL por sessao
│   ├── teams_card_tool.py           # Adaptive Cards para Teams (rich responses)
│   └── text_to_sql_tool.py          # Text-to-SQL (Enhanced v2.0.0)
├── utils/                           # Helpers de modulo — 2 arquivos
│   └── pii_masker.py                # Mascaramento regex CPF/CNPJ/email (SDK 0.1.60 fase 2)
└── workers/                         # Workers RQ locais — 8 arquivos (eval_runner removido — R2 2026-06-12)
    ├── __init__.py
    ├── artifact_worker.py           # build_artifact_job (Vite+React+TS+Tailwind, queue artifacts)
    ├── background_jobs.py           # Jobs background diversos (varredores D8, enqueue)
    ├── calibration_sampler.py       # Amostra turnos para calibracao do judge (flag AGENT_CALIBRATION_SAMPLER)
    ├── plan_verifier.py             # Verify B2 do super-loop (shadow, queue agent_judge)
    ├── step_judge.py                # Judge por step do plano (shadow)
    ├── subagent_validator.py        # Haiku anti-alucinacao (SDK 0.1.60 fase 4, queue agent_validation)
    └── triage_shadow.py             # B-TRIAGE shadow (replan/escalate adiado — ver memoria b3-escalate)
```

---

## Arquitetura de Prompts (v3 — 28/03/2026)

### Principio: Separacao Estrutural (DOC-1.md)

Segue o modelo de 5 camadas do Agent SDK (Anthropic):
1. **System prompt** (`system_prompt`) → comportamento e routing (estatico, cacheavel)
2. **Tools** (`mcp_servers`) → capacidades como dados estruturados (auto-descritos)
3. **Skills** (`SKILL.md` filesystem) → conhecimento de dominio (progressive disclosure)
4. **Subagents** (`agents` dict) → alvos de delegacao (cada um com tools/skills proprios)
5. **Control** (hooks + `allowed_tools`) → permissoes e enforcement

> Detalhe oficial por camada — frontmatter de subagent, secoes obrigatorias do system prompt e gotchas do modelo (Claude 4.x): `.claude/references/AGENT_DESIGN_GUIDE.md` + `.claude/references/AGENT_TEMPLATES.md`.

### Dois modos (feature flag `USE_CUSTOM_SYSTEM_PROMPT`)

| Flag | System Prompt | Identidade | Tokens |
|------|--------------|------------|--------|
| `false` | `{preset: "claude_code", append: system_prompt.md}` | Claude Code + Agente (conflito) | ~7K |
| `true` (default) | `preset_operacional.md + system_prompt.md + empresa_briefing.md` (string) | Apenas Agente (coerente) | **ver bloco auto-medido ↓** |

### Camadas (com flag true)

```
STRING custom (option `system_prompt`) — 3 arquivos concatenados em _build_full_system_prompt():
  1. preset_operacional.md   ← Tools, safety, environment
  2. system_prompt.md        ← Comportamento, routing, regras
  3. empresa_briefing.md     ← Vocabulario, cadeia de valor Nacom
  (tamanhos reais por arquivo: ver bloco auto-medido abaixo)
+ CLAUDE.md raiz via setting_sources      ← project context (FORA da string custom)
+ Dynamic injections (hook UserPromptSubmit) ← memorias, session_context, diretivas
```

> **Tamanho real = AUTO-MEDIDO.** Rode `python scripts/audits/prompt_size_audit.py`
> apos qualquer edicao de prompt. NUNCA hardcodar de cabeca: esta doc ja esteve
> ~6.5x defasada (afirmava ~2.7K, real ~17.5K — corrigido FASE 1 refactor 2026-06-04,
> ver `docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md`).

<!-- prompt-size:start (auto: scripts/audits/prompt_size_audit.py --update-claude-md) -->
| Componente | Linhas | Bytes | Tokens (est.) |
|------------|-------:|------:|--------------:|
| `preset_operacional.md` | 117 | 5079 | ~1.5K tok |
| `system_prompt.md` | 767 | 47853 | ~13.7K tok |
| `empresa_briefing.md` | 81 | 5084 | ~1.5K tok |
| **TOTAL estatico** | **965** | **58016** | **~16.6K tok** |

> Medido por `scripts/audits/prompt_size_audit.py` (tokens = bytes/3.5, estimativa pt-BR+XML). NUNCA editar a mao — rode `--update-claude-md`.
<!-- prompt-size:end -->

> Gatilho de poda (FASE 5): o pre-commit roda `prompt_size_audit.py --check-delta`
> e bloqueia qualquer commit que faça o prompt **crescer** vs `prompt_size_baseline.json`
> sem decisão consciente. Crescimento legítimo: rode `--update-baseline && --update-claude-md`.

### Separacao de responsabilidades

| Arquivo | O QUE define | NAO define |
|---------|-------------|------------|
| `preset_operacional.md` | AWARENESS: tool prioritization, safety, /tmp, persistent systems | Identidade, regras de negocio |
| `system_prompt.md` | COMPORTAMENTO: R0-R7, I2-I4, routing strategy, subagent coordination | Tool descriptions (auto-descritas), knowledge_base (no CLAUDE.md) |
| `CLAUDE.md` (raiz) | REFERENCIA: indice unificado de docs, gotchas de modelos, subagentes | Regras dev, CSS, caminhos de modulo (em ~/.claude/CLAUDE.md) |
| `~/.claude/CLAUDE.md` | DEV-ONLY: Quick Start, migrations, CSS, caminhos, refs dev-only | Visivel apenas ao Claude Code |

### O que mudou na v3 (v4.2.0 do system_prompt)

| Mudanca | Racional (DOC-1.md) | Tokens salvos |
|---------|---------------------|---------------|
| R5: tabela MCP removida | Tool descriptions sao auto-descritas — duplicar no prompt e anti-pattern | ~150 |
| P1-P7: inline �� referencia | Agente delega a `analista-carteira`, nao decide P1-P7 sozinho | ~300 |
| knowledge_base: 17 entradas → ponteiro para CLAUDE.md | Root CLAUDE.md ja fornece indice unificado via `setting_sources` | ~200 |
| Subagent reliability: adicionado | Protocolo `/tmp/subagent-findings/` na coordination_protocol | +30 |
| Root CLAUDE.md: reorganizado | Subcategorias (Odoo, SSW, Infra), entradas dev-only movidas | — |
| analista-carteira.md: DRY | P1-P7 referencia REGRAS_P1_P7.md ao inves de inlinar | ~200 |
| Prompt Cache Optimization | `{data_atual}`, `{usuario_nome}`, `{user_id}` extraidos do system_prompt → injecao via hook `session_context`. System prompt estatico → cache hits | ~20 (vars) |
| Enhanced MCP Migration | Memory (11 tools) + Sessions (4 tools) migradas para `@enhanced_tool` com `outputSchema` + `structuredContent` | — |

### Rollback
- `AGENT_CUSTOM_SYSTEM_PROMPT=false` restaura preset claude_code
- `AGENT_PROMPT_CACHE_OPTIMIZATION=false` restaura variaveis dinamicas no system prompt (via prepend)

### Arquivos envolvidos
- `prompts/preset_operacional.md` — preset customizado (tamanho no bloco auto-medido — `prompt_size_audit.py`)
- `prompts/system_prompt.md` — system prompt operacional (v4.4.0, estatico — sem vars dinamicas)
- `sdk/client.py` — `_format_system_prompt()` (guard cache), `_user_prompt_submit_hook()` (session_context)
- `config/feature_flags.py` — `USE_CUSTOM_SYSTEM_PROMPT`, `USE_PROMPT_CACHE_OPTIMIZATION`
- `config/settings.py` — `operational_preset_path`

### Governanca do prompt (FASE 5 — impede a acrecao de voltar)

> O prompt dobrou (407→862 linhas em ~6 semanas) porque tinha processo de ADICAO
> (todo incidente virava regra) e nenhum de PODA. Estas regras SAO o processo de poda.

**Checklist OBRIGATORIO antes de adicionar QUALQUER regra ao prompt (R-EXEC-5):**
1. **E principio (Camada 0) ou procedimento (Camada 1)?**
   - Principio (identidade, constituicao, regra de negocio como CONCEITO, routing de alto nivel) → fica no prompt.
   - Procedimento hiper-especifico (campos Odoo, nome de wizard, location, passo-a-passo, pos-mortem `sessao <hex>`) → vai para skill/reference (`GOTCHAS.md`, `REGRAS_MODELOS.md`, `REGRAS_OUTPUT.md`); o prompt guarda so' o PRINCIPIO + gatilho (3-5 linhas).
2. **Remover esta linha causa erro mensuravel?** Se nao → nao entra (ou sai). (`.claude/references/STUDY_PROMPT_ENGINEERING_2026.md` secao A-pruning / P1.)
3. **Motivacao (`<why>`) e' FORCA, nao gordura** — explicar o porque melhora instruction following (A2 Top Strength 5/5). Comprimir SO' procedimento, NUNCA motivacao. (Licao da FASE 2: cortar `<why>` degradou e foi revertido — `fee8f1f17`.)
4. **A informacao esta na CAMADA certa?** (F6 PAD-CTX) — antes de adicionar/mover conteudo em QUALQUER camada do contexto do agente (preset, system_prompt, CLAUDE.md, listing de skills, hook dinamico, memorias): aplicar o **checklist de admissao por camada** + tabela de orcamento por bloco de `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md` (secoes "Criterios de admissao (perguntas diagnosticas)" e "Hook dinamico — layout, orcamento e ordem"). Intocaveis (M1-M6) listados la em "Intocaveis e licoes aprendidas".

**Gatilho automatico:** o pre-commit (`prompt_size_audit.py --check-delta`, hook `pre-commit-prompt-lint.sh`) BLOQUEIA todo commit que faca o prompt CRESCER vs `prompt_size_baseline.json`. Crescimento consciente (com poda compensatoria) = rodar `--update-baseline && --update-claude-md` e incluir no mesmo commit. Bypass: `git commit --no-verify`. O mesmo hook roda os checks PAD-CTX: consistencia de subagentes + nao-orfandade da deny-list (`--check-consistency`), orcamento do listing (`skills_listing_audit.py --check`), orcamento do hook dinamico (`tests/agente/sdk/test_hook_budget.py` quando o pipeline de injecao e tocado — F6) e o **tripwire de roteamento** (`--check-routing`): BLOQUEIA mudar a capacidade de um subagente (skills do frontmatter `.claude/agents/*.md`) SEM revisar o `<delegate_when>`/`<capabilities>` dele no `system_prompt` (bug real #164 — `auditando-reclassificacao-odoo` entrou no `auditor-financeiro` mas o gatilho de delegacao ficou so' "reconciliacao", entao o principal nunca delegava e improvisava Bash). Mudanca consciente (revisou o gatilho, ou ja' cobre) = rodar `--update-routing-baseline` e incluir `scripts/audits/subagent_routing_baseline.json` no mesmo commit.

**Cadencia de review (T5.4):** review do system_prompt e' **trimestral** (prometida em `STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` e nao cumprida — religada aqui). Ultima: v4.2.0 (abr/2026, score 4,39/5). **Proxima: jul/2026.** Gatilho extra: sempre que o `--check-delta` for bypassado (`--no-verify`) ou o baseline subir, agendar re-review. A fonte de tamanho e' o bloco auto-medido acima (nunca de cabeca). Itens de roadmap pendentes (R5-R17, P1-P3): `.claude/references/ROADMAP_PROMPT_ENGINEERING_2026.md`.

---

## Regras Criticas

### R1: Dois IDs de sessao — NUNCA confundir
- `session_id` (nosso UUID) → persistencia no banco (`AgentSession.session_id`)
- `sdk_session_id` (efemero do CLI) → armazenado em `data['sdk_session_id']` (JSONB, NAO coluna)
- **Resume** usa `sdk_session_id` (CLI carrega sessao do disco)
- **Banco** usa `session_id` (nosso controle, FK em queries)
- Confundir os dois causa sessao perdida ou mensagens em sessao errada
- ~~`sdk_session_transcript` e TEXT separado~~ REMOVIDA em Fase C (2026-04-21) — transcript vive em `claude_session_store`
- **GOTCHA restore**: `session_persistence.py:136` — se JSONL existe no disco, NAO re-restaura do banco. JSONL corrompido (crash, escrita parcial) → resume falha silenciosamente, SDK cria sessao nova, contexto perdido sem erro visivel

### R2: Thread-safety — 3 mecanismos distintos
| Mecanismo | Para que | Onde |
|-----------|----------|------|
| `ContextVar` (`_current_session_id`) | `session_id` (isolamento por thread E coroutine) | `permissions.py:46` |
| Dict global `_stream_context` + Lock | `event_queue` (cross-thread) | `permissions.py:40-41` |
| Dict `_teams_task_context` | Associar sessao <> TeamsTask | `permissions.py:98` |

**Fase 1 (Async Migration)**: `threading.local()` substituido por `ContextVar` para session_id.
ContextVar funciona em threads E coroutines. API externa inalterada (`set/get_current_session_id`).
NUNCA substituir ContextVar por variavel global — causa race condition entre threads/coroutines.
`event_queue` PRECISA ser global porque o endpoint SSE acessa de outra thread.

### Async Migration — Dual Event (pending_questions.py)
`PendingQuestion` agora tem `async_event: Optional[asyncio.Event]` alem do `threading.Event`.
- `register_question()` cria `asyncio.Event` se em async context
- `submit_answer()` sinaliza AMBOS events
- `async_wait_for_answer()` suspende coroutine (nao bloqueia thread)
- `cancel_pending()` desbloqueia AMBOS events
- `wait_for_answer()` (sync) mantido como fallback

**CUIDADO**: `asyncio.Event.set()` em `submit_answer()` e chamado de outra thread (Flask route).
No CPython o GIL protege, mas nao e oficialmente thread-safe. Se houver race condition,
substituir por `loop.call_soon_threadsafe(pq.async_event.set)`.

### R3: Stream safety — None sentinel + done_event
| Camada | Timeout | Funcao |
|--------|---------|--------|
| Heartbeat SSE | 10s | Evita proxy/Render matar conexao idle |
| Inatividade (renewal) | 300s | Renovavel a cada evento/chunk — timeout se parar de emitir (era 240s ate 2026-05-25) |
| Stream max | 1740s (web) / sem teto (teams) | Teto absoluto. Era 540s/600s ate 2026-05-25 (3 timeouts em 7d). Render permite 100min ([fonte](https://render.com/articles/real-time-ai-chat-websockets-infrastructure)) |
| None sentinel | finally | Garante que SSE generator termina |

NUNCA remover o `yield None` no `finally` do generator — frontend trava esperando eventos.

**`streaming_done_event`** (`client.py:2627`): `asyncio.Event()` que controla o prompt generator. Se NAO chamar `.set()` em QUALQUER error path, o generator fica preso em `done_event.wait(timeout=600)` → processo zombie por 10min. Chamado em 6 locais nos except handlers + 1 bloco `finally` como rede de seguranca.

**DC-8 (CancelledError bypass)**: `asyncio.CancelledError` e `BaseException` (NAO `Exception`) desde Python 3.9. Teams usa `asyncio.wait_for(timeout=chunk_timeout)` per-chunk que cancela via `CancelledError` — bypassa TODOS os 5 except handlers. O bloco `finally` em `_stream_response()` garante que `streaming_done_event.set()` SEMPRE e chamado, mesmo para `CancelledError`, `KeyboardInterrupt` e `SystemExit`. **O path persistente (`_stream_response_persistent`) e IMUNE porque `streaming_done_event = None`.**

**REGRA**: Ao adicionar NOVO error handler em `_stream_response()`, o `finally` block e a rede de seguranca definitiva — NAO precisa chamar `.set()` no novo handler (mas e boa pratica como defense-in-depth).

### R4: AskUserQuestion — blocking cross-arquivo + cross-worker (Redis)
Fluxo cruza 3 arquivos: `pending_questions.py` → `permissions.py` → `routes/chat.py`
- Web: event_queue SSE → frontend responde → POST `/api/user-answer` → Event.set()
- Teams: TeamsTask.status='awaiting_user_input' → Adaptive Card → POST resposta → Event.set()
- Timeout web: 55s. Timeout Teams: 120s (`TEAMS_ASK_USER_TIMEOUT`)

Alterar um arquivo sem verificar os outros 2 quebra o fluxo silenciosamente.

**R-CLI-CRASH (2026-05-12)**: `client.py:1957` respeita `resume_state['failed']`
setado pelo probe ao session_store. Antes, codigo ignorava a flag e fazia
`--resume X` mesmo com sessao confirmadamente ausente do PostgresSessionStore,
causando CLI exit code 1 + `CLIConnectionError "Failed to write to process stdin"`
em ~0.8s, com 2 retries automaticos do Teams services falhando identicamente
(observado em ~22 ocorrencias/2h em prod). Fix:
- `client.py:1957` (R1): se `probe_failed=True`, pular `_with_resume` e usar fallback
  XML via hook `UserPromptSubmit` (`hooks.py:1036` injeta `resume_state['fallback']`
  no `additionalContext`).
- `client.py:2238` (R2): handler `CLIConnectionError` agora detecta resume-related
  (elapsed < 5s + sem partial_text + resume_id) e emite `done` com
  `recoverable_resume_failure=True` em vez de error visivel. Caller (Teams services
  v2/v3) retenta — segunda tentativa entra com `resume_state['failed']=True`
  novamente e o fix R1 evita o crash.
- Defesa em profundidade: R1 evita 95% dos casos upstream; R2 captura edge cases
  (ex: probe nao executou por excecao, mas CLI ainda crashou).

**R-MULTIWORKER (2026-05-12)**: `pending_questions.py` usa Redis SETEX + pub/sub
para sincronizar entre os 4 workers gunicorn. Antes, `_pending` era dict
process-local → POST `/api/user-answer` caia em worker ≠ do registro em 75%
das tentativas → 404 silencioso + timeout 55s. Solucao:
- `register_question`: marca Redis `agent:pq:{sid}` (TTL 130s) + spawna subscriber
  daemon thread que escuta `agent:pq:answer:{sid}` e `agent:pq:cancel:{sid}`.
- `submit_answer` (qualquer worker): tenta local; se nao encontrar, valida Redis
  EXISTS e faz PUBLISH. Subscriber no worker dono recebe e sinaliza Event LOCAL.
- `get_pending_tool_input` tem fallback cross-worker via Redis GET.
- Feature flag: `AGENT_REDIS_PENDING_QUESTIONS=false` faz rollback p/ memory-only.
- Sem Redis: degrada para legacy (funciona dentro do mesmo worker, falha cross).
- API publica 100% preservada — callsites em `permissions.py`, `chat.py`, `bot_routes.py` nao mudaram.

### R5: MCP tools — NAO callable
Tools em `tools/` sao registros MCP (ToolAnnotations). O agente usa `mcp__X__Y` diretamente.
NUNCA importar e chamar como funcao Python — nao sao callables, gera erro silencioso.
Por que (mecanismo: wrapper `claude_agent_sdk` vs MCP spec): `.claude/references/MCP_CAPABILITIES_2026.md`.

### R6: MCP Enhanced Wrapper
`tools/_mcp_enhanced.py` adiciona `outputSchema` + `structuredContent` (MCP spec 2025-06-18).
- Usar `@enhanced_tool` + `create_enhanced_mcp_server` para tools que precisam de structured output
- Migradas: SQL (v2.0.0), Memory (v2.0.0), Sessions (v4.0.0). Demais usam `@tool` standard
- Ref completa: `.claude/references/MCP_CAPABILITIES_2026.md`

### R7: JSONB — flag_modified
Manter o padrao existente em `models.py`: SEMPRE `flag_modified(session, 'data')` apos modificar JSONB.

### R9: Audit Hook Deterministico Odoo — propagacao via PreToolUse (2026-05-28)

`sdk/hooks.py:_keep_stream_open` (PreToolUse) prefixa o `command` de tool `Bash` com env exports. DOIS propositos:
- **`export NACOM_QUIET_BOOT=1` — SEMPRE** (independente de flags; BUG #1 2026-06-08): silencia os logs de boot do `import app` nos scripts CLI de skill (helper `app/utils/boot_log.py`) → stdout/stderr limpos para o agente parsear o resultado.
- **vars de auditoria — quando `AGENT_ODOO_AUDIT_HOOK=true`**: prefixa `export AGENT_SESSION_ID=<ctx> AGENT_TOOL_USE_ID=<tuid> AGENT_TYPE=<atype> AGENT_USER_NAME=<uname>`. Subprocess Bash herda as ENV vars → script Python da skill chama `OdooConnection.execute_kw` → hook em `app/utils/odoo_audit_helpers.py` registra em `operacao_odoo_auditoria` correlacionando com sessao.

**Race-free**: usa `hookSpecificOutput.updatedInput` (SDK 0.1.29+, dict[str, Any]) — isolado por tool call, nao depende de `os.environ` global (que quebraria multi-worker gunicorn).

**Cuidados**:
- Hook NUNCA quebra a tool (try/except + log debug)
- shlex.quote escapa valores (defesa contra injection)
- Quando `AGENT_ODOO_AUDIT_HOOK` OFF, o hook ainda prefixa `NACOM_QUIET_BOOT=1` (silenciar boot), mas NAO as vars de auditoria
- ContextVar `_current_session_id` em `permissions.py:46` e a fonte de `AGENT_SESSION_ID`

Ver `app/odoo/CLAUDE.md` secao P8 para detalhes do hook lado Odoo.
Migration: `scripts/migrations/2026_05_28_operacao_odoo_auditoria_session.{py,sql}`.

### R10: Persistencia da resposta — PRIMARY (thread daemon) vs DEFESA (generator finally)

No path persistente ha 2 gravacoes da resposta em `agent_sessions.data`:
- **PRIMARY**: `finally` da thread daemon `run_async_stream` — roda quando o turno
  COMPLETA, com `full_text` preenchido. E' quem deve salvar a resposta.
- **DEFESA**: `finally` do generator `_stream_chat_response`
  (`source='finally_generator'`) — rede de seguranca caso o primary falhe/morra.

**INVARIANTE (`_should_persist_in_finally`, 2026-05-29)**: a DEFESA so' persiste se
a thread daemon JA terminou (`not thread.is_alive()`). Se a thread ainda processa
(cliente desconectou mid-turno), a defesa DELEGA ao primary. Persistir na defesa
com a thread viva gravaria `full_text` vazio e marcaria `_persisted=True`,
BLOQUEANDO o primary de salvar a resposta real (race que perdia a resposta —
sessao do Marcus: 6 user / 0 assistant no banco apesar do HOOK:Stop). Como
`add_user_message`/`add_assistant_message` NAO sao idempotentes, a defesa NAO pode
rodar em paralelo ao primary.

**Frontend**: ao cair a conexao mid-turno, `startDeferredResponsePoll` (chat.js)
busca a resposta ja' persistida e a renderiza sem recarga manual (associa a 1a
`assistant` apos a ultima `user` de mesmo conteudo — robusto porque o primary
persiste user+assistant atomicamente no mesmo commit).

---

## Hierarquia de Timeouts

Timeouts em 4 arquivos com **deadline renewal**. DEVEM respeitar esta ordem ou causam cascata de falhas:

| Timeout | Valor | Fonte | Funcao |
|---------|-------|-------|--------|
| Heartbeat SSE | 10s | `routes/_constants.py` | Keep-alive para proxy |
| AskUser web | 55s | `pending_questions.py:30` | Espera resposta do usuario |
| AskUser Teams | 120s | `feature_flags.py` | Idem, via Adaptive Card |
| **Web inatividade** | 300s | `routes/_constants.py` | Renovavel a cada evento real (heartbeats NAO renovam) — era 240s ate 2026-05-25 |
| **Teams inatividade** | 300s | `services.py:1086` | Renovavel a cada chunk recebido — era 240s ate 2026-05-25 |
| SDK stream_close | 240s | `client.py:547` | Timeout CLI hooks/MCP |
| Job `validate_subagent_output` | 60s | `hooks.py:SubagentStop enqueue` | Timeout RQ para validacao Haiku |
| Web teto absoluto | 1740s | `routes/_constants.py` | Teto absoluto SSE (margem 60s vs gunicorn 1800s) — era 540s ate 2026-05-25 |
| Teams teto absoluto | — | — | Sem teto absoluto (DC-9, INACTIVITY_TIMEOUT renovavel) |
| Gunicorn timeout | 1800s | `start_render.sh` gunicorn_config | Per-request heartbeat gthread — era 600s ate 2026-05-25 |
| Render hard limit | 100min (6000s) | infra | Render permite ate 100min ([fonte](https://render.com/articles/real-time-ai-chat-websockets-infrastructure)) |

**Deadline renewal**: operacoes longas com progresso continuo NAO sao mais mortas pelo timeout fixo. A cada chunk/evento recebido, o deadline de inatividade (300s) e renovado. Apenas inatividade real (5 min sem progresso) ou teto absoluto disparam timeout.

**REGRA**: `USER_RESPONSE_TIMEOUT` (55s) DEVE ser < timeout do SDK (240s). Se >= SDK, o CLI mata o stream antes do usuario responder.

---

## Gotchas

### system_prompt.md vs preset_operacional.md vs CLAUDE.md
- `prompts/system_prompt.md` = identidade + regras do agente web (usuarios finais)
- `prompts/preset_operacional.md` = tool instructions + safety (substitui preset claude_code)
- Este arquivo (`CLAUDE.md`) = Claude Code (dev). NUNCA misturar prompts dev com prompts agente.
- Ver secao "Arquitetura de Prompts" acima para detalhes da separacao.

### SDK max_buffer_size: 10MB
`client.py:561` configura `max_buffer_size=10_000_000` (10MB). Default do SDK e 1MB — insuficiente para screenshots base64 (PNG full-page: 1.3-2.6MB). Se reduzir abaixo de 2MB, browser_screenshot volta a crashar com "JSON message exceeded maximum buffer size".

### Screenshot compression: 750KB limit
`playwright_mcp_tool.py:516` comprime PNG → JPEG se > 750KB (escalonamento JPEG 80% → resize 50% → 25%; PNG original em disco; requer Pillow). Detalhe + paths S3: `.claude/references/S3_STORAGE.md` §2.

### Prerequisitos de execucao
1. **`set_current_user_id()` ANTES do stream** — MCP tools (`memory_mcp_tool.py:33`, `session_search_tool.py:25`) usam `ContextVar` independentes. Se esquecer: `RuntimeError("user_id nao definido")`. CADA tool tem seu PROPRIO ContextVar.
2. **`get_or_create()` NAO e atomico** (`models.py:380-395`) — query + insert separados, sem `SELECT FOR UPDATE`. Duas threads podem criar sessao duplicada → `IntegrityError`. NUNCA assumir retorno valido sem try/except.
3. **Cascade delete** — `models.py` define `cascade='all, delete-orphan'` nos backrefs (linhas 79, 469, 689). `db.session.query(Model).filter_by(...).delete()` NAO dispara cascade → orphans. DEVE usar `db.session.delete(obj)`.

### Workers RQ: job_id NAO pode conter ":" (RQ 2.6.1)
`rq.job.Job.set_id` levanta `ValueError('id must not contain ":"')`. `AgentStep.step_uid` = `'{session_id}:{turn_seq}'` SEMPRE tem `:`. Qualquer `job_id` derivado DEVE sanitizar: `job_id=f"prefixo-{step_uid.replace(':','-')}"`. O try/except por-step ENGOLE o erro → feature fica 100% inerte SEM teste pegar (MagicMock nao valida job_id). Pegar com `assert ':' not in job_id`.

### Custo: `ResultMessage.total_cost_usd` e ACUMULADO (nao por-turno)
O SDK reporta o custo running-total da sessao SDK — CRESCE a cada turno (e zera quando a sessao SDK e recriada/resume). `_save_messages_to_db` (`routes/chat.py`) converte em DELTA via `sdk/pricing.py:turn_cost_from_cumulative` ANTES de somar em `AgentSession.total_cost_usd`; o acumulado anterior fica em `data['_sdk_cost_cumulative']` (+`_sdk_cost_session_id` p/ detectar reset). NUNCA somar o valor cru por-turno: inflava `total_cost_usd` e `agent_session_costs.cost_usd` ~Nx (N=turnos) — bug 2026-06-19 (sessao reportada $223.59 vs $31.92 real; global 30d 3.0x). Historico corrigido por `scripts/migrations/2026_06_19_backfill_agent_cost_dedup.py` (idempotente/reversivel).

### S3 Storage (screenshots, archive)

Screenshots Playwright (`playwright-screenshots/{YYYY-MM}/`) e archive de sessoes (`agent-archive/{YYYY-MM}/{session}.tar.gz`) usam S3 compartilhado via `get_file_storage()`. Ambos sao best-effort (falha silenciosa se USE_S3=false ou erro de rede). Detalhes completos: `.claude/references/S3_STORAGE.md`.

### Arquivos legados — NAO usar, NAO estender
| Arquivo | Status |
|---------|--------|
| `historia.md` (76K) | Apenas referencia historica |

### Services (25 arquivos, ~14.9K LOC)
Guia completo de regras (R1-R5), gotchas e interdependencias: [`services/CLAUDE.md`](./services/CLAUDE.md).
Todos controlados por feature flags em `config/feature_flags.py`.

### MCP Tools de memoria (memory_mcp_tool.py v2.2.0 Enhanced, 13 operacoes)
| Tool | O que faz |
|------|-----------|
| `view_memories` | Le memoria por path |
| `save_memory` | Cria/atualiza memoria (popula `meta` JSONB + normaliza content p/ paths estruturados) |
| `update_memory` | Atualiza conteudo existente |
| `delete_memory` | Remove memoria |
| `list_memories` | INDICE navegavel (agrupa por kind/dominio + contagens + paths, SEM conteudo; filtros kind/dominio/escopo/prefix/query/limit; exclui frias). NAO eh mais dump |
| `clear_memories` | Limpa TODAS (destrutivo) |
| `search_cold_memories` | Busca no tier frio |
| `view_memory_history` | Consulta historico de versoes de uma memoria |
| `restore_memory_version` | Restaura versao anterior (backup automatico do atual) |
| `resolve_pendencia` | Marca pendencia como resolvida (desaparece do briefing) |
| `log_system_pitfall` | Registra armadilha/gotcha do sistema (max 20, category=structural) |
| `query_knowledge_graph` | Consulta relacoes entre entidades no Knowledge Graph de memorias |
| `register_improvement` | Registra sugestao de melhoria real-time para Claude Code (skill_bug, skill_suggestion, etc.) |

**Admin (debug mode)**: TODAS as 13 tools aceitam `target_user_id=N` para acesso cross-user.
Validacao: `_resolve_user_id(args)` — requer `get_debug_mode() == True`. Todo acesso logado.
**GOTCHA schema (fix 2026-06-12)**: declarar campo no handler NAO basta — o `input_schema`
dict-simples faz o factory marcar tudo `required` + `additionalProperties:false`, rejeitando
`target_user_id` ANTES do handler. Schemas devem ser dict-completo (type+properties+required);
travado por `tests/agente/tools/test_memory_mcp_schema.py`.

### MCP Tools de sessao (session_search_tool.py v4.1.0 Enhanced, 5 operacoes)
| Tool | O que faz |
|------|-----------|
| `search_sessions` | Busca textual (ILIKE) em sessoes anteriores |
| `list_recent_sessions` | Lista sessoes recentes com titulo, data, resumo |
| `semantic_search_sessions` | Busca semantica via embeddings (fallback ILIKE) |
| `list_session_users` | Lista usuarios com sessoes — **admin-only, debug mode** |
| `get_subagent_transcript` | Transcript completo de subagente executado em uma sessao (tools, duracao, findings) |

**Admin (debug mode)**: `search_sessions`, `list_recent_sessions` e `semantic_search_sessions`
aceitam `target_user_id=N` para busca cross-user. `channel='teams'|'web'` filtra por canal.
Pattern: `_resolve_user_id(args)` espelha `memory_mcp_tool.py`.

### MCP Tools de descoberta de schema (progressive disclosure — S1)
| Tool | O que faz |
|------|-----------|
| `buscar_tabelas` (`buscar_tabelas_tool.py`) | Descobre TABELAS por intencao em linguagem natural — 1a camada: o Opus descreve a intencao e recebe candidatas (nome/dominio/descricao/key_fields) SEM adivinhar o nome. Busca **semantica primaria** (`table_catalog_embeddings`, modelo `voyage-4-large`) **+ textual** (append/fallback); respeita a MESMA matriz de permissao do executor (user_id) |
| `consultar_schema` (`schema_mcp_tool.py`) | Schema detalhado de UMA tabela (campos/tipos/FKs/regras) — 2a camada |
| `consultar_valores_campo` | Valores distintos de um campo categorico |

Fluxo: **intencao → `buscar_tabelas` → `consultar_schema(tabela)` → SQL** (`mcp__sql`).
Semantica do catalogo reindexada no scheduler diario (`reindexacao_embeddings.py`, 11o
modulo) por `content_hash`; modelo isolado em `VOYAGE_TABLE_CATALOG_MODEL` (nao afeta o
default global). Pacote text-to-sql S1 — ver `docs/superpowers/specs/2026-06-07-text-to-sql-arquitetura-MASTER-design.md`.

### Debug Mode — Injecao de Contexto (client.py)

O hook `_user_prompt_submit_hook` injeta `<debug_mode_context>` quando debug mode esta ativo.
Isso permite ao Agent SABER que pode usar `target_user_id`, `channel`, e `list_session_users`.

Sem essa injecao, o Agent opera com debug mode nos bastidores mas NAO sabe que pode usar
as capacidades extras — resultado: falha em investigacao cross-user.

---

## Pipeline SSE — Contrato de 3 Camadas

### R8: Novo evento = atualizar TODAS as 3 camadas

Ao adicionar novo tipo de evento, **OBRIGATORIO** atualizar:

1. **`sdk/client.py:_parse_sdk_message()`** — emitir `StreamEvent(type='xxx', ...)`
2. **`routes/chat.py:_process_stream_event()`** — `elif event.type == 'xxx':` → `_sse_event('xxx', ...)`
3. **`static/agente/js/chat.js`** — `case 'xxx':` no switch de SSE

**Se uma camada faltar, o evento e silenciosamente descartado.** Nao ha validacao automatica.

### Excecao R8: eventos emitidos de `can_use_tool` (raw SSE via event_queue)

`ask_user_question` (`config/permissions.py:419`) e `destructive_action_warning` (`config/permissions.py:620`) violam o contrato de 3 camadas **por design**:

- Sao emitidos de DENTRO do callback `can_use_tool` do SDK (pre-tool hook), nao durante parsing de mensagens.
- `can_use_tool` roda em thread separada, sem acesso a instancia `AgentClient` nem ao parser `_parse_sdk_message`.
- Usam `event_queue.put(f"event: {type}\ndata: {json}\n\n")` diretamente — raw SSE string via `queue.Queue` cross-thread.
- SSE generator em `routes/chat.py` dreva o `event_queue` e repassa para o frontend.
- camada 3 (chat.js case) e mantida normalmente.

**Regra**: ao adicionar novo evento emitido de `can_use_tool` ou outro callback async, usar o mesmo padrao `event_queue.put(raw_sse_string)` — NAO tentar passar por `StreamEvent` (nao ha contexto).

### Mapa de eventos

Inventario completo dos ~23 eventos SSE (camada de origem por evento) + os 8 hooks SDK registrados: ver **§Mapa de eventos SSE** em [`SUBSISTEMAS.md`](SUBSISTEMAS.md). **Consulte ANTES de adicionar/alterar um evento** — a R8 acima e a regra; a tabela e o inventario.

---

## Artifacts

Bundle.html auto-contido (Vite+React+TS+Tailwind) renderizado em modal no chat web (NAO no Teams); build assincrono na fila RQ `artifacts`. Token HMAC + iframe sandboxed (sem `allow-same-origin`) + rate limit 5/user/hora. S3 obrigatorio (bundle grande demais p/ DB — ver `.claude/references/S3_STORAGE.md`).

**Mexendo em artifacts (worker, tool MCP, rotas, modal)? LEIA §Artifacts em [`SUBSISTEMAS.md`](SUBSISTEMAS.md)** — componentes, fluxo de 10 passos, seguranca e os gotchas criticos (Node lazy no worker, fila prioritaria, anti-starvation por perfil de worker, rate limit atomico).

---

## Telemetria per-invocacao de subagent (Fase A)

UMA linha por spawn->stop em `AgentInvocationMetric` (distinta de `agent_session_costs` per-message), cobrindo web + Teams + dev (CLI). Dashboard admin em `/agente/admin/metrics`. Flag `AGENT_INVOCATION_METRICS_PERSIST` (default ON).

**Mexendo no hook de metrica, ingestor dev ou dashboard? LEIA §Telemetria de subagent em [`SUBSISTEMAS.md`](SUBSISTEMAS.md)** — inclui o BRIDGE FIX (subagent SDK 0.1.60+ NAO emite `type:result` no JSONL — sem ele o dashboard zera), o COMMIT GUARD e o roadmap. Integra com `.claude/references/SUBAGENT_RELIABILITY.md` (findings via JSONL).

---

## Memoria Compartilhada (PRD v2.1)

Memoria `escopo=empresa` pertence a user_id=0 ("Sistema", visivel a todos); `escopo=pessoal` a um user_id. A busca inclui SEMPRE `user_id ANY([user_id, 0])` em 4 callsites (embeddings pgvector + fallback, `client.py` recencia, KG). Extracao pos-sessao via `pattern_analyzer.extrair_conhecimento_sessao()` (daemon thread, flag `USE_POST_SESSION_EXTRACTION`).

**Ciclo de vida, categorias, decay, paths padrao e criterios de qualidade**: `.claude/references/MEMORY_PROTOCOL.md` (canonico). **Delta de escopo deste modulo (colunas DB `escopo`/`created_by`, os 4 callsites, role awareness)**: §Memoria Compartilhada em [`SUBSISTEMAS.md`](SUBSISTEMAS.md).

---

## Avaliador de Efetividade de Skill + Inbox de Aprovacao (Fase 1)

Avalia pos-sessao se as skills invocadas resolveram o problema; quando nao, cria lembrete por-usuario (auto) OU propoe lembrete-todos / ajuste-de-codigo via Inbox. **EM PROD desde 2026-06-07** (flag `AGENT_SKILL_EVAL`). Funil custo-zero (sentiment+regex+Bash) -> Haiku -> Sonnet sobre a janela ancorada na invocacao; grava `AgentSkillEffectiveness` (idempotente).

**Separacao de competencias (INVIOLAVEL): o avaliador DESCREVE o problema + evidencia e PEDE ajuda; NUNCA prescreve a solucao** (`implementation_notes`/`affected_files` ficam None — quem resolve codigo e o Claude Code). Vale tambem p/ o D8 `improvement_suggester`.

**Componentes, fluxo, flags e demais gotchas (Teams web-only, PII masking, conserta o `directive_promotion` shadow sem UI)**: §Avaliador de Efetividade de Skill em [`SUBSISTEMAS.md`](SUBSISTEMAS.md). Spec/plano em `docs/superpowers/`.

---

## Versao SDK atual

- **claude-agent-sdk**: `0.2.101` | **CLI bundled**: 2.1.177 (suporta `claude-fable-5`) | **anthropic**: `0.109.1` | **mcp**: `>=1.26.0,<2.0.0` (teto `<2.0.0` exigido pelo claude-agent-sdk 0.2.96+; floor herda fix `CallToolResult` perdido em 0.1.70). Bump 0.2.95→0.2.101 (2026-06-13): CLI bundled 2.1.170→2.1.177 + `TaskUpdatedMessage` tipado (#1016, ADITIVO — não adotado); ZERO breaking. anthropic 0.98.1→0.109.1: sem breaking nos padrões usados (`Anthropic()`/`messages.create`/`APIStatusError`/`APIError`).
- **Modelo default (web)**: `claude-opus-4-8` ($5/$25 per MTok, adaptive thinking, 1M context); configurável pelo usuário e **estável dentro da sessão** — o modelo é decidido 1x por sessão (routing só na 1ª msg) e só troca por escolha EXPLÍCITA do usuário no seletor. Bug 2026-06-15: o smart routing rebaixava Opus→Sonnet mid-sessão (em follow-ups curtos), matando o cache MODEL-SCOPED e confundindo o modelo rebaixado; fix via `pick_warm_model`/`should_switch_model` (`sdk/model_router.py`) + `PooledClient.model`. **Teams roda Sonnet FIXO + `TEAMS_EFFORT_LEVEL=high`** (ver `app/teams/CLAUDE.md`). **Rollback web**: `AGENT_MODEL=claude-opus-4-7`.
- **Fable 5 (opt-in por usuario, 2026-06-10)**: `claude-fable-5` (modelo mais capaz, mais CARO + tokenizer ~30% mais tokens) e' exposto na UI (`chat.html`, var `pode_usar_fable5`) e aceito no backend (`chat.py` gate defense-in-depth → fallback Opus se nao-autorizado) SO' para user_ids em `AGENT_FABLE5_ALLOWED_USER_IDS` (CSV, default `"1"`). Helper: `feature_flags.is_fable5_allowed()`. Compativel sem mudar `client.py` (thinking adaptive/omit OK; sem `budget_tokens`/sampling; smart-router so' rebaixa `opus`, nao toca `fable`). Pre-req: CLI bundled >= 2.1.170.
- **SessionStore**: `PostgresSessionStore` source-of-truth (Fase B; tabela `claude_session_store`; flag `AGENT_SDK_SESSION_STORE_ENABLED` ON; flush `batched`|`eager` via `AGENT_SDK_SESSION_STORE_FLUSH`). Rollback: `ROLLBACK_SESSION_STORE.md`.
- **Thinking display**: toggle per-user via `Usuario.preferences['agent_thinking_display']` (default global `AGENT_THINKING_DISPLAY=omitted`).

Features SDK adotadas com impacto direto em `app/agente/` (detalhe — fluxo, gotchas, `arquivo:linha` — por versao no `SDK_CHANGELOG.md`):

| Feature | SDK | Resumo |
|---|---|---|
| `Task*` tools | 0.2.82+ | TodoWrite → `TaskCreate/Update/Get/List`; emit via `task_event` SSE; parser `client.py:_build_task_event` |
| Effort `xhigh` per-subagente | 0.1.74 | 8 subagentes Opus pesados marcados no frontmatter; `agent_loader.py` forward-compat (`_SDK_HAS_EFFORT_FIELD`) |
| `skills` option | 0.1.77 | deprecou `"Skill"` em allowed_tools; Nacom usa **deny-list** (`SKILLS_DELEGADAS_SUBAGENTE`), Lojas **allow-list**. CLI trunca descriptions a 16K chars (8% do ctx) → deny-list corta o principal a 25 skills (Solucao A+B; detalhe no `SDK_CHANGELOG.md` §0.1.77) |
| Refusal + erro HTTP observavel | 0.88.0+ / 0.1.76 | `stop_details` + `api_error_status` propagados no `done`; Sentry tags `anthropic_http_status` / `_5xx`; `APIStatusError.type` em `scanner/service.py` + `memory_consolidator.py` |
| Actionable errors | 0.1.77 | `ProcessError` carrega texto real do CLI ("Reached maximum number of turns") |

> **Historico completo (adocoes, breaking changes, bug fixes, features NAO adotadas — 0.1.49 → 0.2.101 + anthropic 0.85 → 0.109.1, com fluxos e arquitetura)**: `SDK_CHANGELOG.md`. Versoes tambem em `.claude/references/BEST_PRACTICES_2026.md` e `MCP_CAPABILITIES_2026.md` (manter os 3 sincronizados ao bumpar).

---

## Export critico: Teams

`app/teams/` importa de **6 sub-modulos**: permissions, models, SDK client, flags, session_persistence, pending_questions.

**Qualquer mudanca em permissions.py, models.py, client.py, feature_flags.py, session_persistence.py ou pending_questions.py DEVE ser testada no Teams bot.**
