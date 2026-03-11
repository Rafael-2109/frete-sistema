# Agente Services — Guia de Desenvolvimento

**LOC**: 5.8K | **Arquivos**: 12 | **Atualizado**: 11/03/2026

Hub de analise, otimizacao e aprendizado de sessoes em 3 camadas (P0 core, P1 UX, P2 analytics).

---

## Estrutura

```
app/agente/services/
  ├── pattern_analyzer.py        # 1,236 LOC — Patterns prescritivos + perfil + extracao (P1-3)
  ├── knowledge_graph_service.py #   936 LOC — KG 3 layers: regex/Voyage/Sonnet (T3-3)
  ├── insights_service.py        #   879 LOC — Dashboard admin: metricas + health_score (P2)
  ├── memory_consolidator.py     #   524 LOC — Consolidacao + tier frio (P0)
  ├── friction_analyzer.py       #   463 LOC — Deteccao de friccao heuristica (P2-4)
  ├── session_summarizer.py      #   438 LOC — Resumos M1 estruturados via Sonnet (P0-2)
  ├── intersession_briefing.py   #   394 LOC — Briefing entre sessoes, zero LLM (P0)
  ├── tool_skill_mapper.py       #   316 LOC — Mapeamento Tool → Categoria → Dominio (lookup)
  ├── recommendations_engine.py  #   221 LOC — Recomendacoes rule-based para dashboard
  ├── suggestion_generator.py    #   209 LOC — Sugestoes pos-resposta via Sonnet (P1-1)
  └── sentiment_detector.py      #   177 LOC — Deteccao LOCAL de frustracao, zero API (P1-2)
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

### pattern_analyzer: extracao pos-sessao salva como user_id=0
`extrair_conhecimento_sessao()` salva memorias empresa (user_id=0) — termos, cargos, regras, correcoes.
Roda em daemon thread. NUNCA bloquear o response path com extracao.
— FONTE: `pattern_analyzer.py:858-1102`

### memory_consolidator: arquivos protegidos
`user.xml` e `preferences.xml` sao IMUNES a consolidacao. Memorias `category='permanent'` e `importance >= 0.7` tambem.
— FONTE: `memory_consolidator.py:49-52,91,220`

### knowledge_graph: 3 layers com custos diferentes
| Layer | Metodo | Latencia | Custo |
|-------|--------|----------|-------|
| 1 | Regex (UF, pedido, CNPJ, valor) | ~2ms | zero |
| 2 | Voyage Semantic Search | ~300ms | ~$0.0001 |
| 3 | Sonnet piggyback (relacoes) | 0ms extra | zero (reutiliza contextual retrieval) |

`strip_xml_tags()` e exportada — usada por `memory_mcp_tool.py` e `routes.py`. Alterar assinatura quebra 3+ callers.
— FONTE: `knowledge_graph_service.py:2-7,81`

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

---

## Interdependencias

### Chamadores externos (quem chama services/)
| Caller | Services usados |
|--------|----------------|
| `routes.py` | sentiment, suggestions, summarizer, patterns (5 funcoes), friction, insights, KG (strip_xml) |
| `client.py` | intersession_briefing, KG (query_graph_memories) |
| `memory_mcp_tool.py` | consolidator (2 funcoes), KG (extract, remove, strip_xml) |

### Interdependencias internas
| Service | Depende de |
|---------|-----------|
| insights_service | friction_analyzer, recommendations_engine |
| pattern_analyzer | session_summarizer output (JSONB `AgentSession.summary`) |
| knowledge_graph_service | `app.embeddings` (product_search, entity_search) |
| memory_consolidator | `AgentMemory` model + tier frio |

### Padrao de logging
Cada service usa prefixo unico: `[SENTIMENT]`, `[SUGGESTIONS]`, `[SUMMARIZER]`, `[PATTERNS]`, `[KG]`, `[FRICTION]`, `[INSIGHTS]`, `[CONSOLIDATOR]`, `[BRIEFING]`.
