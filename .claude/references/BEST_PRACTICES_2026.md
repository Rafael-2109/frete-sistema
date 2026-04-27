# Best Practices Anthropic 2026 — Plano de Otimizacao (SDK features)

**Atualizado**: 27/04/2026

> **Escopo deste doc**: SDK features (prompt caching, structured outputs, pgvector, MCP servers, versoes).
> Para **prompt engineering conceitual Claude 4.6** (overtriggering, adaptive thinking, prefill deprecation, XML tags, pre-mortem, red team) ver [STUDY_PROMPT_ENGINEERING_2026.md](STUDY_PROMPT_ENGINEERING_2026.md) + [ROADMAP_PROMPT_ENGINEERING_2026.md](ROADMAP_PROMPT_ENGINEERING_2026.md).

---

## Status Atual

| Componente | Versao | Notas |
|-----------|--------|-------|
| `anthropic` SDK | **0.84.0** | Atualizado de 0.79.0. count_tokens, batches, cache_control disponiveis |
| `claude-agent-sdk` | **0.1.66** | CLI 2.1.119. 0.1.60: `list_subagents()`, `get_subagent_messages()`, `setting_sources=[]` fix, TRACEPARENT propagation. 0.1.62: top-level `skills=` param em ClaudeAgentOptions. 0.1.64: SessionStore protocol (6 metodos) + transcript mirroring via `--session-mirror` + `materialize_resume_session` + 9 helpers async store-backed + conformance harness 13 contratos + CLI 2.1.116. 0.1.65: `ThinkingConfig.display` (`--thinking-display`) override para Opus 4.7 default "omitted" + `ServerToolUseBlock`/`ServerToolResultBlock` parser fix + `fold_session_summary`/`import_session_to_store` helpers + bounded retry mirror append + UUID idempotency + CLI 2.1.118. 0.1.66: atual |
| `mcp` | 1.26.0+ | 7 servers, 35 tools |
| pgvector | **0.8.1** (confirmado prod) | iterative_scan SUPORTADO, halfvec disponivel |

---

## IMPLEMENTADO (Fase 1 — Quick Wins)

### 0.1 SDK anthropic 0.79.0 → 0.84.0
- **Arquivo**: `requirements.txt:64`
- **Beneficio**: count_tokens, batches, cache_control, Structured Outputs, bug fixes
- **OutputConfig**: DISPONIVEL — `OutputConfigParam` com `JSONOutputFormatParam` (json_schema)
- **parse()**: Aceita `output_format=PydanticModel` para Structured Outputs tipados
- **Risco**: ZERO — claude-agent-sdk NAO depende de anthropic (verificado)

### 0.2 Prompt Caching nas chamadas diretas
- **O que**: Separacao system/user em todos `messages.create()` com `cache_control: {"type": "ephemeral"}`
- **Arquivos modificados (10 chamadas, 6 arquivos)**:
  - `app/agente/services/session_summarizer.py` — SUMMARY_SYSTEM_PROMPT (1501 chars)
  - `app/agente/services/suggestion_generator.py` — SUGGESTION_SYSTEM_PROMPT (1427 chars)
  - `app/agente/services/pattern_analyzer.py` — PATTERN_SYSTEM_PROMPT (2077 chars) + KNOWLEDGE_EXTRACTION_SYSTEM_PROMPT (1995 chars)
  - `app/agente/services/memory_consolidator.py` — CONSOLIDATION_SYSTEM_PROMPT + VERIFICATION_SYSTEM_PROMPT (3 chamadas: consolidacao + verificacao + retry)
  - `app/agente/tools/memory_mcp_tool.py` — _CONTEXTUAL_SYSTEM_PROMPT (contexto embeddings)
  - `app/devolucao/services/ai_resolver_service.py` — DEPARA_SYSTEM_PROMPT (~4K chars, Sonnet, De-Para produto)
- **NAO refatorados** (baixo beneficio):
  - `ai_resolver_service.py` (3 chamadas Haiku): prompts < 2048 tokens (minimo Haiku)
  - `fatura_pdf_parser.py` (1 chamada): prompt dinamico sem parte estatica
  - `routes.py` (1 chamada Haiku): correcao one-off
  - `memory_agent.py` (2 chamadas Haiku): modulo DEPRECATED
- **Nota**: Minimo cacheavel = 1024 tokens (Sonnet), 2048 tokens (Haiku). Prompts menores beneficiam da separacao system/user (melhor instruction following) mas cache nao ativa.

### 0.3 Structured Outputs (Constrained Decoding)
- **O que**: `client.messages.parse(output_format=PydanticModel)` — constrained decoding garante JSON valido
- **Arquivo**: `app/devolucao/services/ai_resolver_service.py`
- **Modelos Pydantic criados (4)**:
  - `DeParaResponse` — resposta principal De-Para de produtos (Sonnet)
  - `TermosBuscaResponse` — extracao de termos ILIKE (Haiku)
  - `ObservacaoResponse` — extracao de observacoes NFD (Haiku)
  - `DeParaAnaliseCliente`, `DeParaOutraOpcao` — modelos auxiliares
- **Metodos refatorados (3)**:
  1. `resolver_produto()` — Sonnet, parse() com DeParaResponse + fallback create()
  2. `_extrair_termos_busca()` — Haiku, parse() com TermosBuscaResponse + fallback
  3. `extrair_observacao()` — Haiku, parse() com ObservacaoResponse + fallback
- **Fallback**: Cada metodo tenta parse() primeiro; se falhar, usa create() + _extrair_json()
- **Beneficio**: Elimina necessidade de _extrair_json() e _reparar_json() no caminho feliz

### 0.4 pgvector Iterative Scan
- **O que**: `SET LOCAL hnsw.iterative_scan = relaxed_order` antes de queries com WHERE
- **Arquivo**: `app/embeddings/service.py` — metodo `_enable_iterative_scan()`
- **Requisito**: pgvector 0.8.0+. Verifica versao automaticamente, cache de 5 min.
- **Degradacao**: Se pgvector < 0.8.0, SET falha silenciosamente (queries funcionam sem iterative_scan)
- **Metodos habilitados (6)**:
  1. `_search_pgvector_ssw` — quando `subdir_filter` presente
  2. `_search_pgvector_entities` — quando `entity_type != 'all'`
  3. `_search_pgvector_session_turns` — sempre (WHERE user_id)
  4. `_search_pgvector_memories` — sempre (WHERE user_id)
  5. `_search_pgvector_devolucao_reasons` — quando `motivo_filter` presente
  6. `_search_pgvector_routes` — quando `tipo` presente

---

## PROXIMOS PASSOS (Fase 2-4)

### Fase 2 — MCP Servers

#### Postgres MCP Pro — Configuracao Pronta
- **Repo**: github.com/crystaldba/postgres-mcp (2.3K stars, MIT)
- **Prerequisitos verificados** (2026-03-08):
  - `pg_stat_statements` 1.12 — **INSTALADA** no Render
  - `hypopg` — **NAO disponivel** (indices hipoteticos nao funcionarao)
  - pgvector 0.8.1 — compativel
  - Python 3.12.3 — compativel (req: 3.12+)
  - PostgreSQL 18, plano basic_4gb
- **Instalacao**: `uv pip install postgres-mcp`
- **Configuracao** (`~/.claude/settings.json` → `mcpServers`):
```json
"postgres-mcp": {
  "command": "uv",
  "args": ["run", "postgres-mcp", "--access-mode=restricted"],
  "env": {
    "DATABASE_URI": "postgresql://sistema_user:<SENHA>@<HOST>:5432/sistema_fretes"
  }
}
```
- **`--access-mode=restricted`**: Read-only (OBRIGATORIO para producao)
- **DATABASE_URI**: Copiar "External Connection String" do Render Dashboard
- **9 tools**: list_schemas, list_objects, get_object_details, execute_sql, explain_query, get_top_queries, analyze_workload_indexes, analyze_query_indexes, analyze_db_health
- **Overlap**: `execute_sql` sobrepoe Render MCP e text_to_sql. Manter ambos (postgres-mcp para DBA, custom para NL queries)
- **Dependencias**: `psycopg3` (coexiste com `psycopg2-binary` do projeto)
- **Versao**: 0.3.0 (PyPI), Python >= 3.12
- **Status**: [ ] Pendente — requer inserir credenciais manualmente

#### Mapbox MCP — Configuracao Pronta
- **Repo**: github.com/mapbox/mcp-server
- **Instalacao**: Via npx (nao requer install local)
- **Configuracao** (`~/.claude/settings.json` → `mcpServers`):
```json
"mapbox": {
  "command": "npx",
  "args": ["-y", "@mapbox/mcp-server"],
  "env": {
    "MAPBOX_ACCESS_TOKEN": "<TOKEN>"
  }
}
```
- **Conta**: Criar em mapbox.com → Dashboard → Access Tokens
- **Free tier**: 100K geocoding + 100K directions/mes
- **Tools offline (sem API)**: distance, point_in_polygon, bearing, midpoint, centroid, area, bounding_box, buffer, simplify
- **Tools com API**: matrix, directions, isochrone, search, reverse_geocode, optimization, map_matching, static_image
- **20 tools total** (9 API + 9 offline + 2 utility). Licenca BSD 3-Clause
- **Custo estimado**: $0/mes (uso agente ~6K req/mes, free tier = 100K cada API)
- **Valor alto**: matrix (benchmarking transportadoras), optimization (TSP para carga direta), directions (km real para cotacao)
- **Substitui parcialmente**: Google Maps API em `gps_service.py` (geocoding/reverse)
- **Alternativa hosted**: `https://mcp.mapbox.com/mcp` (HTTP, sem npx)
- **Status**: [ ] Pendente — requer criar conta e obter token

### Fase 3 — Features de API

#### Structured Outputs — IMPLEMENTADO (2026-03-08)
- Ver secao 0.3 acima
- [ ] **Batch API**: 50% desconto em workloads nao-interativos
  - Aplicacoes: reprocessamento embeddings, classificacao NFs, analise batch
  - JA disponivel: `client.messages.batches.create()`
- [ ] **Token Counting**: Budget enforcement preciso
  - JA disponivel: `client.messages.count_tokens()`
- [ ] **Session History SDK**: `list_sessions()`, `get_session_messages()` (v0.1.46+)

### Fase 4 — Otimizacoes (4h estimadas)
- [ ] **Runtime MCP Management**: `toggle_mcp_server()` em runtime (lazy-loading tools). Disponivel SDK 0.1.50+, requer ClaudeSDKClient
- [ ] **Context Usage Monitoring**: `get_context_usage()` (SDK 0.1.52+). Requer wiring 3-layer (client→routes→chat.js)
- [ ] **halfvec pgvector**: 50% storage de embeddings (migration destrutiva, testar recall)
- [ ] **HTTP Hooks**: POST JSON para Teams quando agente completa tarefa
- [x] **PreCompact Hook**: Salvar contexto antes de compaction (implementado `_pre_compact_hook`)

### Fase 5 — Memoria e Routing (implementado 2026-03-23)
- [x] **correction_count fix**: Gate broadened para PT-BR paths + keyword detection
- [x] **KG normalization**: 120→13 relation types canonicos, fallback 'regra'→'conceito' eliminado
- [x] **Tier 1.5 always-inject**: Perfis empresa/usuarios injetados para routing
- [x] **tools_used enriched**: `Skill:nome` e `Agent:tipo` em vez de generico
- [x] **importance_score fix**: empresa memories elegiveis para cold tier (0.7→0.5)
- [x] **R0c tightened**: Termos genericos de logistica nao sao mais salvos
- [ ] **Routing context**: Contexto de despacho com armadilhas + dominio por usuario
- [ ] **Resolution records**: `resolves_to` no KG para pesos de ambiguidade

---

## Features JA Disponiveis sem Upgrade Adicional

| Feature | Como Usar | Desde |
|---------|-----------|-------|
| Token Counting | `client.messages.count_tokens()` | 0.79.0 |
| Batch API | `client.messages.batches.create()` | 0.79.0 |
| parse() | `client.messages.parse()` (Pydantic) | 0.79.0 |
| cache_control | `system=[{"type":"text", "text":..., "cache_control":{"type":"ephemeral"}}]` | 0.79.0 |

---

## Economia Estimada

| Otimizacao | Economia | Status |
|-----------|----------|--------|
| Prompt Caching (system prompt + schemas) | 40-60% input tokens | **IMPLEMENTADO** |
| pgvector iterative_scan (recall) | Melhoria qualitativa | **IMPLEMENTADO** |
| Batch API | 50% em nao-interativos | Disponivel |
| Structured Outputs (menos retries) | 5-10% geral | **IMPLEMENTADO** |
| halfvec (storage) | 50% embeddings | Fase 4 |

---

## MCP Servers REJEITADOS

| Server | Motivo |
|--------|--------|
| GitHub MCP | `gh` CLI suficiente |
| Odoo MCP generico | `app/odoo/` custom (17.9K LOC) superior |
| Redis MCP | Valor marginal |
| Slack MCP | Time usa Teams |
| Sentry MCP | INTEGRADO desde 2026-03-11 (20 tools) |

---

## Claude 4.6 Behavioral Changes (adicionado 2026-04-12)

> Sumario rapido. Ref completa: [STUDY_PROMPT_ENGINEERING_2026.md](STUDY_PROMPT_ENGINEERING_2026.md)

Claude Opus 4.6 e Sonnet 4.6 tem mudancas comportamentais que afetam **como escrever prompts**, nao apenas features do SDK:

| Sintoma | Causa | Mitigacao | Ref |
|---------|-------|-----------|-----|
| **Overtrigger** de tools/skills | Mais responsivo a linguagem agressiva ("CRITICAL: You MUST") | Dial back para "Use X when..." em routing; manter "NEVER" apenas em safety invariants | STUDY insight 1, ROADMAP R1 |
| **Overengineering** | Modelo cria arquivos/abstracoes nao pedidos | Adicionar `<avoid_overengineering>` bloco no prompt | STUDY D6 |
| **Subagent overspawning** | Delega mesmo para tarefas simples | Adicionar `<when_subagents_warranted>` bloco | STUDY H5 |
| **Prefill deprecated** | 400 error em Mythos Preview | Migrar para Structured Outputs (Pydantic) | STUDY insight 2, ROADMAP R4 |
| **Thinking config** | `budget_tokens` deprecated | Trocar por `thinking: {type: "adaptive"}` + `effort` | STUDY insight 3, ROADMAP R6 |
| **Latencia alta default Sonnet 4.6** | `effort: high` e o default | Setar `effort: low` (chat) ou `medium` (tools) explicitamente | STUDY E1 |

**Ao auditar prompts existentes** (system_prompt, agents, skills): executar `grep -niE "(CRITICAL|MUST|NEVER|ALWAYS|OBRIGATORIO)"` e decidir por ocorrencia: manter (safety L1) ou substituir (style/routing). Ver [ROADMAP R1](ROADMAP_PROMPT_ENGINEERING_2026.md) para protocolo.

---

## PostgreSQL Producao — Extensoes (verificado 2026-03-08)

| Extensao | Versao | Uso |
|----------|--------|-----|
| `pg_stat_statements` | 1.12 | Queries lentas, workload analysis (postgres-mcp) |
| `vector` (pgvector) | 0.8.1 | Embeddings, iterative_scan, halfvec |
| `plpgsql` | 1.0 | Procedural language padrao |
| `hypopg` | **NAO instalada** | Indices hipoteticos (opcional postgres-mcp) |

PostgreSQL 18, plano basic_4gb, regiao Oregon, disco 5GB.
