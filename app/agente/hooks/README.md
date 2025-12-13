# Sistema de Hooks - Agent SDK

Sistema robusto de hooks programáticos para o Agent SDK da Nacom Goya.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FLUXO DE HOOKS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [SESSÃO INICIA]                                                           │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────┐                                       │
│   │ on_session_start                │  ← MemoryRetriever carrega memórias   │
│   │ (START HOOK)                    │    Monta WorkingSet estruturado       │
│   └─────────────────────────────────┘                                       │
│        │                                                                    │
│        ▼                                                                    │
│   [USUÁRIO ENVIA MENSAGEM]                                                  │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────┐                                       │
│   │ on_pre_query                    │  ← MemoryRetriever atualiza contexto  │
│   │ (PRE HOOK)                      │    Renderiza context_injection        │
│   └─────────────────────────────────┘                                       │
│        │                                                                    │
│        ▼                                                                    │
│   [SDK PROCESSA + CLAUDE RESPONDE]                                          │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────┐                                       │
│   │ on_post_response                │  ← PatternDetector → candidates       │
│   │ (POST HOOK)                     │    WritePolicy → approved             │
│   │                                 │    MemoryWriter → saved               │
│   └─────────────────────────────────┘                                       │
│        │                                                                    │
│        ▼                                                                    │
│   [FEEDBACK DO USUÁRIO (opcional)]                                          │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────┐                                       │
│   │ on_feedback_received            │  ← LearningLoop processa feedback     │
│   │ (FEEDBACK HOOK)                 │    Ajusta confidence de memórias      │
│   └─────────────────────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Características de Robustez

### 1. Multi-Worker Safe
- **Cache local**: `_contexts` é cache, não fonte de verdade
- **DB como fonte**: `agent_events` é append-only
- **Lock distribuído**: `pg_advisory_xact_lock` para exclusão mútua
- **Rebuild automático**: Contexto reconstruído do DB se cache vazio

### 2. Separação de Responsabilidades
```
MemoryRetriever (pre-hook)    → Recupera memórias
PatternDetector (post-hook)   → Detecta padrões → candidates
MemoryWritePolicy             → Avalia candidates → approved
MemoryWriter                  → Persiste approved → saved
```

### 3. WorkingSet Estruturado
```python
WorkingSet:
    profile: Dict           # Dados do usuário
    semantic: List[Dict]    # Fatos, preferências
    procedural: List[Dict]  # Padrões de uso
    recent_entities: List   # Entidades recentes
    corrections: List[Dict] # Correções aprendidas
```

### 4. Write Policy (Gating)
- Confidence mínima: 0.7 (normal) / 0.5 (fim de sessão)
- Evidence count mínimo: 1
- Deduplicação automática
- **HIGH sensitivity NUNCA é recuperável**

### 5. Instrumentação First-Class
Todos os eventos são logados em `agent_events`:
- `session_start` / `session_end`
- `pre_query` / `post_response`
- `tool_call` / `tool_result` / `tool_error`
- `memory_retrieved` / `memory_candidate` / `memory_saved`
- `feedback_received`

### 6. Segurança
- Scrubbing de CPF, CNPJ, senhas, tokens
- Truncamento de payloads
- HIGH sensitivity nunca vai para contexto

## Uso

### Integração no routes.py

```python
from app.agente.hooks import get_hook_manager

async def _stream_chat_response(...):
    manager = get_hook_manager()

    # Início da sessão (primeira mensagem ou nova)
    if is_first_message:
        context = await manager.on_session_start(user_id, session_id)

    # Antes de enviar ao SDK
    pre_result = await manager.on_pre_query(user_id, session_id, prompt)
    context_injection = pre_result['context_injection']

    # ... chama SDK com context_injection no system_prompt.append ...

    # Após resposta
    post_result = await manager.on_post_response(
        user_id=user_id,
        session_id=session_id,
        user_prompt=prompt,
        assistant_response=full_text,
        tools_used=tools_used,
        tool_errors=tool_errors,
    )

    # Verifica se deve pedir feedback
    if post_result['feedback_requested']:
        # Envia evento para frontend pedir feedback
        yield _sse_event('feedback_request', {})
```

### API de Feedback

```python
@agente_bp.route('/api/feedback', methods=['POST'])
async def api_feedback():
    data = request.get_json()
    manager = get_hook_manager()

    result = await manager.on_feedback_received(
        user_id=current_user.id,
        session_id=data['session_id'],
        feedback_type=data['type'],  # positive, negative, correction, preference
        feedback_data=data['data'],
    )

    return jsonify(result)
```

## Migração

### Local (Python)
```bash
python scripts/migrations/create_agent_events_table.py
```

### Render (SQL)
```sql
-- Copiar conteúdo de scripts/migrations/create_agent_events_table.sql
```

## Componentes

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| HookManager | `manager.py` | Coordenação central |
| MemoryRetriever | `memory_retriever.py` | Recupera memórias |
| PatternDetector | `pattern_detector.py` | Detecta padrões |
| MemoryWritePolicy | `write_policy.py` | Avalia candidatos |
| MemoryWriter | `memory_writer.py` | Persiste memórias |
| EventLogger | `event_logger.py` | Instrumentação |
| LearningLoop | `learning_loop.py` | Processa feedback |

## Enums

```python
class MemoryScope(str, Enum):
    GLOBAL = "global"   # Todos os usuários
    ORG = "org"         # Organização
    USER = "user"       # Específico do usuário

class MemorySensitivity(str, Enum):
    LOW = "low"         # Recuperável livremente
    MEDIUM = "medium"   # Requer contexto
    HIGH = "high"       # APENAS telemetria, NUNCA recuperável

class EventType(str, Enum):
    SESSION_START = "session_start"
    PRE_QUERY = "pre_query"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    POST_RESPONSE = "post_response"
    FEEDBACK_RECEIVED = "feedback_received"
    SESSION_END = "session_end"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_CANDIDATE = "memory_candidate"
    MEMORY_SAVED = "memory_saved"
```

## Padrões Detectados

O PatternDetector detecta automaticamente:

| Padrão | Trigger | Exemplo |
|--------|---------|---------|
| Preferência comunicação | "prefiro respostas curtas" | communication=direto |
| Correção | "não é assim, é X" | Salva correção |
| Fato pessoal | "sou gerente de..." | role=gerente |
| Padrão procedural | Mesma keyword em 2+ queries | Detecta tópico frequente |

## Limites

```python
MAX_MEMORIES_PER_TYPE = 5
MAX_CONTEXT_INJECTION_CHARS = 2000
MAX_RECENT_ENTITIES = 10
MAX_PAYLOAD_LOG_SIZE = 500
```
