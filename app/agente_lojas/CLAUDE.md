# Agente Lojas HORA — Guia de Desenvolvimento

**LOC**: ~500 (M0) | **Status**: esqueleto M0 | **Atualizado**: 2026-04-22

Agente dedicado ao pessoal das Lojas Motochefe (HORA), endpoint `/agente-lojas/*`.
Compartilha SDK com `app/agente/` mas com system_prompt, skills, subagents e
escopo de dados isolados.

---

## Porque existe um agente separado

Contrato de isolamento do `app/hora/CLAUDE.md` proibe cross-module entre
HORA, Motochefe-distribuidora e Nacom logistico. Consequencia: o agente
logistico (com ~28K de contexto sobre carteira, frete, Odoo, SSW) nao deve
atender operador de loja — e vice-versa. System prompts, skills e subagents
divergem radicalmente; misturar cria branching por perfil em dezenas de
locais.

Decisao (2026-04-22): novo modulo `app/agente_lojas/` reusando infra do SDK.

Ver proposta completa e decisoes D1-D7 na conversa de spawn.

---

## Estrutura

```
app/agente_lojas/
|-- __init__.py                    # Blueprint + init_app
|-- CLAUDE.md                      # Este arquivo
|-- decorators.py                  # @require_acesso_agente_lojas
|-- config/
|   |-- __init__.py
|   |-- settings.py                # AgentLojasSettings (model, prompt paths, skills)
|   `-- skills_whitelist.py        # Lista de skills permitidas (M1+)
|-- prompts/
|   |-- system_prompt.md           # Identidade + regras operacionais da loja
|   `-- preset_operacional.md      # Tools + safety + /tmp
|-- services/
|   |-- __init__.py
|   `-- scope_injector.py          # Injeta loja_hora_id no user_prompt_submit
|-- routes/
|   |-- __init__.py                # Blueprint agente_lojas_bp
|   |-- chat.py                    # POST /agente-lojas/api/chat (SSE)
|   |-- sessions.py                # Listar/deletar sessoes filtrando agente='lojas'
|   `-- health.py                  # GET /agente-lojas/api/health
`-- templates/agente_lojas/
    `-- chat.html                  # UI de chat (template minimal)
```

---

## Reuso vs exclusivo

| Infra reusada (de `app/agente/`) | Exclusivo deste modulo |
|---------------------------------|------------------------|
| `sdk/client.py` (AgentClient)   | `prompts/system_prompt.md` |
| `sdk/client_pool.py`            | `prompts/preset_operacional.md` |
| `sdk/session_store_adapter.py`  | `config/settings.py` (subclass) |
| `sdk/memory_injection.py`       | `config/skills_whitelist.py` |
| `sdk/hooks.py` (build_hooks)    | `services/scope_injector.py` |
| `config/permissions.py`         | `routes/chat.py` (minimal) |
| `models.py` (AgentSession, ...)  | `templates/agente_lojas/chat.html` |

**Nao duplicar** o SDK — parametrize.

---

## Autorizacao

Decorator unico em `decorators.py:require_acesso_agente_lojas`:

```python
# Permite:
#  - current_user.sistema_lojas == True
#  - current_user.perfil == 'administrador' (admin ve todos)
# Nega para todos os outros.
```

Reusa metodo `current_user.pode_acessar_lojas()` ja existente em
`app/auth/models.py:169`.

---

## Escopo de dados por loja

Hook `_user_prompt_submit` injeta a cada turno:

```xml
<loja_context>
  loja_ids_permitidas: [3]       <!-- usuario escopado -->
  loja_default: 3
  pode_ver_todas: false
</loja_context>
```

Para admin (Rafael):
```xml
<loja_context>
  loja_ids_permitidas: null      <!-- todas -->
  pode_ver_todas: true
</loja_context>
```

Fonte de verdade: `current_user.lojas_hora_ids_permitidas()`.
Skills e subagents DEVEM ler esse contexto e filtrar queries SQL
(`AND loja_id = ANY(...)`).

---

## Particao de sessoes e memorias

Coluna `agente` adicionada em `agent_sessions` e `agent_memories`
(migration `scripts/migrations/2026_04_22_add_agente_coluna.{py,sql}`):

- `'web'` = agente logistico Nacom (valor legado/default)
- `'lojas'` = agente Lojas HORA

Listagens e retrieval DEVEM filtrar por `agente=<valor>` para evitar
cross-contamination.

**M0**: sessoes sao tagueadas corretamente. Retrieval de memoria ainda
compartilha com 'web' (nao e critico enquanto nao houver memorias).
**M3**: isolamento total de memoria (`WHERE agente = 'lojas'`).

---

## Fases de evolucao

| Fase | Escopo | Status |
|------|--------|--------|
| M0   | Esqueleto: endpoint, auth, menu dual, prompt stub | Este commit |
| M1   | Skills M1: `consultando-estoque-loja`, `rastreando-chassi` | Planejado |
| M2   | Recebimento: conferencia + pedido + pecas faltando | Planejado |
| M3   | Venda + isolamento total de memoria | Planejado |
| M4   | Analytics (apos fase financeira HORA) | Planejado |

---

## Gotchas

1. **Nao importar** `app/motochefe/` ou `app/carvia/` direto neste modulo
   (contrato de isolamento HORA). Se precisar de dado da Motochefe como
   fornecedor, consultar via `hora_nf_entrada`.

2. **AgentClient esta em `app/agente/sdk/client.py`** — reuso por import,
   nao copiar.

3. **Template `chat.html`** usa mesmo pattern SSE do `agente/templates/agente/chat.html`
   mas aponta para `/agente-lojas/api/chat`. URLs DEVEM usar `url_for('agente_lojas.X')`.

4. **Sessoes sao marcadas com `agente='lojas'` no insert**. Listagem
   deve SEMPRE incluir `.filter_by(agente='lojas')`.

---

## Referencias

- `app/hora/CLAUDE.md` — contrato de isolamento do modulo HORA
- `app/agente/CLAUDE.md` — guia dev do agente logistico (infra reusada)
- `app/auth/models.py:169-184` — pode_acessar_lojas() + lojas_hora_ids_permitidas()
- `scripts/migrations/2026_04_22_add_agente_coluna.{py,sql}` — migration coluna agente
