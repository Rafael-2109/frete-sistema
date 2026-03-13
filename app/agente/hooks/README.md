# Sistema de Hooks - Agent SDK

## Status: Pacote vazio (hooks removidos)

O subagente Haiku (`MemoryAgent` / `auto_haiku`) foi removido em 2026-03-12.

### Por que foi removido

O `auto_haiku` tinha 3 falhas estruturais:
1. **Sem filtro de durabilidade** — salvava passos intermediarios como memorias permanentes
2. **Sem dedup cross-session** — acumulava memorias repetidas entre sessoes
3. **Extração de baixa qualidade** — Haiku nao tinha contexto suficiente para distinguir fato duravel de ruido

### Substituto

A funcionalidade de memoria agora eh provida pela **MCP Memory Tool** (`app/agente/tools/memory_mcp_tool.py`).

O modelo principal (Sonnet/Opus) gerencia suas proprias memorias via `tool_use` autonomo (`mcp__memory__*`), com qualidade superior por ter contexto completo da conversa.

A extracao pos-sessao eh feita pelo `pattern_analyzer.py` via Sonnet (background).
