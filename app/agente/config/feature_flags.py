"""
Feature flags para o Agent SDK.
Todas iniciam False — ativar progressivamente apos testes.

Uso: definir variaveis de ambiente antes de iniciar o servidor.
Exemplo: AGENT_BUDGET_CONTROL=true flask run --debug
"""
import os

# ====================================================================
# Quick Wins
# ====================================================================

# Extended context window (1M tokens)
# Opus 4.6 e Sonnet 4.6: 1M tokens NATIVO (sem beta header necessário)
# Sonnet 4.5/4.0: precisam de beta header "context-1m-2025-08-07"
# Flag mantida apenas para documentação — modelos atuais usam 1M automaticamente
# Acima de 200K tokens: input 2x, output 1.5x mais caro
USE_EXTENDED_CONTEXT = os.getenv("AGENT_EXTENDED_CONTEXT", "false").lower() == "true"

# Controle de budget por request (disponivel desde SDK v0.1.6)
USE_BUDGET_CONTROL = os.getenv("AGENT_BUDGET_CONTROL", "true").lower() == "true"
MAX_BUDGET_USD = float(os.getenv("AGENT_MAX_BUDGET_USD", "5.0"))

# Context Clearing automatico — remove thinking/tool_uses antigos
# ATIVO por default: a Anthropic recomenda habilitar para conversas longas.
# O hook PreCompact (client.py) contém instruções explícitas de compactação.
# NOTA (2026-02): clear-thinking e clear-tool-uses foram promovidos a GA.
#   Beta headers removidos — flag controla apenas log/documentação.
# Para desativar: AGENT_CONTEXT_CLEARING=false
USE_CONTEXT_CLEARING = os.getenv("AGENT_CONTEXT_CLEARING", "true").lower() == "true"

# Prompt Caching — economia de 50-90% tokens input
# O system_prompt.md do agente e extenso (~8K tokens)
# NOTA (2026-02): prompt-caching foi promovido a GA.
#   Beta header removido — flag controla apenas log/documentação.
USE_PROMPT_CACHING = os.getenv("AGENT_PROMPT_CACHING", "true").lower() == "true"

# ====================================================================
# Architecture + Seguranca
# ====================================================================

# Self-correction — reescrito para Sonnet 4.6 (prompt específico para tabelas numéricas)
# Histórico: Haiku gerava falsos positivos com escopo amplo. Prompt agora valida APENAS
# inconsistências aritméticas em respostas com tabelas numéricas (threshold 500 chars).
# ATIVO por default: Sonnet 4.6 com scope restrito reduz falsos positivos.
# Para desativar: AGENT_SELF_CORRECTION=false
USE_SELF_CORRECTION = os.getenv("AGENT_SELF_CORRECTION", "true").lower() == "true"

# Prompt Cache Optimization — extrai variáveis dinâmicas do system prompt
# ({data_atual}, {usuario_nome}, {user_id}) para injeção via UserPromptSubmit hook.
# System prompt fica estático entre usuários e turnos → prompt caching hits no CLI.
# Depende de USE_CUSTOM_SYSTEM_PROMPT=true para ter efeito.
# Rollback: AGENT_PROMPT_CACHE_OPTIMIZATION=false
USE_PROMPT_CACHE_OPTIMIZATION = os.getenv("AGENT_PROMPT_CACHE_OPTIMIZATION", "true").lower() == "true"

# ====================================================================
# Melhorias de Contexto e Memoria (P0)
# ====================================================================

# Structured Pre-Compaction — salva contexto logistico detalhado antes de compactacao
# Instrui modelo a salvar pedidos, decisoes, tarefas em formato XML estruturado
# ATIVO por default: melhoria direta sem risco, substitui instrucao generica por estruturada
USE_STRUCTURED_COMPACTION = os.getenv("AGENT_STRUCTURED_COMPACTION", "true").lower() == "true"

# Session Summary — gera resumo estruturado ao final de cada interacao
# Usa Sonnet para extrair pedidos, decisoes, tarefas e alertas da conversa
# Custo: ~$0.003 por resumo (Sonnet: $3/1M input + $15/1M output)
# ATIVO por default: migration ja aplicada, implementacao estavel
USE_SESSION_SUMMARY = os.getenv("AGENT_SESSION_SUMMARY", "true").lower() == "true"

# Threshold de mensagens para trigger de sumarizacao
# Sumariza quando message_count >= threshold e summary esta stale (delta >= threshold)
SESSION_SUMMARY_THRESHOLD = int(os.getenv("AGENT_SESSION_SUMMARY_THRESHOLD", "5"))

# ====================================================================
# Melhorias de UX (P1)
# ====================================================================

# Prompt Suggestions — gera 2-3 sugestoes contextuais apos cada resposta
# Usa Sonnet para sugestoes relevantes ao dominio logistico
# Custo: ~$0.003 por chamada (~500 tokens input, ~200 output)
# ATIVO por default: roda em background, nao bloqueia resposta.
# Para desativar: AGENT_PROMPT_SUGGESTIONS=false
USE_PROMPT_SUGGESTIONS = os.getenv("AGENT_PROMPT_SUGGESTIONS", "true").lower() == "true"

# Sentiment Detection — detecta frustração do operador e ajusta tom da resposta
# Heuristicas locais (sem chamada API): mensagens curtas, repetidas, marcadores explicitos
# Custo: zero (deteccao local por regex/heuristica)
# Default false: ativar apos validar que os sinais de frustracao sao precisos
USE_SENTIMENT_DETECTION = os.getenv("AGENT_SENTIMENT_DETECTION", "true").lower() == "true"

# Pattern Learning — analisa sessoes historicas e identifica padroes recorrentes
# Usa Sonnet para detectar: clientes frequentes, queries repetidas, preferencias
# Salva padroes em /memories/learned/patterns.xml para uso proativo
# Custo: ~$0.006 por analise (~4K tokens input, ~800 output Sonnet)
# Trigger: a cada N sessoes do usuario (default 10)
# Default false: requer historico suficiente de sessoes para ser util
USE_PATTERN_LEARNING = os.getenv("AGENT_PATTERN_LEARNING", "true").lower() == "true"

# Numero de sessoes entre analises de padrao
# Analisa quando total_sessions % threshold == 0
PATTERN_LEARNING_THRESHOLD = int(os.getenv("AGENT_PATTERN_LEARNING_THRESHOLD", "10"))

# Behavioral Profile — gera user.xml (Tier 1) com perfil comportamental
# Reutiliza mesma chamada Sonnet do patterns (zero custo adicional quando coincidem)
# Threshold menor que patterns (5 vs 10) para perfil mais rapido
USE_BEHAVIORAL_PROFILE = os.getenv("AGENT_BEHAVIORAL_PROFILE", "true").lower() == "true"
BEHAVIORAL_PROFILE_THRESHOLD = int(os.getenv("AGENT_BEHAVIORAL_PROFILE_THRESHOLD", "5"))

# Extracao pos-sessao de conhecimento organizacional (PRD v2.1)
# Analisa TODAS as mensagens via Sonnet para extrair: definicoes de termos,
# cargos, regras de negocio, correcoes factuais. Salva como memorias empresa (user_id=0).
# Custo: ~$0.003 por execucao (Sonnet, contexto completo). Volume baixo (~4 sessoes/dia).
# Trigger: a cada exchange (min 3 msgs), roda em daemon thread (background).
# A ultima execucao de cada sessao contem toda a conversa (= extracao de fim de sessao).
USE_POST_SESSION_EXTRACTION = os.getenv("AGENT_POST_SESSION_EXTRACTION", "true").lower() == "true"

# Minimo de mensagens para iniciar extracao (evita rodar em sessoes triviais)
POST_SESSION_EXTRACTION_MIN_MESSAGES = int(os.getenv("AGENT_POST_SESSION_EXTRACTION_MIN_MESSAGES", "3"))

# ====================================================================
# Dashboard e Analytics (P2)
# ====================================================================

# Agent Insights Dashboard — pagina admin com analytics de uso do agente
# Mostra: top queries, custos por usuario, tools mais usadas, erros, duracao
# Acesso: apenas usuarios com perfil 'administrador'
# ATIVO por default: dashboard estavel, acesso restrito a admin
USE_AGENT_INSIGHTS = os.getenv("AGENT_INSIGHTS", "true").lower() == "true"

# Reversibility Check — classifica acoes por reversibilidade e pede confirmacao extra
# Intercepta Skills e Bash que podem executar acoes destrutivas (criar separacao, modificar dados)
# Emite evento SSE 'destructive_action_warning' para dialog de confirmacao no frontend
# Default false: ativar apos validar que a classificacao nao gera falsos positivos
USE_REVERSIBILITY_CHECK = os.getenv("AGENT_REVERSIBILITY_CHECK", "true").lower() == "true"

# Friction Analysis — analisa sessoes e identifica pontos de friccao
# Detecta: queries repetidas (operador nao obteve resposta), mensagens curtas apos erro,
# sessoes abandonadas, uso excessivo de tools sem resultado
# Integrado ao Dashboard de Insights (P2-2)
# ATIVO por default: historico suficiente acumulado, integrado ao Insights
USE_FRICTION_ANALYSIS = os.getenv("AGENT_FRICTION_ANALYSIS", "true").lower() == "true"

# ====================================================================
# Memoria Persistente (P0)
# ====================================================================

# Auto-inject de memorias do usuario via UserPromptSubmit hook
# Carrega memorias do banco e injeta como additionalContext no inicio de cada turno
# Garante que o modelo SEMPRE tem contexto de memorias, mesmo se nao chamar tools
# ATIVO por default: feature core do agente, kill switch para rollback
# Para desativar: AGENT_AUTO_MEMORY_INJECTION=false
USE_AUTO_MEMORY_INJECTION = os.getenv("AGENT_AUTO_MEMORY_INJECTION", "true").lower() == "true"

# Threshold minimo de similaridade para injecao de memorias semanticas
# Memorias com score abaixo deste valor NAO sao injetadas (Tier 2)
# Memorias protegidas (user.xml, preferences.xml) sao SEMPRE injetadas (Tier 1)
# Ajustar em producao sem deploy: AGENT_MEMORY_MIN_SIMILARITY=0.50
MEMORY_INJECTION_MIN_SIMILARITY = float(os.getenv("AGENT_MEMORY_MIN_SIMILARITY", "0.45"))

# Consolidacao periodica de memorias via Sonnet
# Quando usuario excede thresholds, consolida memorias redundantes em resumos compactos
# Custo: ~$0.006 por consolidacao (~4K input + ~800 output Sonnet)
# Frequencia: ~1x por semana por usuario ativo
# ATIVO por default: mantem memorias compactas sem intervencao manual
USE_MEMORY_CONSOLIDATION = os.getenv("AGENT_MEMORY_CONSOLIDATION", "true").lower() == "true"

# Thresholds para trigger de consolidacao
# Consolida quando: total_arquivos > FILES OU total_chars > CHARS
MEMORY_CONSOLIDATION_THRESHOLD_FILES = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_FILES", "15"))
MEMORY_CONSOLIDATION_THRESHOLD_CHARS = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_CHARS", "6000"))

# Minimo de arquivos em um diretorio para ser candidato a consolidacao
MEMORY_CONSOLIDATION_MIN_GROUP = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_MIN_GROUP", "3"))

# Cold tier — sanitizacao automatica de memorias ineficazes
# Move para cold (nao injetadas, mas buscaveis) memorias com eficacia abaixo do threshold
# Eficacia = effective_count / usage_count (0.10 = 10%)
# Criterio: usage >= MIN_USAGE E eficacia < MAX_EFFICACY
# Rollback: AGENT_COLD_MOVE=false ou ajustar thresholds sem deploy
USE_COLD_MOVE = os.getenv("AGENT_COLD_MOVE", "true").lower() == "true"
COLD_MOVE_MIN_USAGE = int(os.getenv("AGENT_COLD_MOVE_MIN_USAGE", "20"))
COLD_MOVE_MAX_EFFICACY = float(os.getenv("AGENT_COLD_MOVE_MAX_EFFICACY", "0.10"))

# Sanitizar memorias empresa (user_id=0) com mesmos criterios
# Desativar se empresa mover memorias demais: AGENT_COLD_MOVE_EMPRESA=false
USE_COLD_MOVE_EMPRESA = os.getenv("AGENT_COLD_MOVE_EMPRESA", "true").lower() == "true"

# Garbage collection de memorias cold > 90 dias (MEMORY_PROTOCOL.md)
# Remove permanentemente memorias ja classificadas como cold sem atividade por 90+ dias
# Independente de USE_COLD_MOVE — pausar classificacao nao impede limpeza de memorias ja frias
# Rollback: AGENT_COLD_GC=false
USE_COLD_GC = os.getenv("AGENT_COLD_GC", "true").lower() == "true"
COLD_GC_MAX_AGE_DAYS = int(os.getenv("AGENT_COLD_GC_MAX_AGE_DAYS", "90"))

# Merge inteligente de memorias empresa via Sonnet (substitui append cego)
# Quando true: _try_enrich_existing() usa Sonnet para fundir old+new em versao unica
# Quando false: fallback para append legado (old + "<!-- Enriquecido em -->" + new)
# Custo: ~$0.002 por merge. Frequencia: ~1-3x/semana (so quando enrichment dispara)
# Rollback instantaneo: AGENT_MERGE_ENRICHMENT=false
USE_MERGE_ENRICHMENT = os.getenv("AGENT_MERGE_ENRICHMENT", "true").lower() == "true"

# Briefing Inter-Sessão — injeta eventos entre sessões (erros Odoo, imports, alertas de memória)
# Queries SQL leves, zero custo LLM. Injetado como Tier 0b no início da sessão.
# Default true (env AGENT_INTERSESSION_BRIEFING)
USE_INTERSESSION_BRIEFING = os.getenv("AGENT_INTERSESSION_BRIEFING", "true").lower() == "true"

# ====================================================================
# RAG Semantico (Fase 4)
# ====================================================================

# Embedding inline de turns de sessão: gera embedding em tempo real ao salvar cada turn
# Quando true: routes.py chama _embed_session_turn_best_effort() on-save
# Quando false: embedding só via batch indexer manual (session_turn_indexer.py)
# ATIVO por default (QW-3): batch indexer complementa, mas inline garante cobertura real-time
#
# NOTA: Esta flag controla ESCRITA de embeddings. A LEITURA é controlada por:
#   app/embeddings/config.py:SESSION_SEMANTIC_SEARCH (env: SESSION_SEMANTIC_SEARCH, default true)
# Ambas devem estar true para busca semântica de sessões funcionar end-to-end.
# UNIFICADO (GAP 5): Usa mesma env var que config.py (SESSION_SEMANTIC_SEARCH) para evitar
# dessincronização entre write e read path ao setar apenas uma env var.
USE_SESSION_TURN_EMBEDDING = os.getenv("SESSION_SEMANTIC_SEARCH", "true").lower() == "true"

# Alias legado (compatibilidade com código existente que importa USE_SESSION_SEMANTIC_SEARCH)
USE_SESSION_SEMANTIC_SEARCH = USE_SESSION_TURN_EMBEDDING

# REMOVIDO: USE_MEMORY_SEMANTIC_SEARCH — unificado em app.embeddings.config.MEMORY_SEMANTIC_SEARCH
# Env var: MEMORY_SEMANTIC_SEARCH (default true)
# Ver: app/embeddings/config.py linha 106

# ====================================================================
# Teams Bot
# ====================================================================

# Modelo padrao para o bot do Teams (Sonnet para velocidade)
# Opus 4.6: ~91s por resposta com tools, custo $5/$25 per 1M tokens
# Sonnet 4.5: ~15-25s por resposta com tools, custo $3/$15 per 1M tokens
# Para usar Opus no Teams: TEAMS_DEFAULT_MODEL=claude-opus-4-6
TEAMS_DEFAULT_MODEL = os.getenv("TEAMS_DEFAULT_MODEL", "claude-opus-4-6")

# Modo assincrono para o bot do Teams
# Quando true: retorna task_id imediatamente, processa em daemon thread, Azure Function faz polling
# Quando false: fluxo sincrono legado (resposta direta na mesma request)
TEAMS_ASYNC_MODE = os.getenv("TEAMS_ASYNC_MODE", "true").lower() == "true"

# Timeout para AskUserQuestion no Teams (segundos)
# O usuario tem este tempo para responder o Adaptive Card antes de timeout
# Default 120s (2 minutos) — maior que web (55s) pois Teams e mais lento
TEAMS_ASK_USER_TIMEOUT = int(os.getenv("TEAMS_ASK_USER_TIMEOUT", "120"))

# Progressive streaming: flush texto parcial ao DB durante processamento
# Quando true: polling retorna resposta_parcial enquanto status='processing'
# Quando false: comportamento atual (resposta so no final)
TEAMS_PROGRESSIVE_STREAMING = os.getenv("TEAMS_PROGRESSIVE_STREAMING", "true").lower() == "true"

# Intervalo em segundos entre flushes de texto parcial ao DB
TEAMS_STREAM_FLUSH_INTERVAL = float(os.getenv("TEAMS_STREAM_FLUSH_INTERVAL", "4.0"))

# Smart model routing: mensagens simples usam Sonnet (15-25s), complexas Opus (60-90s)
# Desativar para voltar ao comportamento anterior (tudo Opus)
TEAMS_SMART_MODEL_ROUTING = os.getenv("TEAMS_SMART_MODEL_ROUTING", "true").lower() == "true"

# Modelo rápido para mensagens simples (usado quando SMART_MODEL_ROUTING=true)
TEAMS_FAST_MODEL = os.getenv("TEAMS_FAST_MODEL", "claude-sonnet-4-6")

# Feedback visual de tool calls: mostra "Consultando dados..." durante execução de tools
# Desativar se causar flickering ou problemas visuais no Teams
TEAMS_TOOL_STATUS_FEEDBACK = os.getenv("TEAMS_TOOL_STATUS_FEEDBACK", "true").lower() == "true"

# ====================================================================
# Hooks Expandidos (P3)
# ====================================================================

# Expanded Hooks — adiciona hooks Stop e UserPromptSubmit alem dos 3 existentes
# Stop: loga metricas finais da sessao (tokens, custo, duracao, tools usadas)
# UserPromptSubmit: pode enriquecer o prompt do usuario antes de processar
# ATIVO por default: overhead minimo (apenas logging).
# Para desativar: AGENT_EXPANDED_HOOKS=false
USE_EXPANDED_HOOKS = os.getenv("AGENT_EXPANDED_HOOKS", "true").lower() == "true"

# ====================================================================
# Stderr Callback (SDK Debug Output)
# ====================================================================
# Quando true: registra stderr callback no ClaudeAgentOptions para capturar
# debug output do CLI subprocess em real-time. Emite como SSE event 'stderr'
# para o debug panel no frontend (admin-only, requer debug_mode=true).
# Quando false: stderr capturado apenas em ProcessError (comportamento original).
# Desativar se causar overhead perceptível no streaming.
USE_STDERR_CALLBACK = os.getenv("AGENT_STDERR_CALLBACK", "true").lower() == "true"

# ====================================================================
# Async Streaming (migração incremental)
# ====================================================================
# Quando true: usa implementação async nativa para streaming SSE
# Quando false: usa bridge Thread+Queue+asyncio.run (legado)
USE_ASYNC_STREAMING = os.getenv("ASYNC_STREAMING", "true").lower() == "true"
# ====================================================================
# Persistent SDK Client (migração query() → ClaudeSDKClient)
# ====================================================================
# Quando true: usa ClaudeSDKClient persistente (subprocess vivo entre turnos)
#   - Pool por sessão no daemon thread com event loop persistente
#   - ~2x menor latência (sem overhead spawn/destroy CLI por turno)
#   - Habilita interrupt, model switch, MCP server recovery
# Quando false: usa query() standalone (status quo — spawn + destroy por turno)
# Rollback instantâneo: AGENT_PERSISTENT_SDK_CLIENT=false + restart
# Ref: .claude/references/ROADMAP_SDK_CLIENT.md
USE_PERSISTENT_SDK_CLIENT = os.getenv("AGENT_PERSISTENT_SDK_CLIENT", "true").lower() == "true"

# Timeout em segundos para idle clients no pool (disconnect automático)
# Libera recursos de clients sem atividade por este período
PERSISTENT_CLIENT_IDLE_TIMEOUT = int(os.getenv("AGENT_CLIENT_IDLE_TIMEOUT", "900"))  # 15 min

# Intervalo em segundos entre limpezas de clients idle
PERSISTENT_CLIENT_CLEANUP_INTERVAL = int(os.getenv("AGENT_CLIENT_CLEANUP_INTERVAL", "60"))  # 1 min

# ====================================================================
# Custom System Prompt (Prompt Architecture v2)
# ====================================================================

# Substitui preset claude_code por preset_operacional.md + system_prompt.md
# Quando true: system_prompt = preset_operacional.md + system_prompt.md (string pura)
# Quando false: system_prompt = {preset: claude_code, append: system_prompt.md} (original)
# ATIVO: preset_operacional.md substitui claude_code preset
# Rollback instantaneo: AGENT_CUSTOM_SYSTEM_PROMPT=false
USE_CUSTOM_SYSTEM_PROMPT = os.getenv("AGENT_CUSTOM_SYSTEM_PROMPT", "true").lower() == "true"

# ====================================================================
# Debug Mode (Admin)
# ====================================================================

# Debug Mode — permite admin desbloquear tabelas internas e memorias cross-user
# Controlado por toggle na UI, validado server-side (perfil=administrador)
# Default true: feature disponivel, mas requer ativacao explicita pelo admin
USE_DEBUG_MODE = os.getenv("AGENT_DEBUG_MODE", "true").lower() == "true"

# ====================================================================
# Improvement Dialogue (Loop Agent SDK <-> Claude Code)
# ====================================================================

# Habilita dialogo versionado de melhoria continua.
# Agent SDK gera sugestoes pos-sessao via Sonnet (~$0.005/sessao).
# Claude Code (D8 cron diario) avalia, implementa e responde.
# Agent SDK verifica respostas via intersession briefing.
# Default false: ativacao gradual apos testes.
USE_IMPROVEMENT_DIALOGUE = os.getenv("AGENT_IMPROVEMENT_DIALOGUE", "false").lower() == "true"

# Minimo de mensagens na sessao para gerar sugestoes de melhoria
IMPROVEMENT_DIALOGUE_MIN_MESSAGES = int(os.getenv("AGENT_IMPROVEMENT_MIN_MESSAGES", "3"))
