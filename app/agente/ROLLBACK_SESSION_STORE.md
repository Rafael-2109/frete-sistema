# Rollback — SessionStore adapter (SDK 0.1.64, Fase A)

**Contexto**: `app/agente/CLAUDE.md` → secao "SDK 0.1.64 (atualizado 2026-04-21)".

---

## Cenarios de rollback

### Cenario A: MirrorErrorMessage > 10 em 1h OU resume falha em producao

**Acao imediata (0 downtime)**:

1. Render Dashboard → Environment → set:
   ```
   AGENT_SDK_SESSION_STORE_ENABLED=false
   ```
2. Redeploy (Render auto-redeploy ou manual). Proximos requests usam path legado via `session_persistence.py`.

**Validar rollback (5 min pos-deploy)**:

```
# Logs Render: nenhum [SESSION_STORE] entry novo
# Query Postgres:
SELECT COUNT(*) FROM claude_session_store
WHERE mtime > (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint - 300000;
-- Deve estar estatico (no crescimento em 5 min)
```

**Investigar** (sem urgencia):

```sql
-- Ultimos MirrorErrorMessage no Sentry
-- Filtrar por message LIKE 'SessionStore mirror_error%'
```

**Cleanup**: nao remover tabela `claude_session_store` — dados orfaos nao afetam performance (indexed). Manter para post-mortem. Pode-se truncar depois se confirmado definitivo:

```sql
-- Opcional, apenas apos confirmacao de abandono definitivo
TRUNCATE claude_session_store;
-- OU
DROP TABLE claude_session_store;
```

---

### Cenario B: Conformance test falha em CI (antes de deploy)

Nao aplicar flag ON em producao ate conformance passar.

```bash
pytest tests/agente/sdk/test_session_store_conformance.py -vv
```

**Debug local**:
```bash
pytest tests/agente/sdk/test_session_store_conformance.py -vv --pdb
```

Se falha em contrato especifico:
- Contrato 1-6 (required + subpath/project_key): bug no adapter core — revisar `append`/`load`
- Contrato 7-8 (`list_sessions`): revisar GROUP BY + filter subpath=''
- Contrato 9-11 (`delete`): revisar cascade semantics
- Contrato 12-13 (`list_subkeys`): revisar SELECT DISTINCT + WHERE subpath != ''

---

### Cenario C: Migration DDL falha

```bash
python scripts/migrations/2026_04_21_claude_session_store.py
```

- Idempotente via `IF NOT EXISTS` — rerunar e seguro
- Se tabela parcialmente criada (DDL interrompida):
  ```sql
  DROP TABLE IF EXISTS claude_session_store;
  ```
  E re-rodar a migration.

---

### Cenario D: Pool asyncpg exhaustion

**Sintoma**: `asyncpg.exceptions.TooManyConnectionsError` em logs Render.

**Query diagnostica**:
```sql
SELECT state, application_name, count(*)
FROM pg_stat_activity
WHERE datname = '<db_name>'
GROUP BY 1, 2
ORDER BY 3 DESC;
```

**Acao**:
1. Verificar se `application_name` de asyncpg excede 12 (4 workers × 3 max_size)
2. Se sim: reduzir `max_size=2` em `session_store_adapter.py::_get_pool`
3. Se ainda insuficiente: revisitar tier Render Postgres (Starter → Standard = 200 conn)

---

## Monitoramento pos-deploy (Fase A soak)

### Metricas a acompanhar (48h antes de Fase B)

```sql
-- 1. Crescimento da tabela (deve ser linear com trafego)
SELECT
    date_trunc('hour', to_timestamp(mtime / 1000)) AS hora,
    COUNT(*) AS rows,
    COUNT(DISTINCT session_id) AS sessions
FROM claude_session_store
WHERE mtime > (EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hours') * 1000)::bigint
GROUP BY 1 ORDER BY 1;

-- 2. Sessions novas vs legadas (distribui proporcional esperada)
SELECT
    'store' AS origem, COUNT(DISTINCT session_id) AS sessions
FROM claude_session_store
WHERE mtime > (EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hours') * 1000)::bigint
UNION ALL
SELECT
    'legado', COUNT(*)
FROM agent_sessions
WHERE updated_at > NOW() - INTERVAL '24 hours'
  AND sdk_session_transcript IS NOT NULL;

-- 3. Pool asyncpg em uso
SELECT application_name, state, count(*)
FROM pg_stat_activity
WHERE application_name LIKE '%asyncpg%' OR application_name LIKE '%postgres%'
GROUP BY 1, 2;
```

### Sentry — alertas recomendados

- Alert: `message:"SessionStore mirror_error"` count > 5 em 1h → trigger Slack
- Alert: `message:"[SESSION_STORE] init falhou"` count > 3 em 1h → trigger Slack
- Alert: `message:"[SESSION_STORE] erro consultando DB"` count > 10 em 1h → warning (fallback conservador em ação)

---

## Criterios para passar a Fase B

Todos obrigatorios:

1. Conformance test: **13/13 contratos** passando em CI
2. 48h producao canary com flag ON: **0 MirrorErrorMessage** no Sentry
3. p50 primeiro turno: **degradacao <= 50ms** vs baseline pre-deploy
4. `claude_session_store` crescendo em rows novos consistentemente
5. Zero alerta `[SESSION_STORE] init falhou` em logs Render
6. Teams bot smoke test: resume apos worker recycle OK
7. Pool `pg_stat_activity` asyncpg < 12 no pico

Se qualquer criterio falhar: investigar raiz, aplicar rollback (Cenario A) e revisar plano.
