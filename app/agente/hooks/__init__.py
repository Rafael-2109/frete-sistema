"""
Sistema de Hooks para o Agent SDK.

ARQUITETURA SIMPLIFICADA:
- MemoryAgent: Subagente Haiku para gerenciamento inteligente de memorias
  - PRE-HOOK: get_relevant_context() - Retorna memorias relevantes para o prompt
  - POST-HOOK: analyze_and_save() - Detecta padroes/correcoes e salva silenciosamente

Uso:
    from app.agente.hooks import get_memory_agent

    agent = get_memory_agent()

    # PRE-HOOK: Antes de enviar ao SDK
    context = agent.get_relevant_context(user_id, prompt)
    if context:
        prompt_with_context = f"[CONTEXTO DO USUARIO]\n{context}\n\n{prompt}"

    # POST-HOOK: Apos resposta
    result = agent.analyze_and_save(user_id, prompt, response)
"""

from .memory_agent import (
    MemoryAgent,
    get_memory_agent,
    reset_memory_agent,
)

__all__ = [
    'MemoryAgent',
    'get_memory_agent',
    'reset_memory_agent',
]
