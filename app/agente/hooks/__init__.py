"""
Sistema de Hooks para o Agent SDK.

Historico: Este pacote continha o MemoryAgent (subagente Haiku)
para deteccao automatica de memorias (auto_haiku). Deprecado e
removido em 2026-03-12.

A funcionalidade de memoria agora eh provida pela MCP Memory Tool
em app/agente/tools/memory_mcp_tool.py. O modelo principal gerencia
suas proprias memorias via tool_use autonomo (mcp__memory__*).
"""
