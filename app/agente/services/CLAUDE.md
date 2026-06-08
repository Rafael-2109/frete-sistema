<!-- doc:meta
tipo: explanation
camada: L2
sot_de: —
hub: app/agente/CLAUDE.md
superseded_by: —
atualizado: 2026-06-08
-->
# Agente Services — Guia de Desenvolvimento

> **Papel:** guia dev dos services de inteligencia do Agente Web (analise, otimizacao e aprendizado de sessoes). Companheiro do guia do modulo: [`CLAUDE.md`](../CLAUDE.md). Abra antes de editar `app/agente/services/`.

**LOC**: ~13.8K | **Arquivos**: 23 | **Atualizado**: 2026-06-08

## Contexto

Hub de analise, otimizacao e aprendizado de sessoes em 3 camadas (P0 core, P1 UX, P2 analytics). Todos rodam best-effort (R1) sob feature flag (R2). O **protocolo de memoria** que estes services alimentam/consomem (ciclo de vida, decay, paths, criterios de qualidade) e canonico em `.claude/references/MEMORY_PROTOCOL.md`.

---

## Estrutura

```
app/agente/services/
  ├── _utils.py                       #    57 LOC — Helpers compartilhados (parse_llm_json_response)
  ├── pattern_analyzer.py             # 2,432 LOC — Patterns prescritivos + perfil + extracao (P1-3)
  ├── insights_service.py             # 1,897 LOC — Dashboard admin: metricas + health_score (P2)
  ├── knowledge_graph_service.py      # 1,160 LOC — KG 3 layers: regex/Voyage/Sonnet (T3-3)
  ├── memory_consolidator.py          #   736 LOC — Consolidacao + tier frio (P0)
  ├── metrics_dashboard_service.py    #   690 LOC — Dashboard telemetria subagent (Fase A1+A3)
  ├── improvement_suggester.py        #   602 LOC — Dialogo melhoria Agent SDK <-> Claude Code (D8)
  ├── eval_gate_service.py            #   568 LOC — Gate de avaliacao offline (A3 golden dataset)
  ├── directive_promotion_service.py  #   887 LOC — Promocao automatica de diretriz (A4 Distill→Deploy)
  ├── ontology_bootstrap.py           #   211 LOC — Bootstrap da ontologia (knowledge graph / ontology_query)
  ├── intersession_briefing.py        #   576 LOC — Briefing entre sessoes, zero LLM (P0)
  ├── artifact_service.py             #   491 LOC — Rate limit + spec validation + S3 upload (artifacts)
  ├── friction_analyzer.py            #   490 LOC — Deteccao de friccao heuristica (P2-4)
  ├── session_summarizer.py           #   480 LOC — Resumos M1 estruturados via Sonnet (P0-2)
  ├── sql_evaluator_falses_service.py #   387 LOC — Detector de falsos negativos no SQL evaluator
  ├── tool_skill_mapper.py            #   383 LOC — Mapeamento Tool → Categoria → Dominio (lookup)
  ├── recommendations_engine.py       #   279 LOC — Recomendacoes rule-based para dashboard
  ├── suggestion_generator.py         #   223 LOC — Sugestoes pos-resposta via Sonnet (P1-1)
  ├── sentiment_detector.py           #   260 LOC — Deteccao LOCAL de frustracao, zero API (P1-2)
  ├── teams_observability_service.py  #   346 LOC — KPIs canal Teams (teams_tasks + agent_step), read-only (F2)
  ├── skill_effectiveness_service.py  # Avaliador de efetividade de skill pos-sessao (Fase 1): janela+funil estagio0/Haiku/Sonnet+aplicacao+idempotencia
  └── approval_inbox_service.py       # Inbox de Aprovacao: AgentMemory shadow + ImprovementDialogue proposed (conserta directive_promotion shadow->ativa)
```

## Regras Criticas

### R1: Best-effort — NUNCA propagar excecoes
TODOS os services rodam em background ou inline no stream SSE. Excecao propagada = stream morto.
**Padrao**: `try/except Exception: logger.error(...)` — logado, NUNCA re-raised.

### R2: Feature flags — TODO service DEVE ter flag
Cada service e controlado por flag em `config/feature_flags.py`. Codigo que chama service DEVE verificar flag ANTES.
**NUNCA** chamar service sem `if USE_X:` — causa custo API desnecessario quando desativado.

### R3: Truncamento — SEMPRE truncar conteudo antes de enviar ao LLM
| Service | Limite | Fonte |
|---------|--------|-------|
| session_summarizer | 3K chars/msg | `session_summarizer.py:121` |
| suggestion_generator | 1K user + MAX_RESPONSE_CHARS assistant | `suggestion_generator.py:97-107` |
| pattern_analyzer (analyze) | 500 chars/msg, 10 msgs/sessao | `pattern_analyzer.py:174-175` |
| pattern_analyzer (extract) | 3K chars/msg, cap 40K total | `pattern_analyzer.py:873-886` |
| knowledge_graph | 300 chars busca semantica | `knowledge_graph_service.py:176` |

Sem truncamento: token explosion → custo 10x, latencia 30s+, possivel timeout.

### R4: XML escape — SEMPRE escapar antes de salvar memorias
Memorias armazenam XML. Conteudo com `<>&"'` corrompe parsing.
`_xml_escape()` definida em `pattern_analyzer.py:787` e `session_summarizer.py:428`.

### R5: Prompt caching Sonnet — `cache_control: ephemeral`
Services que chamam Sonnet DEVEM incluir `cache_control: {"type": "ephemeral"}` no system message.
Economia: 50-90% tokens input. Sem cache = custo duplicado em chamadas consecutivas.

---

## Gotchas

### pattern_analyzer: prescritivo vs descritivo
Output DEVE ser PRESCRITIVO ("Quando cliente X pedir Y, faca Z") — NAO descritivo ("Usuario frequentemente pede Y").
Descritivo = padrao inutil que nao muda comportamento do agente. ERRAR AQUI corrompe aprendizado.
— FONTE: `pattern_analyzer.py:4,40,88`

### pattern_analyzer: extracao pos-sessao PESSOAL (S1 — 2026-04-07)
`extrair_insights_pessoais_sessao()` salva memorias PESSOAIS (user_id do usuario).
Complementar a extracao empresa — extrai correcoes, preferencias, expertise, contexto.
4 tipos: `correcao` (→ /corrections/), `preferencia` (→ preferences.xml append),
`expertise` (→ /learned/expertise_*.xml), `contexto` (→ /context/work_context.xml).
Dedup via `_check_memory_duplicate()` de `memory_mcp_tool.py`.
Roda em daemon thread, mesmo trigger que empresa (min 3 msgs).
Flag: `USE_POST_SESSION_PERSONAL_EXTRACTION` (= `AGENT_POST_SESSION_PERSONAL_EXTRACTION` env).
Custo: ~$0.003 por execucao (Sonnet).
Motivacao: R0 auto-save depende do modelo chamar save_memory — Marcus teve 0 calls em 9 sessoes.
— FONTE: `pattern_analyzer.py:extrair_insights_pessoais_sessao()`

### pattern_analyzer: thresholds adaptativos para profile (S2 — 2026-04-07)
`should_generate_profile()` agora tem 2 criterios adaptativos ANTES do threshold fixo:
1. Sessao longa (>= `PROFILE_LONG_SESSION_THRESHOLD`, default 20 msgs) → trigger
2. Sessao cara (>= `PROFILE_COST_THRESHOLD`, default $5.00) → trigger
Resolve: usuarios low-frequency com sessoes densas ficavam com user.xml stale por semanas.
— FONTE: `pattern_analyzer.py:should_generate_profile()`

### pattern_analyzer: extracao pos-sessao EMPRESA (Taxonomia 5 niveis)
`extrair_conhecimento_sessao()` salva memorias empresa (user_id=0) com 3 tipos operacionais.
Taxonomia de 5 niveis: 1-2 (lookup/composicao) = NAO memorizar, 3-5 (diagnostico/armadilha/heuristica) = memorizar.
4 criterios formais: bifurca? perdeu tempo? implicito? transferivel? (min 2 verdadeiros).
Briefing da empresa injetado via `config/empresa_briefing.md` (cache module-level).
Titulos existentes injetados no user message para reutilizacao/enriquecimento.
Busca semantica pre-save via `_find_similar_empresa_memory()` (dedup_embedding, threshold 0.80).
JSON: `titulo`, `tipo` (protocolo|armadilha|heuristica), `nivel` (3-5), `criterios_atendidos`, `descricao`, `prescricao`.
Paths: `/memories/empresa/{protocolos|armadilhas|heuristicas}/{dominio}/{slug-do-titulo}.xml`
Backward-compatible com formato legado (term_definitions, business_rules, corrections).
Roda em daemon thread. NUNCA bloquear o response path com extracao.
— FONTE: `pattern_analyzer.py:835-1550`

### memory_consolidator: arquivos protegidos
`user.xml` e `preferences.xml` sao IMUNES a consolidacao. Memorias `category='permanent'` e `importance >= 0.7` tambem.
— FONTE: `memory_consolidator.py:49-52,91,220`

### knowledge_graph: 3 layers com custos diferentes
| Layer | Metodo | Latencia | Custo |
|-------|--------|----------|-------|
| 1 | Regex (UF, pedido, CNPJ, valor) | ~2ms | zero |
| 2 | Voyage Semantic Search | ~300ms | ~$0.0001 |
| 3 | Sonnet piggyback (relacoes) | 0ms extra | zero (reutiliza contextual retrieval) |

`strip_xml_tags()` e usada apenas INTERNAMENTE no `knowledge_graph_service.py` (via `normalize_for_comparison()` + extracao de entidades). Alterar assinatura afeta dedup/comparacao de memorias do KG.
— FONTE: `knowledge_graph_service.py` (definicao + callers internos)

### session_summarizer: campo `acoes_usuario`
= acoes do USUARIO (lancou, consultou, cancelou), NAO do agente. Confundir = resumo sem valor.
— FONTE: `session_summarizer.py:79`

### sentiment_detector: threshold conservador
`score >= 3` = frustracao detectada. Preferir falso negativo sobre falso positivo (tom inadequado injetado).
— FONTE: `sentiment_detector.py:138-140`

### friction_analyzer: prefix grouping O(n log n)
Clustering por prefixo usa sort + varredura linear. NAO alterar para comparacao par-a-par O(n²).
— FONTE: `friction_analyzer.py:210-248`

### insights_service: composicao inline
Chama `friction_analyzer` + `recommendations_engine` internamente. Alteracao em qualquer um afeta dashboard admin.

### improvement_suggester: dialogo versionado D8 (batch + real-time)
Loop Agent SDK <-> Claude Code. Sonnet analisa batch de sessoes recentes (8h) e gera 0-5 sugestoes cross-sessao.
Tambem avalia respostas pendentes do Claude Code contra sessoes recentes.
6 categorias: skill_suggestion, instruction_request, prompt_feedback, gotcha_report, memory_feedback, **skill_bug** (nova).
Max 3 versoes por suggestion_key (spiral prevention). Flag: `USE_IMPROVEMENT_DIALOGUE` (= `AGENT_IMPROVEMENT_DIALOGUE` env).
Tabela: `agent_improvement_dialogue`. Custo: ~$0.005/batch.
**Dois caminhos de entrada:**
- Batch: APScheduler modulo 25 (07:00 e 10:00) — captura sessoes abandonadas
- Real-time: MCP tool `register_improvement` (memory server) — agente registra durante conversa (R9 system_prompt)
POST endpoint: `/api/improvement-dialogue`. GET: `/api/improvement-dialogue/pending`.
— FONTE: `improvement_suggester.py:1-25`, `sincronizacao_incremental_definitiva.py` (step 25), `memory_mcp_tool.py`

### skill_effectiveness_service + approval_inbox_service (Fase 1 — 2026-06-07)
Avaliador pos-sessao de efetividade de skill (detalhe completo em `app/agente/CLAUDE.md`).
Funil estagio0 custo-zero (sentiment+regex+Bash) -> Haiku -> Sonnet sobre a janela ancorada
na invocacao. 3 ramos: `lembrete_usuario` (AgentMemory mandatory, AUTO) / `lembrete_todos`
(shadow -> Inbox) / `ajuste_codigo` (`AgentImprovementDialogue` proposed).
**Separacao de competencias (inviolavel)**: NUNCA prescreve solucao no `ajuste_codigo`
(so problema + evidencia; Claude Code resolve) — vale tb p/ `improvement_suggester` (D8).
PII via `pii_masker.mask_pii` antes do LLM e antes de persistir `evidencia_json`.
`approval_inbox_service` conserta o gap do `directive_promotion` (shadow sem UI): aba
"Pendentes de Aprovacao" em `/agente/memorias` faz `shadow -> ativa`.
**Teams web-only**: `build_skill_windows` casa `"Skill:<nome>"` (so a web grava — `chat.py:866`).
Flag `AGENT_SKILL_EVAL` (R2). — FONTE: `skill_effectiveness_service.py`, `approval_inbox_service.py`

---

## Interdependencias

### Chamadores externos (quem chama services/)
| Caller | Services usados |
|--------|----------------|
| `routes/` (chat, _helpers, insights, admin_learning) | sentiment, suggestions, summarizer, patterns (5 funcoes), friction, insights |
| `sincronizacao_incremental_definitiva.py` | improvement_suggester (batch, modulo 25) |
| `client.py` | intersession_briefing, KG (query_graph_memories) |
| `memory_mcp_tool.py` | consolidator (2 funcoes), KG (extract, remove) |

### Interdependencias internas
| Service | Depende de |
|---------|-----------|
| insights_service | friction_analyzer, recommendations_engine |
| pattern_analyzer | session_summarizer output (JSONB `AgentSession.summary`) |
| knowledge_graph_service | `app.embeddings` (product_search, entity_search) |
| memory_consolidator | `AgentMemory` model + tier frio |
| improvement_suggester | `AgentImprovementDialogue` model |

### Padrao de logging
Cada service usa prefixo unico: `[SENTIMENT]`, `[SUGGESTIONS]`, `[SUMMARIZER]`, `[PATTERNS]`, `[KG]`, `[FRICTION]`, `[INSIGHTS]`, `[CONSOLIDATOR]`, `[BRIEFING]`, `[IMPROVEMENT]`.
