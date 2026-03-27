# Limpeza v2 (query) — Checklist de Remocao

> **Status**: v2 DESLIGADO em 2026-03-27 (dispatches removidos).
> Dead code mantido para rollback. Remover quando confirmado estavel em producao.
>
> **Rollback**: `git revert <commit>` restaura os 4 dispatches.

---

## O que foi feito (2026-03-27)

Removidos os 4 dispatches condicionais que escolhiam entre v2 e v3:

| Arquivo | O que mudou |
|---------|-------------|
| `app/agente/sdk/client.py:stream_response()` | Removido `if USE_PERSISTENT_SDK_CLIENT` — chama `_stream_response_persistent` direto |
| `app/agente/routes.py` (streaming) | Removido `else: asyncio.run()` — usa `submit_coroutine` direto |
| `app/agente/routes.py` (interrupt) | Removido guard `if not USE_PERSISTENT_SDK_CLIENT: return 501` |
| `app/agente/routes.py` (health) | Removido check condicional — pool status sempre incluso |
| `app/teams/services.py` (non-streaming) | Removido `else: asyncio.run()` — usa `submit_coroutine` direto |
| `app/teams/services.py` (streaming) | Idem |

---

## O que remover quando estavel (~2 semanas apos deploy)

### 1. Dead code em `app/agente/sdk/client.py`

| Item | Linhas aprox. | LOC |
|------|---------------|-----|
| `import query as sdk_query` | linha 26 | 1 |
| `streaming_done_event` field em `_StreamParseState` | linhas 1037-1040 | 4 |
| `streaming_done_event.set()` em `_parse_sdk_message` (ResultMessage) | linhas 1830-1831 | 2 |
| `state.streaming_done_event = None` em `_stream_response_persistent` | linhas 2911-2914 | 4 |
| Comentarios "streaming_done_event" em error handlers | ~6 locais | 12 |
| `_stream_response()` metodo inteiro | linhas ~3245-3593 | **~350** |
| `_make_streaming_prompt()` metodo inteiro | linhas ~3596-3643 | **~48** |
| `_with_resume()` metodo inteiro | linhas ~3644-3659 | **~16** |
| **Subtotal** | | **~437 LOC** |

### 2. Feature flag em `app/agente/config/feature_flags.py`

| Item | Linhas |
|------|--------|
| Bloco `USE_PERSISTENT_SDK_CLIENT` + constantes idle/cleanup | 261-278 |

**NAO remover** `PERSISTENT_CLIENT_IDLE_TIMEOUT` e `PERSISTENT_CLIENT_CLEANUP_INTERVAL` — sao usados pelo pool (agora unico path).

### 3. Guards em `app/agente/sdk/client_pool.py`

| Item | Linhas |
|------|--------|
| Docstring "Feature flag: USE_PERSISTENT_SDK_CLIENT (default false)" | 14 |
| `from ..config.feature_flags import USE_PERSISTENT_SDK_CLIENT` em `_ensure_pool_initialized` | 150 |
| `if not USE_PERSISTENT_SDK_CLIENT: return False` | 151 |
| `from ..config.feature_flags import USE_PERSISTENT_SDK_CLIENT` em `get_pool_status` | 460 |
| `if not USE_PERSISTENT_SDK_CLIENT: return {'enabled': False}` | 462-466 |

Apos remover a flag, o pool SEMPRE inicia. Esses guards viram dead code.

### 4. Scripts de teste

| Script | O que remover |
|--------|---------------|
| `scripts/test_sdk_client_e2e.py` | Secao 7 inteira (rollback path check, linhas 492-517) |
| `scripts/test_sdk_client_migration.py` | Testes que verificam dispatch flag e `_stream_response` existem |

### 5. Documentacao

| Arquivo | O que atualizar |
|---------|-----------------|
| `app/agente/CLAUDE.md` | Remover refs a DC-8, `streaming_done_event`, `_stream_response` |
| `app/teams/CLAUDE.md` | Remover tabela v2/v3, flag rollback, "v3 em rollback desde DC-7" |
| `.claude/references/ROADMAP_SDK_CLIENT.md` | Marcar Fase 5 como CONCLUIDA |
| Este arquivo (`V2_QUERY_CLEANUP.md`) | Deletar |

### 6. Env var no Render

| Acao |
|------|
| Remover `AGENT_PERSISTENT_SDK_CLIENT` do Render Dashboard (nao sera mais lida) |

---

## Criterios para remover

- [ ] Deploy com dispatches removidos rodando sem erros por >= 2 semanas
- [ ] Zero issues Sentry relacionadas a `client_pool` ou streaming
- [ ] CPU e memoria estaveis (sem crescimento monotonico)
- [ ] Teams funcional (mensagens enviadas e recebidas)
- [ ] Interrupt funcional (botao web)
