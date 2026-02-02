"""
DEPRECATED: Sistema de Hooks para o Agent SDK.

A funcionalidade de memória agora é provida pela MCP Memory Tool
em app/agente/tools/memory_mcp_tool.py.

O modelo principal gerencia suas próprias memórias via tool_use
autônomo (mcp__memory__*), sem necessidade de subagente Haiku.

Mantido temporariamente para rollback de segurança.
Os exports são preservados para evitar ImportError em código legado.
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
