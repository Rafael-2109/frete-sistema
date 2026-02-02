"""
Session Pool — DEPRECADO.

Mantido como arquivo vazio para compatibilidade de imports.

HISTÓRICO:
- v1: SessionPool + PooledClient gerenciavam ClaudeSDKClient instances
- v2: Migrado para query() + resume (self-contained, sem pool)
  - query() spawna CLI process, executa, limpa automaticamente
  - resume=sdk_session_id restaura contexto da conversa anterior
  - Sem locks, sem connect/disconnect, sem cleanup thread, sem atexit

O SessionPool era necessário porque ClaudeSDKClient precisa de event loop
persistente (anyio background tasks), mas Flask cria/destrói event loop a
cada request (asyncio.run()). query() não tem esse problema.
"""
