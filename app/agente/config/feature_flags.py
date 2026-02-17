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
# Suportado por: Sonnet 4/4.5 e Opus 4.6+
# Opus 4.5 e anteriores NAO suportam
# Requer organizacao no tier 4 ou custom rate limits
# Acima de 200K tokens: input 2x, output 1.5x mais caro
USE_EXTENDED_CONTEXT = os.getenv("AGENT_EXTENDED_CONTEXT", "false").lower() == "true"

# Controle de budget por request (disponivel desde SDK v0.1.6)
USE_BUDGET_CONTROL = os.getenv("AGENT_BUDGET_CONTROL", "false").lower() == "true"
MAX_BUDGET_USD = float(os.getenv("AGENT_MAX_BUDGET_USD", "2.0"))

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

# Self-correction — DESATIVADO permanentemente
# Haiku gerava falsos positivos frequentes na "Observacao de validacao"
# que contradiziam a resposta correta e confundiam o operador.
# Para reativar: melhorar o prompt de validacao em client.py._self_correct_response() primeiro.
USE_SELF_CORRECTION = False

# ====================================================================
# Melhorias de Contexto e Memoria (P0)
# ====================================================================

# Structured Pre-Compaction — salva contexto logistico detalhado antes de compactacao
# Instrui modelo a salvar pedidos, decisoes, tarefas em formato XML estruturado
# ATIVO por default: melhoria direta sem risco, substitui instrucao generica por estruturada
USE_STRUCTURED_COMPACTION = os.getenv("AGENT_STRUCTURED_COMPACTION", "true").lower() == "true"

# Session Summary — gera resumo estruturado ao final de cada interacao
# Usa Haiku para extrair pedidos, decisoes, tarefas e alertas da conversa
# Custo: ~$0.001 por resumo (Haiku: $0.25/1M input + $1.25/1M output)
# ATIVO por default: migration ja aplicada, implementacao estavel
USE_SESSION_SUMMARY = os.getenv("AGENT_SESSION_SUMMARY", "true").lower() == "true"

# Threshold de mensagens para trigger de sumarizacao
# Sumariza quando message_count >= threshold e summary esta stale (delta >= threshold)
SESSION_SUMMARY_THRESHOLD = int(os.getenv("AGENT_SESSION_SUMMARY_THRESHOLD", "5"))

# ====================================================================
# Melhorias de UX (P1)
# ====================================================================

# Prompt Suggestions — gera 2-3 sugestoes contextuais apos cada resposta
# Usa Haiku para sugestoes relevantes ao dominio logistico
# Custo: ~$0.001 por chamada (~500 tokens input, ~200 output)
# Default false: ativar apos verificar que Haiku esta respondendo rapido (<1s)
USE_PROMPT_SUGGESTIONS = os.getenv("AGENT_PROMPT_SUGGESTIONS", "false").lower() == "true"

# Sentiment Detection — detecta frustração do operador e ajusta tom da resposta
# Heuristicas locais (sem chamada API): mensagens curtas, repetidas, marcadores explicitos
# Custo: zero (deteccao local por regex/heuristica)
# Default false: ativar apos validar que os sinais de frustracao sao precisos
USE_SENTIMENT_DETECTION = os.getenv("AGENT_SENTIMENT_DETECTION", "false").lower() == "true"

# Pattern Learning — analisa sessoes historicas e identifica padroes recorrentes
# Usa Haiku para detectar: clientes frequentes, queries repetidas, preferencias
# Salva padroes em /memories/learned/patterns.xml para uso proativo
# Custo: ~$0.002 por analise (~4K tokens input, ~800 output Haiku)
# Trigger: a cada N sessoes do usuario (default 10)
# Default false: requer historico suficiente de sessoes para ser util
USE_PATTERN_LEARNING = os.getenv("AGENT_PATTERN_LEARNING", "true").lower() == "true"

# Numero de sessoes entre analises de padrao
# Analisa quando total_sessions % threshold == 0
PATTERN_LEARNING_THRESHOLD = int(os.getenv("AGENT_PATTERN_LEARNING_THRESHOLD", "10"))

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

# Consolidacao periodica de memorias via Haiku
# Quando usuario excede thresholds, consolida memorias redundantes em resumos compactos
# Custo: ~$0.002 por consolidacao (~4K input + ~800 output Haiku)
# Frequencia: ~1x por semana por usuario ativo
# ATIVO por default: mantem memorias compactas sem intervencao manual
USE_MEMORY_CONSOLIDATION = os.getenv("AGENT_MEMORY_CONSOLIDATION", "true").lower() == "true"

# Thresholds para trigger de consolidacao
# Consolida quando: total_arquivos > FILES OU total_chars > CHARS
MEMORY_CONSOLIDATION_THRESHOLD_FILES = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_FILES", "15"))
MEMORY_CONSOLIDATION_THRESHOLD_CHARS = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_CHARS", "6000"))

# Minimo de arquivos em um diretorio para ser candidato a consolidacao
MEMORY_CONSOLIDATION_MIN_GROUP = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_MIN_GROUP", "3"))

# ====================================================================
# RAG Semantico (Fase 4)
# ====================================================================

# Busca semantica em sessoes anteriores via embeddings
# Quando true: tool semantic_search_sessions disponivel + search_sessions usa semantica
# Quando false: comportamento original (ILIKE em JSONB)
# Default false: ativar apos batch indexer popular session_turn_embeddings
USE_SESSION_SEMANTIC_SEARCH = os.getenv("AGENT_SESSION_SEMANTIC_SEARCH", "false").lower() == "true"

# REMOVIDO: USE_MEMORY_SEMANTIC_SEARCH — unificado em app.embeddings.config.MEMORY_SEMANTIC_SEARCH
# Env var: MEMORY_SEMANTIC_SEARCH (default true)
# Ver: app/embeddings/config.py linha 81

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

# ====================================================================
# Hooks Expandidos (P3)
# ====================================================================

# Expanded Hooks — adiciona hooks Stop e UserPromptSubmit alem dos 3 existentes
# Stop: loga metricas finais da sessao (tokens, custo, duracao, tools usadas)
# UserPromptSubmit: pode enriquecer o prompt do usuario antes de processar
# Default false: ativar apos validar que nao causa overhead excessivo
USE_EXPANDED_HOOKS = os.getenv("AGENT_EXPANDED_HOOKS", "false").lower() == "true"
