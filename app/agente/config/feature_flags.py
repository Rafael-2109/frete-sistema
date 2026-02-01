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
# RESTRICAO: So funciona com Sonnet 4/4.5 — NAO com Opus
# Requer organizacao no tier 4 ou custom rate limits
# Acima de 200K tokens: input 2x, output 1.5x mais caro
USE_EXTENDED_CONTEXT = os.getenv("AGENT_EXTENDED_CONTEXT", "false").lower() == "true"

# Controle de budget por request (disponivel desde SDK v0.1.6)
USE_BUDGET_CONTROL = os.getenv("AGENT_BUDGET_CONTROL", "false").lower() == "true"
MAX_BUDGET_USD = float(os.getenv("AGENT_MAX_BUDGET_USD", "2.0"))

# Context Clearing automatico — remove thinking/tool_uses antigos
USE_CONTEXT_CLEARING = os.getenv("AGENT_CONTEXT_CLEARING", "false").lower() == "true"

# Prompt Caching — economia de 50-90% tokens input
# O system_prompt.md do agente e extenso (~8K tokens)
USE_PROMPT_CACHING = os.getenv("AGENT_PROMPT_CACHING", "false").lower() == "true"

# ====================================================================
# Architecture + Seguranca
# ====================================================================

# Self-correction — validar output antes de entregar
# Chamada Haiku rapida para verificar coerencia da resposta
USE_SELF_CORRECTION = os.getenv("AGENT_SELF_CORRECTION", "false").lower() == "true"
