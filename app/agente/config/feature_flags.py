"""
Feature flags para migracao gradual do Agent SDK.
Todas iniciam False — ativar progressivamente apos testes.

Uso: definir variaveis de ambiente antes de iniciar o servidor.
Exemplo: AGENT_BUDGET_CONTROL=true flask run --debug
"""
import os

# ====================================================================
# FASE 2: Quick Wins
# ====================================================================

# Extended context window (1M tokens)
# RESTRICAO: So funciona com Sonnet 4/4.5 — NAO com Opus
# Requer organizacao no tier 4 ou custom rate limits
# Acima de 200K tokens: input 2x, output 1.5x mais caro
USE_EXTENDED_CONTEXT = os.getenv("AGENT_EXTENDED_CONTEXT", "false").lower() == "true"

# Controle de budget por request (disponivel desde SDK v0.1.6)
USE_BUDGET_CONTROL = os.getenv("AGENT_BUDGET_CONTROL", "false").lower() == "true"
MAX_BUDGET_USD = float(os.getenv("AGENT_MAX_BUDGET_USD", "2.0"))

# Context Clearing automatico — remove thinking/tool_uses antigos
# Threshold recomendado producao: 30-40k tokens
USE_CONTEXT_CLEARING = os.getenv("AGENT_CONTEXT_CLEARING", "false").lower() == "true"
CONTEXT_CLEARING_THRESHOLD = int(os.getenv("AGENT_CONTEXT_CLEARING_THRESHOLD", "35000"))

# Compaction manual de contexto via Haiku
# Ativado quando contexto excede threshold de tokens
USE_MANUAL_COMPACTION = os.getenv("AGENT_MANUAL_COMPACTION", "false").lower() == "true"
COMPACTION_TOKEN_THRESHOLD = int(os.getenv("AGENT_COMPACTION_THRESHOLD", "80000"))

# Prompt Caching — economia de 50-90% tokens input
# O system_prompt.md do agente e extenso (~8K tokens)
USE_PROMPT_CACHING = os.getenv("AGENT_PROMPT_CACHING", "false").lower() == "true"

# ====================================================================
# FASE 3: Architecture + Seguranca
# ====================================================================

# Subagentes programaticos com AgentDefinition
# Coexiste com .claude/agents/*.md (filesystem)
USE_PROGRAMMATIC_AGENTS = os.getenv("AGENT_PROGRAMMATIC_AGENTS", "false").lower() == "true"

# Self-correction — validar output antes de entregar
# Chamada Haiku rapida para verificar coerencia da resposta
USE_SELF_CORRECTION = os.getenv("AGENT_SELF_CORRECTION", "false").lower() == "true"

# ====================================================================
# FASE 4: Cookbook Capabilities
# ====================================================================

# Text-to-SQL — converte perguntas em linguagem natural para SQL
# Usa Haiku para gerar e validar SQL (Evaluator-Optimizer pattern)
# Seguranca: regex validator + SET TRANSACTION READ ONLY + blacklist tabelas
USE_TEXT_TO_SQL = os.getenv("AGENT_TEXT_TO_SQL", "false").lower() == "true"
TEXT_TO_SQL_TIMEOUT = int(os.getenv("AGENT_TEXT_TO_SQL_TIMEOUT", "5"))
TEXT_TO_SQL_MAX_ROWS = int(os.getenv("AGENT_TEXT_TO_SQL_MAX_ROWS", "500"))

# ====================================================================
# FASE 5: ClaudeSDKClient (sessoes bidirecionais)
# Substitui query() por ClaudeSDKClient para manter canal persistente.
# SDK gerencia contexto e compactacao nativamente.
# ====================================================================

# Ativar ClaudeSDKClient em vez de query()
# Quando false: usa query() (comportamento atual)
# Quando true: usa ClaudeSDKClient via SessionPool
USE_SDK_CLIENT = os.getenv("AGENT_USE_SDK_CLIENT", "false").lower() == "true"

# Maximo de ClaudeSDKClient simultaneos no pool
# Cada client consome ~300-500MB (subprocesso CLI)
# Render Pro 4GB: max 5-6 | Standard 2GB: max 2-3 | Starter 512MB: max 1
SDK_CLIENT_MAX_POOL = int(os.getenv("AGENT_SDK_CLIENT_MAX_POOL", "5"))

# Timeout em segundos para desconectar clients inativos
# Default 300s (5 min) — libera memoria de sessoes abandonadas
SDK_CLIENT_IDLE_TIMEOUT = int(os.getenv("AGENT_SDK_CLIENT_IDLE_TIMEOUT", "300"))

# Intervalo em segundos entre ciclos de cleanup do pool
SDK_CLIENT_CLEANUP_INTERVAL = int(os.getenv("AGENT_SDK_CLIENT_CLEANUP_INTERVAL", "60"))
