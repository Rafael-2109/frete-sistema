│ Plan to implement                                                                      │
│                                                                                        │
│ Avaliacao Critica do Sistema de Memoria + Plano de Evolucao                            │
│                                                                                        │
│ Data: 2026-03-02                                                                       │
│ Escopo: Agente Logistico Web — sistema de memoria persistente, embeddings e RAG        │
│ Metodo: Analise de codigo + pesquisa cientifica (20+ artigos) + frameworks de mercado  │
│ (8+) + docs Context7 (6 libs)                                                          │
│                                                                                        │
│ ---                                                                                    │
│ 1. CONTEXTO — Por que esta avaliacao                                                   │
│                                                                                        │
│ O agente logistico web opera em dominio critico (frete, estoque, financeiro) onde      │
│ aprendizado continuo e a diferenca entre um assistente util e um que repete erros. O   │
│ sistema atual tem 3 camadas de memoria (hook injection + MCP tools + consolidacao      │
│ Haiku), embeddings Voyage AI + pgvector, e services auxiliares (pattern analyzer,      │
│ session summarizer). Esta avaliacao identifica gaps e propoe evolucoes baseadas no     │
│ estado da arte.                                                                        │
│                                                                                        │
│ ---                                                                                    │
│ 2. DIAGNOSTICO DO SISTEMA ATUAL                                                        │
│                                                                                        │
│ 2.1 O que funciona bem                                                                 │
│                                                                                        │
│ ┌────────────────────────────────┬───────────────────────────────────────────┬──────┐  │
│ │           Componente           │                 Avaliacao                 │ Nota │  │
│ ├────────────────────────────────┼───────────────────────────────────────────┼──────┤  │
│ │ Hook de injecao (Tier 1+2)     │ Solido. Protegidas + semantica + fallback │ 8/10 │  │
│ │                                │  recencia                                 │      │  │
│ ├────────────────────────────────┼───────────────────────────────────────────┼──────┤  │
│ │ MCP tools de memoria           │ Completo. 6 tools CRUD + sanitizacao      │ 8/10 │  │
│ │                                │ anti-injection                            │      │  │
│ ├────────────────────────────────┼───────────────────────────────────────────┼──────┤  │
│ │ Embeddings Voyage AI           │ Boa escolha. voyage-4-lite                │ 7/10 │  │
│ │                                │ custo/beneficio bom                       │      │  │
│ ├────────────────────────────────┼───────────────────────────────────────────┼──────┤  │
│ │ pgvector + cosine              │ Funcional. Fallback Python quando         │ 7/10 │  │
│ │                                │ indisponivel                              │      │  │
│ ├────────────────────────────────┼───────────────────────────────────────────┼──────┤  │
│ │ Versionamento                  │ Excelente. Audit trail completo           │ 9/10 │  │
│ │ (AgentMemoryVersion)           │                                           │      │  │
│ ├────────────────────────────────┼───────────────────────────────────────────┼──────┤  │
│ │ Feature flags granulares       │ Muito bom. Kill switches para tudo        │ 9/10 │  │
│ ├────────────────────────────────┼───────────────────────────────────────────┼──────┤  │
│ │ Consolidacao Haiku             │ Funcional mas limitada (ver gaps)         │ 6/10 │  │
│ └────────────────────────────────┴───────────────────────────────────────────┴──────┘  │
│                                                                                        │
│ 2.2 GAPS CRITICOS (Impacto direto na qualidade)                                        │
│                                                                                        │
│ GAP-1: Sem Importance Scoring — todas as memorias tem peso igual                       │
│                                                                                        │
│ - Problema: Uma memoria "usuario prefere modo escuro" tem o mesmo peso que             │
│ "transportadora X tem historico de atrasos no AM". O retrieval semantico ordena por    │
│ similaridade ao prompt, mas ignora importancia intrinseca.                             │
│ - Impacto: Memorias triviais podem deslocar memorias criticas no budget de 4000 chars. │
│ - Referencia: Stanford Generative Agents (2023) — formula score = a*recency +          │
│ b*importance + c*relevance com decay 0.995/hora. Simples e comprovada.                 │
│                                                                                        │
│ GAP-2: Sem Memory Decay — memorias acumulam sem degradar                               │
│                                                                                        │
│ - Problema: Memorias antigas nunca perdem relevancia. "Cotacao de frete para AM custou │
│  R$ 12.500" de 6 meses atras compete igualmente com uma de ontem.                      │
│ - Impacto: Context pollution. O budget de 4000 chars fica saturado com informacoes     │
│ obsoletas.                                                                             │
│ - Referencia: "Intelligent Decay" (2025, arXiv:2509.25250) — esquecimento ativo        │
│ baseado em relevancia + recencia.                                                      │
│                                                                                        │
│ GAP-3: Embedding inline de turns DESLIGADO por default                                 │
│                                                                                        │
│ - Problema: USE_SESSION_SEMANTIC_SEARCH = false em feature_flags.py. Novos turns NAO   │
│ sao embedados automaticamente. A busca semantica em sessoes so funciona se o batch     │
│ indexer foi executado manualmente.                                                     │
│ - Impacto: O agente nao consegue buscar sessoes recentes semanticamente — depende de   │
│ ILIKE textual (fragil) ou execucao manual do indexer.                                  │
│ - Desconexao: embeddings/config.py:SESSION_SEMANTIC_SEARCH = true (busca habilitada),  │
│ mas feature_flags.py:USE_SESSION_SEMANTIC_SEARCH = false (escrita desabilitada). Flags │
│  em arquivos diferentes com nomes similares e semantica oposta.                        │
│                                                                                        │
│ GAP-4: Embeddings orfaos nunca sao limpos                                              │
│                                                                                        │
│ - Problema: Deletar uma memoria em agent_memories NAO remove o embedding em            │
│ agent_memory_embeddings. O memory_id e FK "logica" (sem constraint real no banco). Nao │
│  existe garbage collection.                                                            │
│ - Impacto: Embeddings stale podem ser retornados na busca semantica, apontando para    │
│ memorias que nao existem mais. Resultados fantasma.                                    │
│                                                                                        │
│ GAP-5: Consolidacao perde nuances                                                      │
│                                                                                        │
│ - Problema: Haiku com max_tokens=1200 e instrucao "maximo 800 caracteres" comprime N   │
│ memorias detalhadas em 1 resumo generico. Informacoes nuancadas (excecoes, condicoes   │
│ especificas) podem ser perdidas.                                                       │
│ - Impacto: Apos consolidacao, o agente pode perder detalhes como "transportadora Y so  │
│ atrasa em entregas para zona rural de MG" (consolidado como "Y pode atrasar").         │
│ - Referencia: LangMem (LangChain) — consolidacao com verificacao de fatos preservados  │
│ pos-merge.                                                                             │
│                                                                                        │
│ GAP-6: Sem Reflection/Learning-from-errors                                             │
│                                                                                        │
│ - Problema: Quando o agente erra (cotacao errada, rota subotima, dado incorreto) e o   │
│ usuario corrige, nao existe mecanismo automatico para capturar essa correcao como      │
│ aprendizado.                                                                           │
│ - Impacto: O agente repete os mesmos erros. Depende do modelo decidir autonomamente    │
│ chamar save_memory (inconsistente).                                                    │
│ - Referencia: Reflexion (2023) + Dual-Loop Metacognition (2025) — banco de reflexoes   │
│ pos-erro.                                                                              │
│                                                                                        │
│ 2.3 GAPS MODERADOS (Otimizacao)                                                        │
│                                                                                        │
│ GAP-7: pgvector sem HNSW index                                                         │
│                                                                                        │
│ - Problema: Busca vetorial esta usando sequential scan (sem indice HNSW ou IVFFlat     │
│ criado). Funcional para volumes baixos, mas degrada com escala.                        │
│ - Impacto: Latencia de busca cresce linearmente com o numero de embeddings.            │
│ - Referencia: pgvector docs — HNSW com m=16, ef_construction=64 e padrao recomendado.  │
│                                                                                        │
│ GAP-8: Reranking desabilitado                                                          │
│                                                                                        │
│ - Problema: Pipeline embed -> retrieve sem reranking. Voyage rerank-2.5-lite esta      │
│ configurado mas desabilitado (RERANKING_ENABLED=false).                                │
│ - Impacto: Top-K pode incluir resultados com alta similaridade vetorial mas baixa      │
│ relevancia semantica real. Cross-encoder (reranker) resolveria.                        │
│ - Trade-off: +~2s latencia, +~$0.01/100 docs. Aceitavel para busca de memorias (nao    │
│ real-time).                                                                            │
│                                                                                        │
│ GAP-9: Truncamento fixo de 4000 chars sem priorizacao                                  │
│                                                                                        │
│ - Problema: _load_user_memories_for_context() trunca em 4000 chars com result[:4000].  │
│ Corta no meio de uma memoria se o buffer estourar.                                     │
│ - Impacto: A ultima memoria injetada pode ficar truncada no meio de uma frase,         │
│ perdendo informacao critica.                                                           │
│                                                                                        │
│ GAP-10: Context budget nao adaptativo                                                  │
│                                                                                        │
│ - Problema: Budget fixo de 4000 chars (~1000 tokens) independente do modelo (Sonnet vs │
│  Opus), tamanho do prompt, ou complexidade da query.                                   │
│ - Impacto: Com Opus (200K context), 1000 tokens e desperdicio. Com queries simples,    │
│ memorias desnecessarias consomem budget.                                               │
│ - Referencia: Adaptive RAG (LangGraph) — ajustar retrieval por complexidade da query.  │
│                                                                                        │
│ GAP-11: Pattern analyzer nao usa embeddings                                            │
│                                                                                        │
│ - Problema: pattern_analyzer.py analisa sessoes via texto bruto (Haiku). Poderia       │
│ pre-filtrar sessoes relevantes usando embeddings antes de enviar ao LLM.               │
│ - Impacto: Custo desnecessario (processa sessoes irrelevantes) e resultados menos      │
│ focados.                                                                               │
│                                                                                        │
│ GAP-12: Sem metricas de qualidade de memoria                                           │
│                                                                                        │
│ - Problema: Nao existe medicao de: recall de memorias, precision dos resultados        │
│ semanticos, taxa de uso das memorias injetadas, feedback do usuario sobre utilidade.   │
│ - Impacto: Impossivel saber se o sistema esta melhorando ou degradando. Ajustes sao no │
│  escuro.                                                                               │
│ - Referencia: MemoryAgentBench (ICLR 2026) — 4 metricas: Accurate Retrieval, Test-Time │
│  Learning, Long-Range Understanding, Conflict Resolution.                              │
│                                                                                        │
│ ---                                                                                    │
│ 3. RECOMENDACOES — Roadmap priorizado                                                  │
│                                                                                        │
│ Tier 1: Quick Wins (1-2 dias cada, alto impacto)                                       │
│                                                                                        │
│ QW-1: Memory Importance Scoring + Decay                                                │
│                                                                                        │
│ O que: Adicionar campos importance_score (float 0-1) e last_accessed_at (timestamp) a  │
│ agent_memories. Calcular score composto no retrieval: final_score = 0.3 *              │
│ recency_decay + 0.3 * importance + 0.4 * cosine_similarity.                            │
│                                                                                        │
│ Arquivos:                                                                              │
│ - scripts/migrations/add_importance_score_memories.py + .sql — DDL                     │
│ - app/agente/tools/memory_mcp_tool.py — atualizar last_accessed_at quando memoria e    │
│ lida/injetada                                                                          │
│ - app/agente/sdk/client.py:_load_user_memories_for_context() — usar score composto     │
│ para ordenar                                                                           │
│ - app/embeddings/memory_search.py — incorporar importance no ranking                   │
│                                                                                        │
│ Importance scoring: Heuristico simples (sem chamada LLM):                              │
│ - Menciona entidade de negocio (cliente, transportadora, rota) → +0.3                  │
│ - Contem valor monetario → +0.2                                                        │
│ - Contem correcao/erro → +0.3                                                          │
│ - Path /memories/corrections/* → +0.2                                                  │
│ - Path /memories/learned/* → +0.1                                                      │
│ - Default: 0.5                                                                         │
│                                                                                        │
│ Recency decay: decay = 0.995 ^ (horas_desde_ultimo_acesso). Memoria acessada ha 1      │
│ semana: 0.995^168 = 0.43. Ha 1 mes: 0.995^720 = 0.03.                                  │
│                                                                                        │
│ Complexidade: BAIXA | Impacto: ALTO                                                    │
│                                                                                        │
│ QW-2: Garbage Collection de Embeddings Orfaos                                          │
│                                                                                        │
│ O que: Ao deletar memoria, deletar embedding correspondente. Adicionar job periodico   │
│ para limpar orfaos.                                                                    │
│                                                                                        │
│ Arquivos:                                                                              │
│ - app/agente/tools/memory_mcp_tool.py:delete_memory() — adicionar DELETE FROM          │
│ agent_memory_embeddings WHERE memory_id = ?                                            │
│ - scripts/migrations/gc_orphan_embeddings.py — one-time cleanup                        │
│                                                                                        │
│ Complexidade: MUITO BAIXA | Impacto: MEDIO                                             │
│                                                                                        │
│ QW-3: Ativar Embedding Inline de Turns + Resolver Desconexao de Flags                  │
│                                                                                        │
│ O que: Mudar USE_SESSION_SEMANTIC_SEARCH default para true. Documentar claramente a    │
│ diferenca entre as duas flags.                                                         │
│                                                                                        │
│ Arquivos:                                                                              │
│ - app/agente/config/feature_flags.py:159 — mudar default para "true"                   │
│ - Renomear para clareza: USE_SESSION_TURN_EMBEDDING (escrita) vs                       │
│ SESSION_SEMANTIC_SEARCH (leitura)                                                      │
│                                                                                        │
│ Complexidade: MUITO BAIXA | Impacto: ALTO (habilita busca semantica real-time)         │
│                                                                                        │
│ QW-4: Truncamento inteligente em vez de corte bruto                                    │
│                                                                                        │
│ O que: Em vez de result[:4000], truncar por memoria completa. Se a proxima memoria nao │
│  cabe, parar (nao cortar no meio).                                                     │
│                                                                                        │
│ Arquivo: app/agente/sdk/client.py:181-182                                              │
│                                                                                        │
│ Logica:                                                                                │
│ # Em vez de: result = result[:4000]                                                    │
│ # Fazer: acumular memorias ate budget, parar quando nao couber                         │
│ budget = 4000                                                                          │
│ current = 0                                                                            │
│ selected = []                                                                          │
│ for mem in all_memories:                                                               │
│     mem_text = format_memory(mem)                                                      │
│     if current + len(mem_text) > budget:                                               │
│         break                                                                          │
│     selected.append(mem_text)                                                          │
│     current += len(mem_text)                                                           │
│                                                                                        │
│ Complexidade: MUITO BAIXA | Impacto: MEDIO                                             │
│                                                                                        │
│ Tier 2: Melhorias Estruturais (3-5 dias cada)                                          │
│                                                                                        │
│ T2-1: Reflection Bank — Aprendizado com Erros                                          │
│                                                                                        │
│ O que: Detectar quando usuario corrige o agente (padroes: "nao, o correto e...",       │
│ "errado", "na verdade...") e salvar automaticamente em /memories/corrections/ com      │
│ contexto.                                                                              │
│                                                                                        │
│ Implementacao:                                                                         │
│ 1. Adicionar deteccao de correcao no _user_prompt_submit_hook (regex simples)          │
│ 2. Quando detectado: salvar em /memories/corrections/{timestamp}.xml com: erro,        │
│ correcao, contexto                                                                     │
│ 3. Opcional: instruir o modelo via system prompt a usar save_memory proativamente apos │
│  ser corrigido                                                                         │
│                                                                                        │
│ Arquivos:                                                                              │
│ - app/agente/sdk/client.py — deteccao no hook                                          │
│ - app/agente/prompts/system_prompt.md — instrucao para auto-correcao                   │
│                                                                                        │
│ Referencia: Reflexion (Shinn et al., 2023) + Dual-Loop Metacognition (2025)            │
│ Complexidade: MEDIA | Impacto: ALTO                                                    │
│                                                                                        │
│ T2-2: Context Budget Adaptativo                                                        │
│                                                                                        │
│ O que: Ajustar budget de memoria baseado em: modelo usado (Opus=8K, Sonnet=4K,         │
│ Haiku=2K), tamanho do prompt, complexidade estimada.                                   │
│                                                                                        │
│ Logica:                                                                                │
│ base_budget = {"opus": 8000, "sonnet": 4000, "haiku": 2000}                            │
│ prompt_length_factor = max(0.5, 1 - len(prompt) / 10000)                               │
│ budget = int(base_budget[model] * prompt_length_factor)                                │
│                                                                                        │
│ Arquivo: app/agente/sdk/client.py:_load_user_memories_for_context()                    │
│                                                                                        │
│ Complexidade: BAIXA | Impacto: MEDIO                                                   │
│                                                                                        │
│ T2-3: HNSW Index para pgvector                                                         │
│                                                                                        │
│ O que: Criar indices HNSW nas tabelas de embeddings. Configurar ef_search para         │
│ queries.                                                                               │
│                                                                                        │
│ Migration:                                                                             │
│ CREATE INDEX CONCURRENTLY idx_memory_emb_hnsw                                          │
│ ON agent_memory_embeddings                                                             │
│ USING hnsw (embedding vector_cosine_ops)                                               │
│ WITH (m = 16, ef_construction = 64);                                                   │
│                                                                                        │
│ CREATE INDEX CONCURRENTLY idx_session_emb_hnsw                                         │
│ ON session_turn_embeddings                                                             │
│ USING hnsw (embedding vector_cosine_ops)                                               │
│ WITH (m = 16, ef_construction = 64);                                                   │
│                                                                                        │
│ Arquivo: scripts/migrations/add_hnsw_indexes_embeddings.py + .sql                      │
│                                                                                        │
│ Complexidade: BAIXA | Impacto: MEDIO (performance, nao qualidade)                      │
│                                                                                        │
│ T2-4: Consolidacao com Verificacao de Preservacao                                      │
│                                                                                        │
│ O que: Apos consolidar, verificar que todos os fatos originais estao presentes no      │
│ resumo. Usar Haiku para cross-check.                                                   │
│                                                                                        │
│ Implementacao: Pos-consolidacao, chamar Haiku com prompt: "Compare a lista original de │
│  fatos com o resumo. Liste fatos PERDIDOS." Se algum fato perdido, re-consolidar com   │
│ instrucao mais explicita.                                                              │
│                                                                                        │
│ Arquivo: app/agente/services/memory_consolidator.py:_consolidate_group()               │
│                                                                                        │
│ Custo: +$0.001 por consolidacao (double-check Haiku)                                   │
│ Complexidade: MEDIA | Impacto: MEDIO                                                   │
│                                                                                        │
│ T2-5: Metricas de Qualidade de Memoria                                                 │
│                                                                                        │
│ O que: Instrumentar o sistema para medir:                                              │
│ 1. Injection rate: % de turns que recebem memorias semanticas vs fallback              │
│ 2. Memory utilization: % de memorias que sao efetivamente injetadas (vs nunca          │
│ acessadas)                                                                             │
│ 3. Correction frequency: Frequencia de correcoes do usuario apos injecao de memoria    │
│ 4. Decay distribution: Distribuicao de idades das memorias ativas                      │
│                                                                                        │
│ Implementacao: Logs estruturados (ja existem parcialmente em [MEMORY_INJECT]).         │
│ Adicionar metricas no dashboard de Insights.                                           │
│                                                                                        │
│ Arquivos:                                                                              │
│ - app/agente/sdk/client.py — adicionar campos ao log                                   │
│ - app/agente/routes/insights_routes.py — nova secao de metricas de memoria             │
│                                                                                        │
│ Complexidade: MEDIA | Impacto: ALTO (observabilidade)                                  │
│                                                                                        │
│ Tier 3: Evolucoes Avancadas (1-2 semanas cada, avaliar ROI)                            │
│                                                                                        │
│ T3-1: Contextual Retrieval (Anthropic) para Chunks de Memoria                          │
│                                                                                        │
│ O que: Ao embedar uma memoria, gerar contexto breve (1-2 frases) que situa a memoria   │
│ no contexto geral do usuario. Embedar contexto + memoria em vez de so memoria.         │
│                                                                                        │
│ Referencia: Anthropic Contextual Retrieval — reduz erros de retrieval em ate 67%.      │
│ Aplicacao: Memorias curtas como "usar modo escuro" perdem significado isoladamente.    │
│ Com contexto: "Preferencia de interface do usuario Rafael: usar modo escuro".          │
│                                                                                        │
│ Trade-off: Requer 1 chamada Haiku por memoria no momento do save (~$0.0003). Para ~50  │
│ memorias/usuario, custo total < $0.02.                                                 │
│                                                                                        │
│ Complexidade: MEDIA | Impacto: ALTO                                                    │
│                                                                                        │
│ T3-2: Habilitar Reranking Seletivo                                                     │
│                                                                                        │
│ O que: Ativar reranking apenas para buscas de memoria (nao sessoes), onde precisao e   │
│ mais importante que latencia.                                                          │
│                                                                                        │
│ Implementacao: Adicionar flag MEMORY_RERANKING_ENABLED (separada de RERANKING_ENABLED  │
│ global). No memory_search.py, apos busca vetorial top-20, rerankar para top-5 usando   │
│ rerank-2.5-lite.                                                                       │
│                                                                                        │
│ Trade-off: +1-2s latencia na injecao de memorias. Aceitavel pois ocorre antes do       │
│ stream iniciar.                                                                        │
│                                                                                        │
│ Complexidade: BAIXA (infraestrutura ja existe) | Impacto: MEDIO                        │
│                                                                                        │
│ T3-3: Knowledge Graph Simplificado (sem Neo4j)                                         │
│                                                                                        │
│ O que: Extrair entidades e relacoes das memorias e armazenar em tabela PostgreSQL      │
│ simples. Na busca, complementar resultados vetoriais com entidades relacionadas.       │
│                                                                                        │
│ Schema:                                                                                │
│ CREATE TABLE agent_memory_entities (                                                   │
│     id SERIAL PRIMARY KEY,                                                             │
│     user_id INTEGER NOT NULL,                                                          │
│     entity_type VARCHAR(50),  -- 'cliente', 'transportadora', 'rota', 'produto'        │
│     entity_name VARCHAR(255),                                                          │
│     memory_id INTEGER REFERENCES agent_memories(id) ON DELETE CASCADE,                 │
│     UNIQUE(user_id, entity_type, entity_name, memory_id)                               │
│ );                                                                                     │
│                                                                                        │
│ CREATE TABLE agent_memory_relations (                                                  │
│     id SERIAL PRIMARY KEY,                                                             │
│     user_id INTEGER NOT NULL,                                                          │
│     source_entity_id INTEGER REFERENCES agent_memory_entities(id),                     │
│     relation_type VARCHAR(50),  -- 'atrasa_em', 'melhor_para', 'custa_mais_que'        │
│     target_entity_id INTEGER REFERENCES agent_memory_entities(id)                      │
│ );                                                                                     │
│                                                                                        │
│ Referencia: Mem0 Graph Memory — conceito similar, implementado sobre pgvector          │
│ existente.                                                                             │
│ Complexidade: ALTA | Impacto: ALTO (para queries multi-hop como "qual transportadora e │
│  melhor para AM considerando custo e prazo?")                                          │
│                                                                                        │
│ ---                                                                                    │
│ 4. O QUE NAO FAZER (anti-recomendacoes)                                                │
│                                                                                        │
│ ┌──────────────────────┬─────────────────────────────────┬─────────────────────────┐   │
│ │       Tecnica        │           Por que NAO           │       Alternativa       │   │
│ ├──────────────────────┼─────────────────────────────────┼─────────────────────────┤   │
│ │                      │ Over-engineering. Nosso agente  │ Manter hook injection + │   │
│ │ MemGPT/Letta         │ nao precisa de virtual memory   │  budget adaptativo      │   │
│ │                      │ paging                          │                         │   │
│ ├──────────────────────┼─────────────────────────────────┼─────────────────────────┤   │
│ │ Fine-tuning para     │ Requer treinamento, nao temos   │ Adaptive RAG via        │   │
│ │ Self-RAG             │ dados suficientes               │ classificacao           │   │
│ │                      │                                 │ heuristica              │   │
│ ├──────────────────────┼─────────────────────────────────┼─────────────────────────┤   │
│ │                      │ Complexidade excessiva (6 tipos │ Importance scoring +    │   │
│ │ MemOS/MIRIX          │  de memoria, 8 agentes)         │ decay resolvem 80% do   │   │
│ │                      │                                 │ problema                │   │
│ ├──────────────────────┼─────────────────────────────────┼─────────────────────────┤   │
│ │ Neo4j para Knowledge │ Infra adicional, custo,         │ PostgreSQL tables com   │   │
│ │  Graph               │ complexidade operacional        │ queries SQL simples     │   │
│ ├──────────────────────┼─────────────────────────────────┼─────────────────────────┤   │
│ │ Spaced Repetition    │ Agente nao e estudante — nao    │ Decay temporal e        │   │
│ │                      │ precisa "revisar" memorias      │ suficiente              │   │
│ ├──────────────────────┼─────────────────────────────────┼─────────────────────────┤   │
│ │ HyDE (Hypothetical   │ Custo alto (5 docs hipoteticos  │ Contextual Retrieval no │   │
│ │ Document Embeddings) │ por query), complexidade, ganho │  indexing e mais        │   │
│ │                      │  marginal                       │ eficiente               │   │
│ ├──────────────────────┼─────────────────────────────────┼─────────────────────────┤   │
│ │ RAPTOR (tree         │ Overhead de construcao da       │ Consolidacao simples    │   │
│ │ summarization)       │ arvore, sem volume para         │ via Haiku               │   │
│ │                      │ justificar                      │                         │   │
│ └──────────────────────┴─────────────────────────────────┴─────────────────────────┘   │
│                                                                                        │
│ ---                                                                                    │
│ 5. VERIFICACAO                                                                         │
│                                                                                        │
│ Como testar Quick Wins (QW-1 a QW-4):                                                  │
│                                                                                        │
│ 1. QW-1: Criar 10 memorias com importancias variadas → verificar que busca semantica   │
│ retorna ordenadas por score composto (nao apenas cosine)                               │
│ 2. QW-2: Deletar memoria → verificar que embedding correspondente foi removido → rodar │
│  GC → verificar que nao ha orfaos                                                      │
│ 3. QW-3: Enviar mensagem ao agente → verificar nos logs que turn foi embedado inline → │
│  buscar semanticamente → confirmar que o turn recente aparece                          │
│ 4. QW-4: Criar memorias que totalizam >4000 chars → verificar que nenhuma memoria esta │
│  cortada no meio                                                                       │
│                                                                                        │
│ Como medir sucesso geral:                                                              │
│                                                                                        │
│ - Antes: Contar quantas vezes o agente usa fallback recencia vs semantica (log         │
│ [MEMORY_INJECT])                                                                       │
│ - Depois: Meta = 80%+ das injecoes via semantica, 0 embeddings orfaos, 0 memorias      │
│ truncadas                                                                              │
│                                                                                        │
│ ---                                                                                    │
│ 6. FONTES PRINCIPAIS                                                                   │
│                                                                                        │
│ Artigos Cientificos                                                                    │
│                                                                                        │
│ - Stanford Generative Agents (2023) — formula de importance scoring                    │
│ - A-MEM: Agentic Memory (NeurIPS 2025) — Zettelkasten para LLMs                        │
│ - MemoryOS (EMNLP 2025) — 3-tier hierarquico                                           │
│ - Intelligent Decay (2025) — esquecimento ativo                                        │
│ - Reflexion (2023) — aprendizado com erros                                             │
│ - MemoryAgentBench (ICLR 2026) — metricas de avaliacao                                 │
│                                                                                        │
│ Frameworks                                                                             │
│                                                                                        │
│ - Mem0 — graph memory sobre pgvector                                                   │
│ - Zep/Graphiti — temporal knowledge graph                                              │
│ - LangMem — extract/consolidate patterns                                               │
│ - CrewAI — weighted memory retrieval                                                   │
│                                                                                        │
│ Documentacao (Context7)                                                                │
│                                                                                        │
│ - pgvector — HNSW tuning (m, ef_construction, ef_search, iterative_scan)               │
│ - Voyage AI — contextualized chunks (voyage-context-3), reranking, input_type          │
│ - Mem0 — graph memory pattern, categorias customizadas                                 │
│ - LangChain — procedural memory (auto-refinamento de prompts)                          │
│                                                                                        │
│ ---                                                                                    │
│ 7. ORDEM DE IMPLEMENTACAO RECOMENDADA                                                  │
│                                                                                        │
│ Semana 1: QW-1 (Importance + Decay) + QW-2 (GC Embeddings) + QW-3 (Ativar inline) +    │
│ QW-4 (Truncamento)                                                                     │
│ Semana 2: T2-1 (Reflection Bank) + T2-3 (HNSW Index)                                   │
│ Semana 3: T2-2 (Budget Adaptativo) + T2-5 (Metricas)                                   │
│ Semana 4: T2-4 (Consolidacao verificada) + T3-2 (Reranking seletivo)                   │
│ Futuro:   T3-1 (Contextual Retrieval) + T3-3 (Knowledge Graph)     




 PARA DEPLOY — rodar nesta ordem:                             ║
  ║ 1. fix_memory_last_accessed_backfill.py  (corrige backfill)  ║
  ║ 2. add_hnsw_indexes_embeddings.py        (re-run: índices)   ║
  ║ 3. gc_orphan_embeddings.py   