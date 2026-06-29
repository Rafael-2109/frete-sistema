<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano TDD task-by-task da F1 (piloto de handoff de sessao — especialista quente gestor-recebimento)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-28
-->

# F1 — Piloto de Handoff de Sessão (especialista quente) — Implementation Plan

> **Papel:** plano executável (TDD task-by-task, flag-OFF, shadow-first) da F1 — piloto de handoff de sessão para o especialista quente `gestor-recebimento`, derivado da spec `docs/superpowers/specs/2026-06-28-handoff-sessao-agente-custo-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Indice

- [Goal / Architecture / Tech Stack](#goal)
- [Global Constraints](#global-constraints)
- [File Structure](#file-structure)
- [Task 1: Feature flag + resolver de modo](#task-1-feature-flag--resolver-de-modo)
- [Task 2: agent_router — decisão de papel por turno (puro)](#task-2-agent_router--decisão-de-papel-por-turno-puro)
- [Task 3: Pool multi-papel — PooledClient.role + chave composta](#task-3-pool-multi-papel--pooledclientrole--chave-composta)
- [Task 4: Estado agente_ativo em AgentSession.data (R7)](#task-4-estado-agente_ativo-em-agentsessiondata-r7)
- [Task 5: Handoff magro — builder + guard de orçamento](#task-5-handoff-magro--builder--guard-de-orçamento)
- [Task 6: Tools MCP transferir_para / devolver_ao_principal](#task-6-tools-mcp-transferir_para--devolver_ao_principal)
- [Task 7: Cliente especialista + integração no route (shadow-first)](#task-7-cliente-especialista--integração-no-route-shadow-first)
- [Task 8: Executor atômico (subagente dedicado) + prova de invariantes](#task-8-executor-atômico-subagente-dedicado--prova-de-invariantes)
- [Task 9: Gate de métrica (custo/sessão + cache_read antes/depois)](#task-9-gate-de-métrica-custosessão--cache_read-antesdepois)
- [Rollout](#rollout-pós-implementação-fora-do-código--requer-aval)
- [Self-Review](#self-review)
- [Execução](#execução)

## Goal

**Goal:** Pôr em produção, atrás de flag (off→shadow→on→admin), o handoff de sessão para UM especialista quente (`gestor-recebimento`): o principal promove a sessão a um cliente SDK persistente que conduz o assunto e mantém contexto; o ato irreversível vai a um executor atômico (Task one-shot) chamado pelo próprio especialista.

**Architecture:** Camada de aplicação, sem mudar o SDK. (1) Pool multi-papel (`client_pool.py` ganha `role`); (2) `agent_router.py` (irmão do `model_router.py`) decide qual papel atende a mensagem, estado em `AgentSession.data['agente_ativo']`; (3) tools MCP `transferir_para`/`devolver_ao_principal` (handoff magro <10k tok); (4) executor atômico = subagente dedicado chamado pelo especialista só para `--confirmar`; (5) reversão; (6) memória de trabalho via `get_subagent_findings` (ligado na F0). Tudo gated; shadow-first com gate de métrica antes de `on`.

**Tech Stack:** Python 3.12 · Flask 3.1 · Flask-SQLAlchemy 3.1 (JSONB `AgentSession.data`) · claude-agent-sdk 0.2.101 (`ClaudeSDKClient` persistente, `@enhanced_tool` MCP in-process) · pytest. Pool roda num event loop daemon dedicado (`submit_coroutine`).

## Global Constraints

> Copiados verbatim da spec §Invariantes e do `app/agente/CLAUDE.md`. Valem para TODA task.

- **Dry-run default + R11/R12 + gate `permissions.py` por-nome-de-skill {1,55} + audit hook R9** — INTACTOS no executor atômico. `permissions.py` NÃO muda (executor herda `can_use_tool` idêntico via ContextVar). (`permissions.py:498-1032`, fail-closed `1021-1032`.)
- **R7 JSONB:** toda escrita em `AgentSession.data[...]` exige `flag_modified(session, 'data')` num app_context que comita, senão a mudança é silenciosamente perdida. (`chat.py:2240-2265`.)
- **R1 dois ids:** `session_id` (nosso UUID, coluna) ≠ `sdk_session_id` (efêmero CLI, em `data` JSONB). Handoff reusa `session_id`; cada papel tem seu próprio `sdk_session_id`. Nunca confundir.
- **Model stickiness:** `PooledClient.model` é decidido 1x e NUNCA muda (cache MODEL-SCOPED; bug 2026-06-15). Cada `(session_id, role)` tem seu próprio cache; trocar de papel = **1 cache-write por troca** (aceito), por isso handoff magro (<10k tok) é obrigatório.
- **Governança do prompt (FASE 5):** qualquer novo `prompts/*.md` ou mudança em listing/skills do agente passa por `scripts/audits/prompt_size_audit.py --check-delta` (pre-commit bloqueia crescimento). Crescimento consciente: `--update-baseline && --update-claude-md` no mesmo commit. Aplicar checklist PAD-CTX (`.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md`).
- **Teams export:** mudança em `client.py`/`permissions.py`/`feature_flags.py`/`models.py`/`session_persistence.py`/`pending_questions.py` DEVE ser testada no Teams. As tasks abaixo que tocam `client.py`/`feature_flags.py`/`models.py` incluem nota Teams.
- **Defesa em profundidade:** toda alteração de roteamento de custo no web só vale na **1ª msg de sessão fria** (sessão quente usa `pick_warm_model`, não roteia — `chat.py:165-199`). O agent_router é decidido **1x por turno** no início (cliente fixo no turno, troca no próximo).
- **Piloto = UM especialista (`gestor-recebimento`).** Nenhum SEFAZ/faturar no piloto. Flag default `off`. Nada em produção sem aval.

**Convenção de chave de pool:** `_pool_key(session_id, role) = f"{session_id}::{role}"` (string, retrocompatível com o `_registry: Dict[str, PooledClient]` atual; `role='principal'` reproduz o comportamento de hoje com sufixo `::principal`).

---

## File Structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `app/agente/config/feature_flags.py` | Flag + resolver `resolve_specialist_handoff_mode()` (off/shadow/on/admin) | Modificar (~L1300 região resolvers) |
| `app/agente/sdk/agent_router.py` | Decide papel por turno: `select_specialist()` + `log_specialist_decision()` (irmão do `model_router.py`) | **Criar** |
| `app/agente/sdk/handoff_context.py` | `build_handoff_context()` + guard de orçamento (<10k tok) | **Criar** |
| `app/agente/sdk/client_pool.py` | `PooledClient.role` + `_pool_key()` + `role=` em get/create/disconnect/touch | Modificar (126-151, 159, 305-561) |
| `app/agente/models.py` | Helpers `set_agente_ativo()`/`get_agente_ativo()` em `AgentSession` (R7) | Modificar (classe AgentSession) |
| `app/agente/sdk/specialist_profiles.py` | Registro de perfis (role→prompt+skills); piloto `gestor-recebimento` | **Criar** |
| `app/agente/prompts/especialista_recebimento.md` | System prompt do especialista quente | **Criar** |
| `app/agente/tools/handoff_mcp_tool.py` | Tools `transferir_para` + `devolver_ao_principal` (@enhanced_tool) | **Criar** |
| `app/agente/sdk/client.py` | `_build_options(..., specialist_profile=None)` + registro condicional do handoff_server | Modificar (1516, 1880-1889, 2019-2034) |
| `app/agente/routes/chat.py` | Integração: agent_router + provisão do cliente especialista + persistência `agente_ativo` | Modificar (L199-200 gap, L165-172) |
| `.claude/agents/executor-recebimento-nfpo.md` | Executor atômico (subagente dedicado, tools apertadas) | **Criar** |
| `app/agente/services/specialist_handoff_metrics.py` | Gate de métrica: custo/sessão + cache_read ratio antes/depois | **Criar** |
| `tests/agente/sdk/test_*` etc. | Testes por task | **Criar** |

**Ordem:** T1→T6 são unidades puras/testáveis (seguras, sem efeito em prod com flag off). T7→T8 são integração gated (shadow-first). T9 é medição (pré-requisito do gate `on`).

---

### Task 1: Feature flag + resolver de modo

**Files:**
- Modify: `app/agente/config/feature_flags.py` (região de resolvers, ~L1300)
- Test: `tests/agente/config/test_specialist_handoff_flag.py`

**Interfaces:**
- Produces: `resolve_specialist_handoff_mode(is_admin: bool = False) -> str` → `'off'|'shadow'|'on'`. Espelha `resolve_subagent_checkpoint_mode` (`feature_flags.py:1300-1319`).

**Nota Teams:** `feature_flags.py` é export-crítico — rodar a suíte Teams ao final (Step 6).

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/config/test_specialist_handoff_flag.py
from unittest.mock import patch
import app.agente.config.feature_flags as ff


def _resolve(env, is_admin=False):
    with patch.dict('os.environ', env, clear=False):
        return ff.resolve_specialist_handoff_mode(is_admin=is_admin)


def test_default_off():
    # clear=True garante env limpo (CI pode ter AGENT_SPECIALIST_HANDOFF setado).
    with patch.dict('os.environ', {}, clear=True):
        assert ff.resolve_specialist_handoff_mode() == 'off'

def test_shadow_e_on_literais():
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'shadow'}) == 'shadow'
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'on'}) == 'on'

def test_valor_invalido_cai_para_off():
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'banana'}) == 'off'

def test_admin_e_on_para_admin_shadow_para_demais():
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'admin'}, is_admin=True) == 'on'
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'admin'}, is_admin=False) == 'shadow'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/config/test_specialist_handoff_flag.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'resolve_specialist_handoff_mode'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agente/config/feature_flags.py — adicionar junto aos outros resolvers (~L1320)
_SPECIALIST_HANDOFF_VALID = {"off", "shadow", "on", "admin"}

def resolve_specialist_handoff_mode(is_admin: bool = False) -> str:
    """Resolve o modo do PILOTO de handoff de sessao (F1 — especialista quente).

    Spec: docs/superpowers/specs/2026-06-28-handoff-sessao-agente-custo-design.md.
    Lido FRESH do env (rollout sem redeploy). Default OFF (de-risking).
        off    -> nada (comportamento atual; subagente efemero por turno)
        shadow -> agent_router DECIDE + loga, mas NAO troca o cliente ativo
        on     -> handoff real (troca para o especialista quente)
        admin  -> "on" para admin (canary), "shadow" para os demais
    """
    raw = os.getenv("AGENT_SPECIALIST_HANDOFF", "off").strip().lower()
    if raw not in _SPECIALIST_HANDOFF_VALID:
        return "off"
    if raw == "admin":
        return "on" if is_admin else "shadow"
    return raw  # off | shadow | on
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/config/test_specialist_handoff_flag.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/agente/config/feature_flags.py tests/agente/config/test_specialist_handoff_flag.py
git commit -m "feat(agente): flag AGENT_SPECIALIST_HANDOFF + resolver (F1 T1)"
```

- [ ] **Step 6: Teams regression**

Run: `python -m pytest tests/teams/ -q` → Expected: all pass (flag aditiva, default off).

---

### Task 2: agent_router — decisão de papel por turno (puro)

**Files:**
- Create: `app/agente/sdk/agent_router.py`
- Test: `tests/agente/sdk/test_agent_router.py`

**Interfaces:**
- Consumes: nada (função pura).
- Produces:
  - `select_specialist(message: str, current_active: str = 'principal', word_limit: int = 15) -> tuple[str, str]` → `(role, reason)`. `role ∈ {'principal','gestor-recebimento'}`.
  - `log_specialist_decision(session_id, user_id, prompt_preview, role, reason) -> None` (espelha `model_router.log_routing_decision`).

**Princípio (conservador, R-EXEC-6):** só entra no especialista em frase clara de recebimento; mantém o especialista em continuação curta; **sai** (reversão) em sinal de outro domínio. Na dúvida → `principal`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/sdk/test_agent_router.py
from app.agente.sdk.agent_router import select_specialist


def test_frase_de_recebimento_entra_no_especialista():
    role, reason = select_specialist("vincular o pedido C2615437 na nota 48862 pelo odoo")
    assert role == "gestor-recebimento"
    assert reason == "padrao_recebimento"

def test_continuacao_curta_mantem_especialista():
    role, reason = select_specialist("e a 48863?", current_active="gestor-recebimento")
    assert role == "gestor-recebimento"
    assert reason == "continuacao"

def test_sinal_de_outro_dominio_reverte_ao_principal():
    role, reason = select_specialist(
        "qual a margem de custeio do palmito?", current_active="gestor-recebimento")
    assert role == "principal"
    assert reason == "reversao_outro_dominio"

def test_default_principal_quando_nao_ha_sinal():
    role, reason = select_specialist("bom dia, tudo bem?")
    assert role == "principal"
    assert reason == "default"

def test_prompt_complexo_longo_fica_no_principal_mesmo_com_keyword():
    msg = ("preciso entender a politica de vinculacao de nota com pedido, comparar "
           "tolerancias, revisar premissas fiscais e decidir a estrategia geral aqui")
    role, reason = select_specialist(msg)
    assert role == "principal"
    assert reason == "prompt_complexo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/sdk/test_agent_router.py -q`
Expected: FAIL — `ModuleNotFoundError: app.agente.sdk.agent_router`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agente/sdk/agent_router.py
"""Agent Router — decide qual PAPEL (principal vs especialista quente) atende o turno.

Irmao do model_router.py. F1 piloto: unico especialista = 'gestor-recebimento'.
Decisao 1x por turno no inicio (cliente fixo no turno). Conservador (R-EXEC-6):
so' entra no especialista em frase clara de recebimento; mantem em continuacao
curta; sai (reversao) em sinal de outro dominio; default principal.
"""
from __future__ import annotations
import logging
import re

logger = logging.getLogger(__name__)

PILOT_SPECIALIST = "gestor-recebimento"

# Frase de recebimento (vinculacao/conciliacao/match NF x PO). Ancorada nos
# padroes reais (model_router padrao_nf_po + vinculacao_fastpath).
_RE_RECEBIMENTO = re.compile(
    r"\b(vincul\w+|desvincul\w+|conciliar?|consolidar?|split)\b.*\b(nota|nf|pedido|po)\b"
    r"|\bmatch\s+(da\s+)?nf\b|\bnota\s+\d+\b.*\bpedido\b|\bpedido\s+\S+\b.*\bnota\s+\d+\b",
    re.IGNORECASE)

# Sinais de OUTRO dominio (reversao do especialista de recebimento).
_RE_OUTRO_DOMINIO = re.compile(
    r"\b(margem|custeio|frete|cota[cç][aã]o|estoque|ruptura|carteira|separa[cç][aã]o|"
    r"embarque|entrega|canhoto|devolu[cç][aã]o|sped|faturar?|sefaz)\b",
    re.IGNORECASE)


def select_specialist(message: str, current_active: str = "principal",
                      word_limit: int = 15) -> tuple[str, str]:
    if not message or not message.strip():
        return "principal", "empty"
    stripped = message.strip()
    words = len(stripped.split())

    # Frase clara de recebimento entra/permanece no especialista — MAS guard de
    # complexidade: pergunta longa/estrategica fica no principal (espelha
    # model_router prompt_complexo, >15 palavras).
    if _RE_RECEBIMENTO.search(stripped):
        if words > word_limit:
            return "principal", "prompt_complexo"
        return PILOT_SPECIALIST, "padrao_recebimento"

    # Ja' dentro do especialista: continuacao curta mantem; outro dominio reverte.
    if current_active == PILOT_SPECIALIST:
        if _RE_OUTRO_DOMINIO.search(stripped):
            return "principal", "reversao_outro_dominio"
        if words <= 6:
            return PILOT_SPECIALIST, "continuacao"
        return "principal", "reversao_assunto_amplo"

    return "principal", "default"


def log_specialist_decision(session_id, user_id, prompt_preview, role, reason) -> None:
    preview = (prompt_preview or "")[:80].replace("\n", " ")
    logger.info(
        f"[AGENT_ROUTER] session={(session_id or '')[:12]} user={user_id} "
        f"role={role} reason={reason} preview=\"{preview}\"")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/sdk/test_agent_router.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/agent_router.py tests/agente/sdk/test_agent_router.py
git commit -m "feat(agente): agent_router select_specialist conservador (F1 T2)"
```

---

### Task 3: Pool multi-papel — PooledClient.role + chave composta

**Files:**
- Modify: `app/agente/sdk/client_pool.py` (PooledClient 126-151; `_registry` 159; `get_or_create_client` 305; `get_pooled_client` 549; `disconnect_client` 448; `touch_client` 639; cleanup 589-636; shutdown 701-751)
- Test: `tests/agente/sdk/test_client_pool_roles.py`

**Interfaces:**
- Consumes: nada novo.
- Produces:
  - `PooledClient.role: str = 'principal'` (novo field).
  - `_pool_key(session_id: str, role: str = 'principal') -> str` → `f"{session_id}::{role}"`.
  - `get_pooled_client(session_id, role='principal')`, `get_or_create_client(session_id, options, user_id=0, role='principal')`, `disconnect_client(session_id, role='principal')`, `touch_client(session_id, role='principal')` — todas retrocompatíveis (default `'principal'`).

**Gotcha (map):** o `_cleanup_idle_clients`/`shutdown` iteram `_registry`; com chave string composta a iteração continua válida (chave string), mas `disconnect_client` precisa ser chamado com a chave composta — adaptar usando os FIELDS do próprio `PooledClient` (`.session_id`, `.role`) ao desconectar no cleanup, não a chave.

**Nota Teams:** `client_pool.py` não está na lista export-crítica, mas é usado pelo path persistente do Teams — rodar Teams ao final.

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/sdk/test_client_pool_roles.py
from app.agente.sdk import client_pool as cp


def test_pool_key_compoe_session_e_role():
    assert cp._pool_key("sess-1", "principal") == "sess-1::principal"
    assert cp._pool_key("sess-1", "gestor-recebimento") == "sess-1::gestor-recebimento"

def test_pool_key_default_principal():
    assert cp._pool_key("sess-1") == "sess-1::principal"

def test_pooled_client_tem_role_default_principal():
    pc = cp.PooledClient(client=object(), session_id="s")
    assert pc.role == "principal"

def test_get_pooled_client_isola_por_papel():
    cp._registry.clear()
    principal = cp.PooledClient(client=object(), session_id="s", role="principal")
    especialista = cp.PooledClient(client=object(), session_id="s", role="gestor-recebimento")
    with cp._registry_lock:
        cp._registry[cp._pool_key("s", "principal")] = principal
        cp._registry[cp._pool_key("s", "gestor-recebimento")] = especialista
    assert cp.get_pooled_client("s", role="principal") is principal
    assert cp.get_pooled_client("s", role="gestor-recebimento") is especialista
    assert cp.get_pooled_client("s") is principal  # retrocompat
    cp._registry.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/sdk/test_client_pool_roles.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute '_pool_key'` (e `PooledClient(...).role`).

- [ ] **Step 3: Write minimal implementation**

```python
# client_pool.py — no PooledClient dataclass, apos `model: Optional[str] = None` (L151):
    role: str = "principal"

# client_pool.py — helper de chave (apos definicao de _registry, ~L161):
def _pool_key(session_id: str, role: str = "principal") -> str:
    """Chave composta do registry/creation_locks (retrocompat: role default)."""
    return f"{session_id}::{role}"
```

Em seguida, adaptar (sem mudar a lógica interna, só a chave e a assinatura):

```python
# get_pooled_client (L549) — adicionar role e usar _pool_key:
def get_pooled_client(session_id: str, role: str = "principal") -> Optional[PooledClient]:
    with _registry_lock:
        return _registry.get(_pool_key(session_id, role))

# get_or_create_client (L305) — assinatura: ... user_id: int = 0, role: str = "principal"
#   trocar TODOS os _registry[...] / _registry.get(...) / _get_creation_lock(...) por
#   _pool_key(session_id, role); ao criar PooledClient(...) passar role=role.
# disconnect_client (L448) — assinatura: (session_id, role="principal"); usar
#   _registry.pop(_pool_key(session_id, role), None).
# touch_client (L639) — (session_id, role="principal"); lookup via _pool_key.
# _get_creation_lock (L290) — (session_id, role="principal"); dict keyed por _pool_key.
```

```python
# _cleanup_idle_clients (L589-636) e shutdown_pool (L701-751): a iteracao
# `for key in list(_registry.keys())` continua valida (chave string). Ao
# desconectar dentro do loop, usar os FIELDS do PooledClient, nao a chave:
#   pooled = _registry.get(key)
#   ...  # mesma logica de idle/lock
#   await disconnect_client(pooled.session_id, role=pooled.role)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/sdk/test_client_pool_roles.py tests/agente/sdk/test_client_pool.py tests/agente/sdk/test_client_pool_creation_lock.py -q`
Expected: PASS (novos + os 2 de regressão do pool seguem verdes).

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/client_pool.py tests/agente/sdk/test_client_pool_roles.py
git commit -m "feat(agente): pool multi-papel (PooledClient.role + chave composta) (F1 T3)"
```

- [ ] **Step 6: Teams regression** — `python -m pytest tests/teams/ -q` → all pass.

---

### Task 4: Estado agente_ativo em AgentSession.data (R7)

**Files:**
- Modify: `app/agente/models.py` (classe `AgentSession`)
- Test: `tests/agente/models/test_agente_ativo_state.py`

**Interfaces:**
- Produces (métodos de instância de `AgentSession`):
  - `get_agente_ativo(self) -> str` → `data.get('agente_ativo', 'principal')`.
  - `set_agente_ativo(self, role: str) -> None` → grava `data['agente_ativo']` + `flag_modified(self, 'data')` (caller comita).

**Nota Teams:** `models.py` é export-crítico — rodar Teams ao final.

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/models/test_agente_ativo_state.py
from app import db
from app.agente.models import AgentSession


def test_default_principal_quando_ausente(app):
    with app.app_context():
        s = AgentSession(session_id='t-ativo-1', user_id=1, data={})
        assert s.get_agente_ativo() == 'principal'

def test_set_persiste_com_flag_modified(app):
    with app.app_context():
        s = AgentSession(session_id='t-ativo-2', user_id=1, data={})
        db.session.add(s)
        s.set_agente_ativo('gestor-recebimento')
        db.session.commit()
    with app.app_context():
        r = AgentSession.query.filter_by(session_id='t-ativo-2').first()
        assert r.get_agente_ativo() == 'gestor-recebimento'
        AgentSession.query.filter_by(session_id='t-ativo-2').delete()
        db.session.commit()

def test_set_preserva_outras_chaves_de_data(app):
    with app.app_context():
        s = AgentSession(session_id='t-ativo-3', user_id=1,
                         data={'sdk_session_id': 'abc', 'messages': [1, 2]})
        s.set_agente_ativo('gestor-recebimento')
        assert s.data['sdk_session_id'] == 'abc'
        assert s.data['messages'] == [1, 2]
        assert s.data['agente_ativo'] == 'gestor-recebimento'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/models/test_agente_ativo_state.py -q`
Expected: FAIL — `AttributeError: 'AgentSession' object has no attribute 'get_agente_ativo'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agente/models.py — dentro da classe AgentSession (junto aos outros helpers de data):
    def get_agente_ativo(self) -> str:
        """Papel ativo no handoff de sessao (F1). 'principal' por default."""
        return (self.data or {}).get('agente_ativo', 'principal')

    def set_agente_ativo(self, role: str) -> None:
        """Grava o papel ativo em data['agente_ativo'] (R7 flag_modified).
        Preserva o restante de data. Caller comita no app_context."""
        from sqlalchemy.orm.attributes import flag_modified
        _data = self.data or {}
        _data['agente_ativo'] = role
        self.data = _data
        flag_modified(self, 'data')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/models/test_agente_ativo_state.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/agente/models.py tests/agente/models/test_agente_ativo_state.py
git commit -m "feat(agente): AgentSession.get/set_agente_ativo (R7) (F1 T4)"
```

- [ ] **Step 6: Teams regression** — `python -m pytest tests/teams/ -q` → all pass.

---

### Task 5: Handoff magro — builder + guard de orçamento

**Files:**
- Create: `app/agente/sdk/handoff_context.py`
- Test: `tests/agente/sdk/test_handoff_context.py`

**Interfaces:**
- Produces:
  - `estimate_tokens(text: str) -> int` → `ceil(len(text) / 3.5)` (heurística pt-BR já usada em `prompt_size_audit.py`).
  - `build_handoff_context(objetivo: str, entidades: dict, saldo: dict | None = None, max_tokens: int = 10000) -> dict` → `{'objetivo', 'entidades', 'saldo', 'tokens_estimados', 'truncado': bool}`. Se exceder `max_tokens`, trunca `entidades`/`saldo` para caber e marca `truncado=True` (NUNCA a conversa inteira — só dados resolvidos).
  - `render_handoff_block(ctx: dict) -> str` → bloco `<handoff_context>...</handoff_context>` para injeção no especialista.

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/sdk/test_handoff_context.py
from app.agente.sdk.handoff_context import (
    estimate_tokens, build_handoff_context, render_handoff_block)


def test_estimate_tokens_heuristica():
    assert estimate_tokens("a" * 350) == 100

def test_build_inclui_campos_e_conta_tokens():
    ctx = build_handoff_context(
        objetivo="vincular NF 48862 ao PO C2615437",
        entidades={"nf": "48862", "po": "C2615437"},
        saldo={"validacao_id": 991})
    assert ctx["objetivo"].startswith("vincular")
    assert ctx["entidades"]["nf"] == "48862"
    assert ctx["saldo"]["validacao_id"] == 991
    assert ctx["tokens_estimados"] > 0
    assert ctx["truncado"] is False

def test_build_trunca_quando_excede_orcamento():
    grande = {f"k{i}": "x" * 500 for i in range(200)}  # ~28k tokens
    ctx = build_handoff_context(objetivo="obj", entidades=grande, max_tokens=2000)
    assert ctx["truncado"] is True
    assert len(ctx["entidades"]) < len(grande)   # removeu de fato (nao so' flag)
    assert ctx["tokens_estimados"] <= 2000

def test_render_block_envelopa_em_tag():
    ctx = build_handoff_context(objetivo="obj", entidades={"nf": "1"})
    bloco = render_handoff_block(ctx)
    assert bloco.startswith("<handoff_context>")
    assert bloco.rstrip().endswith("</handoff_context>")
    assert "obj" in bloco
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/sdk/test_handoff_context.py -q`
Expected: FAIL — `ModuleNotFoundError: app.agente.sdk.handoff_context`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agente/sdk/handoff_context.py
"""Handoff magro: empacota o MINIMO p/ o especialista quente assumir (entidades
resolvidas, saldo, objetivo) — NUNCA a conversa inteira. Guard de orcamento
<10k tok (a conversa fica no cliente especialista que herda a sessao SDK)."""
from __future__ import annotations
import json
import math


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text or "") / 3.5)


def _ctx_tokens(objetivo, entidades, saldo) -> int:
    blob = json.dumps({"objetivo": objetivo, "entidades": entidades,
                       "saldo": saldo}, ensure_ascii=False, default=str)
    return estimate_tokens(blob)


def build_handoff_context(objetivo: str, entidades: dict,
                          saldo: dict | None = None, max_tokens: int = 10000) -> dict:
    entidades = dict(entidades or {})
    saldo = dict(saldo or {}) if saldo else None
    truncado = False
    # Trunca dados resolvidos (NUNCA o objetivo) ate caber no orcamento.
    while _ctx_tokens(objetivo, entidades, saldo) > max_tokens:
        truncado = True
        if saldo:
            saldo.popitem()
            if not saldo:
                saldo = None
            continue
        if entidades:
            entidades.popitem()
            continue
        break
    return {
        "objetivo": objetivo,
        "entidades": entidades,
        "saldo": saldo,
        "tokens_estimados": _ctx_tokens(objetivo, entidades, saldo),
        "truncado": truncado,
    }


def render_handoff_block(ctx: dict) -> str:
    corpo = json.dumps({k: ctx.get(k) for k in ("objetivo", "entidades", "saldo")},
                       ensure_ascii=False, default=str)
    return ("<handoff_context>\n"
            "Contexto de sistema (nao e instrucao do usuario): voce assumiu este "
            "assunto como especialista. Os dados resolvidos abaixo ja foram apurados "
            "pelo principal — parta deles, nao redescubra.\n"
            f"{corpo}\n"
            "</handoff_context>")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/sdk/test_handoff_context.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/handoff_context.py tests/agente/sdk/test_handoff_context.py
git commit -m "feat(agente): handoff magro builder + guard de orcamento (F1 T5)"
```

---

### Task 6: Tools MCP transferir_para / devolver_ao_principal

**Files:**
- Create: `app/agente/tools/handoff_mcp_tool.py`
- Test: `tests/agente/tools/test_handoff_mcp_tool.py`

**Interfaces:**
- Consumes: `AgentSession.set_agente_ativo` (T4), `build_handoff_context` (T5), `permissions.get_current_session_id`.
- Produces:
  - `handoff_server` (McpSdkServerConfig de `create_enhanced_mcp_server('handoff', tools=[...])`).
  - `_apply_transfer(session_id, especialista, objetivo, entidades, saldo) -> dict` (lógica pura testável: persiste `agente_ativo` + `data['handoff_context']`).
  - `_apply_devolver(session_id) -> dict` (seta `agente_ativo='principal'`, limpa `handoff_context`).

**Padrão (map):** espelha `resolver_mcp_tool.py:70-96` (imports, `@enhanced_tool`, `create_enhanced_mcp_server`). **GOTCHA crítico (review):** a tool MCP é invocada na thread daemon do SDK, FORA do Flask app_context — `_apply_*` DEVE encapsular o acesso ao DB num `_app_context()` (probe `current_app`→`nullcontext`, senão `create_app().app_context()`), espelhando `subagent_checkpoint._app_context()`. Sem isso, `db.session.commit()` explode (ou perde a escrita) em produção, embora o teste passe (roda dentro de `app.app_context()`).

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/tools/test_handoff_mcp_tool.py
from app import db
from app.agente.models import AgentSession
from app.agente.tools.handoff_mcp_tool import _apply_transfer, _apply_devolver, handoff_server


def test_handoff_server_registra_duas_tools():
    assert handoff_server is not None

def test_apply_transfer_persiste_ativo_e_contexto(app):
    with app.app_context():
        db.session.add(AgentSession(session_id='hx-1', user_id=1, data={}))
        db.session.commit()
        out = _apply_transfer('hx-1', 'gestor-recebimento',
                              objetivo='vincular NF 48862 ao PO C2615437',
                              entidades={'nf': '48862', 'po': 'C2615437'}, saldo=None)
        assert out['ok'] is True
        r = AgentSession.query.filter_by(session_id='hx-1').first()
        assert r.get_agente_ativo() == 'gestor-recebimento'
        assert r.data['handoff_context']['entidades']['nf'] == '48862'
        AgentSession.query.filter_by(session_id='hx-1').delete()
        db.session.commit()

def test_apply_transfer_sem_sessao_retorna_erro(app):
    with app.app_context():
        out = _apply_transfer('nao-existe', 'gestor-recebimento', objetivo='x', entidades={})
        assert out['ok'] is False

def test_apply_devolver_volta_ao_principal(app):
    with app.app_context():
        s = AgentSession(session_id='hx-2', user_id=1,
                         data={'agente_ativo': 'gestor-recebimento',
                               'handoff_context': {'objetivo': 'x'}})
        db.session.add(s)
        db.session.commit()
        out = _apply_devolver('hx-2')
        assert out['ok'] is True
        r = AgentSession.query.filter_by(session_id='hx-2').first()
        assert r.get_agente_ativo() == 'principal'
        assert 'handoff_context' not in (r.data or {})
        AgentSession.query.filter_by(session_id='hx-2').delete()
        db.session.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/tools/test_handoff_mcp_tool.py -q`
Expected: FAIL — `ModuleNotFoundError: app.agente.tools.handoff_mcp_tool`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agente/tools/handoff_mcp_tool.py
"""Tools MCP de handoff de sessao (F1): transferir_para + devolver_ao_principal.
Espelha resolver_mcp_tool.py. So' registradas se AGENT_SPECIALIST_HANDOFF != off."""
from __future__ import annotations
import logging
from sqlalchemy.orm.attributes import flag_modified

from contextlib import nullcontext

from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

logger = logging.getLogger(__name__)


def _app_context():
    """Hooks/handlers MCP async do SDK rodam FORA do Flask app_context (thread
    daemon do pool). Sem isto, AgentSession.query / db.session.commit() explodem
    com RuntimeError('Working outside of application context'). Reusa o atual se
    existir, senao cria um. Mesmo padrao de subagent_checkpoint._app_context()."""
    try:
        from flask import current_app as _probe
        _ = _probe.name
        return nullcontext()
    except RuntimeError:
        from app import create_app
        return create_app().app_context()


def _apply_transfer(session_id, especialista, objetivo, entidades, saldo=None) -> dict:
    from app import db
    from app.agente.models import AgentSession
    from app.agente.sdk.handoff_context import build_handoff_context
    with _app_context():
        s = AgentSession.query.filter_by(session_id=session_id).first()
        if not s:
            return {"ok": False, "erro": "sessao_nao_encontrada"}
        ctx = build_handoff_context(objetivo=objetivo, entidades=entidades, saldo=saldo)
        s.set_agente_ativo(especialista)
        _data = s.data or {}
        _data['handoff_context'] = ctx
        s.data = _data
        flag_modified(s, 'data')
        db.session.commit()
        logger.info(f"[HANDOFF] transfer -> {especialista} session={session_id[:12]} "
                    f"tokens={ctx['tokens_estimados']} truncado={ctx['truncado']}")
        return {"ok": True, "especialista": especialista,
                "tokens": ctx["tokens_estimados"]}


def _apply_devolver(session_id) -> dict:
    from app import db
    from app.agente.models import AgentSession
    with _app_context():
        s = AgentSession.query.filter_by(session_id=session_id).first()
        if not s:
            return {"ok": False, "erro": "sessao_nao_encontrada"}
        s.set_agente_ativo('principal')
        _data = s.data or {}
        _data.pop('handoff_context', None)
        s.data = _data
        flag_modified(s, 'data')
        db.session.commit()
        logger.info(f"[HANDOFF] devolver -> principal session={session_id[:12]}")
        return {"ok": True}


@enhanced_tool(
    name="transferir_para",
    description=("Transfere a conducao do assunto para um especialista quente "
                "(piloto: gestor-recebimento), passando um handoff MAGRO "
                "(entidades/saldo/objetivo, NUNCA a conversa). Use quando o "
                "assunto e' recebimento (vincular/conciliar NF x PO) e exige "
                "dialogo continuo no dominio."),
    input_schema={"type": "object", "required": ["especialista", "objetivo"],
                  "additionalProperties": False,
                  "properties": {
                      "especialista": {"type": "string", "enum": ["gestor-recebimento"]},
                      "objetivo": {"type": "string"},
                      "entidades": {"type": "object"},
                      "saldo": {"type": "object"}}},
)
async def transferir_para(args: dict) -> dict:
    from app.agente.config.permissions import get_current_session_id
    sid = get_current_session_id()
    out = _apply_transfer(sid, args["especialista"], args["objetivo"],
                          args.get("entidades") or {}, args.get("saldo"))
    return {"content": [{"type": "text", "text": str(out)}], "structuredContent": out}


@enhanced_tool(
    name="devolver_ao_principal",
    description=("Devolve a conducao ao agente principal quando o assunto sai do "
                "escopo do especialista. Limpa o handoff_context."),
    input_schema={"type": "object", "additionalProperties": False, "properties": {}},
)
async def devolver_ao_principal(args: dict) -> dict:
    from app.agente.config.permissions import get_current_session_id
    out = _apply_devolver(get_current_session_id())
    return {"content": [{"type": "text", "text": str(out)}], "structuredContent": out}


handoff_server = create_enhanced_mcp_server(
    "handoff", version="1.0.0", tools=[transferir_para, devolver_ao_principal])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/tools/test_handoff_mcp_tool.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Register no `_build_options` (condicional sob flag)**

Em `app/agente/sdk/client.py`, na região de registro de MCP servers (padrão `ontology` ~L2019-2033, antes de `return ClaudeAgentOptions`):

```python
        # Handoff de sessao (F1) — so' registra a tool no PRINCIPAL e fora de 'off'.
        try:
            from ..config.feature_flags import resolve_specialist_handoff_mode
            if resolve_specialist_handoff_mode() != 'off' and specialist_profile is None:
                from ..tools.handoff_mcp_tool import handoff_server
                _register_mcp('handoff', handoff_server)
        except Exception as _h_err:
            logger.debug(f"[handoff] registro da tool pulado: {_h_err}")
```

> `specialist_profile` é o parâmetro adicionado na Task 7 (o principal o recebe `None`; o especialista NÃO expõe `transferir_para` — ele usa o executor atômico, não re-delega).

- [ ] **Step 6: Commit**

```bash
git add app/agente/tools/handoff_mcp_tool.py app/agente/sdk/client.py tests/agente/tools/test_handoff_mcp_tool.py
git commit -m "feat(agente): tools handoff transferir_para/devolver + registro gated (F1 T6)"
```

- [ ] **Step 7: Teams regression** — `client.py` export-crítico: `python -m pytest tests/teams/ -q` → all pass.

---

### Task 7: Cliente especialista + integração no route (shadow-first)

**Files:**
- Create: `app/agente/sdk/specialist_profiles.py`
- Create: `app/agente/prompts/especialista_recebimento.md`
- Modify: `app/agente/sdk/client.py` (`_build_options` 1516 — param `specialist_profile`)
- Modify: `app/agente/routes/chat.py` (gap L199-200; provisão de cliente L165-172)
- Test: `tests/agente/sdk/test_specialist_profiles.py`, `tests/agente/routes/test_agent_router_integration.py`

**Interfaces:**
- Consumes: `select_specialist` (T2), pool `role=` (T3), `get_agente_ativo`/`set_agente_ativo` (T4), `resolve_specialist_handoff_mode` (T1).
- Produces:
  - `SpecialistProfile` dataclass `{role: str, system_prompt_path: str, skills: list[str]}`.
  - `SPECIALIST_PROFILES: dict[str, SpecialistProfile]` (piloto: `'gestor-recebimento'` → skills `['validacao-nf-po','conciliando-odoo-po','rastreando-odoo','resolvendo-entidades']`).
  - `_build_options(..., specialist_profile: Optional[SpecialistProfile] = None)` — quando presente, substitui `system_prompt` (lê `system_prompt_path`) e `skills` (allow-list do especialista).
  - `_resolve_agent_role(session_id, message, is_admin=False) -> str` (helper testável extraído do route).

**Modo de operação (gate-respeitando):**
- `off`: nada (já garantido pela flag).
- `shadow`: agent_router DECIDE + `log_specialist_decision` + persiste `agente_ativo` (mede), mas **continua streamando pelo cliente principal**.
- `on`: provisiona/obtém o `PooledClient` do especialista (`role='gestor-recebimento'`) e streama por ele; injeta `render_handoff_block(data['handoff_context'])` no 1º turno.

> **Por que o especialista só é provisionado em sessão fria/handoff explícito:** respeitar model stickiness (Global Constraints). A troca de papel é decidida no início do turno (cliente fixo no turno).

- [ ] **Step 1: Write the failing test (perfil + options)**

```python
# tests/agente/sdk/test_specialist_profiles.py
import os
from app.agente.sdk.specialist_profiles import SPECIALIST_PROFILES, SpecialistProfile


def test_piloto_gestor_recebimento_existe():
    p = SPECIALIST_PROFILES.get("gestor-recebimento")
    assert isinstance(p, SpecialistProfile)
    assert p.role == "gestor-recebimento"
    assert "validacao-nf-po" in p.skills

def test_profile_aponta_para_prompt_existente():
    p = SPECIALIST_PROFILES["gestor-recebimento"]
    assert os.path.exists(p.system_prompt_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/sdk/test_specialist_profiles.py -q`
Expected: FAIL — `ModuleNotFoundError: app.agente.sdk.specialist_profiles`

- [ ] **Step 3: Write minimal implementation (perfil + prompt)**

```python
# app/agente/sdk/specialist_profiles.py
"""Perfis de especialista quente (F1). Piloto: gestor-recebimento."""
from __future__ import annotations
import os
from dataclasses import dataclass, field

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


@dataclass(frozen=True)
class SpecialistProfile:
    role: str
    system_prompt_path: str
    skills: list[str] = field(default_factory=list)


SPECIALIST_PROFILES: dict[str, SpecialistProfile] = {
    "gestor-recebimento": SpecialistProfile(
        role="gestor-recebimento",
        system_prompt_path=os.path.join(_PROMPTS_DIR, "especialista_recebimento.md"),
        skills=["validacao-nf-po", "conciliando-odoo-po", "rastreando-odoo",
                "resolvendo-entidades"],
    ),
}
```

```markdown
<!-- app/agente/prompts/especialista_recebimento.md -->
Você é o **especialista de Recebimento** do agente logístico Nacom Goya, conduzindo
diretamente o assunto de vinculação/conciliação de NF×PO (recebimento de compras).

Você assumiu a conversa via handoff: leia o bloco `<handoff_context>` (entidades/saldo/
objetivo já apurados pelo principal) e **parta dele — não redescubra do zero**. Se houver
findings de execuções anteriores deste assunto, eles chegam no contexto; reaproveite.

Regras:
- Dialogue, diagnostique e confirme com o usuário em DRY-RUN (barato) ANTES de qualquer
  ato irreversível.
- Para o ato irreversível (validar picking, conciliar/split PO com `--confirmar`), chame o
  **executor atômico** (subagente `executor-recebimento-nfpo`) passando os parâmetros já
  resolvidos. O executor recebe pronto, executa `--confirmar` e finaliza numa única invocação.
- Quando o assunto sair de recebimento, chame `devolver_ao_principal`.
- NUNCA pule confirmação; os gates de permissão (R11/R12) e a auditoria (R9) continuam valendo.
```

- [ ] **Step 4: Run perfil test (GREEN)**

Run: `python -m pytest tests/agente/sdk/test_specialist_profiles.py -q` → Expected: PASS (2 passed)

- [ ] **Step 5: `_build_options` aceita `specialist_profile`**

Em `client.py:_build_options` (assinatura L1516) adicionar `specialist_profile: Optional['SpecialistProfile'] = None`. Antes de montar `options_dict['system_prompt']` e `options_dict['skills']`/allowed_tools:

```python
        # F1: se for cliente ESPECIALISTA, troca prompt + skills (allow-list propria).
        _spec_skills = None
        if specialist_profile is not None:
            try:
                with open(specialist_profile.system_prompt_path, 'r', encoding='utf-8') as _f:
                    _spec_prompt = _f.read()
                full_system_prompt = self._build_full_system_prompt(_spec_prompt)
                _spec_skills = sorted(specialist_profile.skills)
            except Exception as _sp_err:
                logger.warning(f"[specialist] profile load falhou, fallback principal: {_sp_err}")
                specialist_profile = None
```

E, onde `skills`/`allowed_tools` são definidos, usar `_spec_skills` quando não-None (o especialista usa **allow-list**, como o agente_lojas — `skills=sorted(...)` no `ClaudeAgentOptions`).

- [ ] **Step 6: Write the failing integration test (shadow decide + persiste)**

```python
# tests/agente/routes/test_agent_router_integration.py
from unittest.mock import patch
from app import db
from app.agente.models import AgentSession
from app.agente.routes.chat import _resolve_agent_role


def test_shadow_decide_e_persiste_mas_nao_troca(app):
    with app.app_context():
        db.session.add(AgentSession(session_id='ari-1', user_id=1, data={}))
        db.session.commit()
        with patch('app.agente.config.feature_flags.resolve_specialist_handoff_mode',
                   return_value='shadow'):
            role_efetivo = _resolve_agent_role(
                session_id='ari-1', message='vincular pedido C1 na nota 48862 pelo odoo',
                is_admin=False)
        assert role_efetivo == 'principal'   # shadow nao troca
        r = AgentSession.query.filter_by(session_id='ari-1').first()
        assert r.get_agente_ativo() == 'gestor-recebimento'   # decisao registrada
        AgentSession.query.filter_by(session_id='ari-1').delete(); db.session.commit()

def test_on_troca_para_especialista(app):
    with app.app_context():
        db.session.add(AgentSession(session_id='ari-2', user_id=1, data={}))
        db.session.commit()
        with patch('app.agente.config.feature_flags.resolve_specialist_handoff_mode',
                   return_value='on'):
            role_efetivo = _resolve_agent_role(
                session_id='ari-2', message='vincular pedido C1 na nota 48862 pelo odoo',
                is_admin=False)
        assert role_efetivo == 'gestor-recebimento'
        AgentSession.query.filter_by(session_id='ari-2').delete(); db.session.commit()
```

- [ ] **Step 7: Run integration test to verify it fails**

Run: `python -m pytest tests/agente/routes/test_agent_router_integration.py -q`
Expected: FAIL — `ImportError: cannot import name '_resolve_agent_role'`

- [ ] **Step 8: Implement `_resolve_agent_role` + wire no `api_chat`**

```python
# app/agente/routes/chat.py — helper testavel (extrai a decisao do route):
def _resolve_agent_role(session_id, message, is_admin=False):
    """F1: decide o papel do turno. Persiste a DECISAO (agente_ativo) sempre que
    fora de 'off' (mede em shadow); retorna o papel EFETIVO (principal em shadow,
    especialista em on). Best-effort: erro -> principal."""
    from app.agente.config.feature_flags import resolve_specialist_handoff_mode
    mode = resolve_specialist_handoff_mode(is_admin=is_admin)
    if mode == 'off':
        return 'principal'
    try:
        from app.agente.models import AgentSession
        from app.agente.sdk.agent_router import select_specialist, log_specialist_decision
        from app import db
        s = AgentSession.query.filter_by(session_id=session_id).first()
        current = s.get_agente_ativo() if s else 'principal'
        role, reason = select_specialist(message, current_active=current)
        log_specialist_decision(session_id, None, message, role, reason)
        if s is not None:
            s.set_agente_ativo(role)   # registra decisao (mede em shadow)
            db.session.commit()
        return role if mode == 'on' else 'principal'   # shadow NAO troca
    except Exception as _ar_err:
        import logging
        logging.getLogger('sistema_fretes').warning(f"[agent_router] falhou: {_ar_err}")
        return 'principal'
```

No `api_chat`, no gap L199-200 (após o model_router, antes do `plan_mode`):

```python
        # F1 agent_router — decide papel (gated). Em 'on', usa cliente especialista.
        agent_role = _resolve_agent_role(session_id, message, is_admin=bool(debug_mode))
```

- [ ] **Step 8a (PRÉ-FLIGHT obrigatório — verificação de costura):** ANTES de costurar o swap, LER `chat.py:600-810` (`_stream_chat_response` / onde `get_pooled_client`+`stream_response` são chamados) e mapear: (i) onde o `PooledClient` é obtido por turno; (ii) onde o `prompt` é montado (para prefixar `render_handoff_block`). Registrar os `arquivo:linha` exatos antes de editar — NÃO inventar o ponto de inserção.

- [ ] **Step 8b: Costura do swap (respeitando model stickiness):** quando `agent_role != 'principal'` (modo `on`): obter o `PooledClient` do papel via `get_or_create_client(session_id, options_especialista, role=agent_role)` (com `specialist_profile=SPECIALIST_PROFILES[agent_role]` no `_build_options`) e streamar por ele; prefixar `render_handoff_block(session.data.get('handoff_context'))` ao prompt SÓ no 1º turno do especialista (quando o cliente daquele papel é recém-criado).

> **Invariante de model stickiness (guarda explícita):** cada `(session_id, role)` tem seu PRÓPRIO `PooledClient` com seu PRÓPRIO `model` fixo (T3). Trocar de papel ≠ rebaixar modelo de um cliente existente — apenas escolhe QUAL cliente quente atende. O `agent_router` conservador (T2: continuação curta mantém, reversão só em domínio claro) **minimiza o thrashing** entre papéis (custo = 1 cache-write por troca real de assunto, aceito pela spec). NUNCA chamar `set_model` no cliente do papel; o `model` do `PooledClient` é imutável (T3 / bug 2026-06-15).
> **Teste de costura (adicionar quando o ponto exato for conhecido no 8a):** um teste de integração que prove que, dentro do MESMO turno, o cliente do papel não tem o `model` alterado (stickiness) e que o `render_handoff_block` só é prefixado uma vez (1º turno do especialista).

- [ ] **Step 9: Run integration tests (GREEN)**

Run: `python -m pytest tests/agente/routes/test_agent_router_integration.py tests/agente/sdk/test_specialist_profiles.py -q`
Expected: PASS (4 passed)

- [ ] **Step 10: Governança do prompt (novo prompt especialista)**

Run: `python scripts/audits/prompt_size_audit.py --check-delta`
O `especialista_recebimento.md` é prompt SEPARADO (não soma no principal) — confirmar que o audit não o conta no baseline do principal. Se contar como crescimento consciente: `--update-baseline --update-claude-md` no mesmo commit. Aplicar checklist PAD-CTX.

- [ ] **Step 11: Commit**

```bash
git add app/agente/sdk/specialist_profiles.py app/agente/prompts/especialista_recebimento.md app/agente/sdk/client.py app/agente/routes/chat.py tests/agente/sdk/test_specialist_profiles.py tests/agente/routes/test_agent_router_integration.py
git commit -m "feat(agente): cliente especialista + agent_router integrado shadow/on (F1 T7)"
```

- [ ] **Step 12: Teams regression** — `client.py` export-crítico: `python -m pytest tests/teams/ -q` → all pass.

---

### Task 8: Executor atômico (subagente dedicado) + prova de invariantes

**Files:**
- Create: `.claude/agents/executor-recebimento-nfpo.md`
- Test: `tests/agente/config/test_executor_atomico_invariantes.py`

**Interfaces:**
- Consumes: `agent_loader.load_agent_definitions` (`agent_loader.py:321-500`), `permissions.can_use_tool` (intacto).
- Produces: definição de subagente `executor-recebimento-nfpo` (tools apertadas: `Bash, Grep, Read` + skills `validacao-nf-po, conciliando-odoo-po`; sem MCP de escrita ampla).

**Invariante a provar:** o executor chama `can_use_tool` IDÊNTICO (nada muda em `permissions.py`). O teste prova que (a) o gate R11.1 (`action_update_taxes`) ainda NEGA mesmo no contexto do executor; (b) a definição não habilita Write/Edit amplos. NÃO há código novo de permissão — o teste é a rede que garante que NÃO regredimos.

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/config/test_executor_atomico_invariantes.py
import asyncio
import os
from unittest import mock
from app.agente.config import permissions as perm


def _deny_check(tool_name, tool_input):
    # asyncio.run (NAO get_event_loop().run_until_complete — quebra com "loop
    # already running" sob pytest-asyncio). Precedente: test_permissions_odoo_tax_gate.py.
    return asyncio.run(perm.can_use_tool(tool_name, tool_input, None))

def test_executor_nao_bypassa_gate_r11_action_update_taxes(app):
    with app.app_context():
        perm.set_current_session_id('exec-1')
        with mock.patch('app.agente.config.feature_flags.USE_ODOO_TAX_GATE', True):
            res = _deny_check('Bash', {
                'command': "python -c \"models.execute_kw(db,uid,pw,'sale.order',"
                           "'action_update_taxes',[[123]])\""})
        assert res.__class__.__name__ == 'PermissionResultDeny'

def test_executor_definicao_carrega_com_tools_apertadas():
    from app.agente.config.agent_loader import load_agent_definitions
    defs = load_agent_definitions(os.path.join(os.getcwd(), '.claude', 'agents'))
    ex = defs.get('executor-recebimento-nfpo')
    assert ex is not None, 'executor nao carregou'
    # AgentDefinition (claude_agent_sdk) tem campo `tools` (list) — verificado.
    # Apertada: so' Bash/Grep/Read, sem Write/Edit.
    assert ex.tools is not None
    assert 'Write' not in ex.tools and 'Edit' not in ex.tools
    assert set(ex.tools) <= {'Bash', 'Grep', 'Read'}
```

> Verificado no código real: `load_agent_definitions(agents_dir) -> dict` (`agent_loader.py:321`) e `AgentDefinition.tools` é `list` (campo nativo do SDK `claude_agent_sdk` — fields `tools`/`disallowedTools`/`skills`/`model`/`effort`...).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/config/test_executor_atomico_invariantes.py -q`
Expected: FAIL — `executor nao carregou` (arquivo `.md` ainda não existe).

- [ ] **Step 3: Write the subagent definition**

```markdown
<!-- .claude/agents/executor-recebimento-nfpo.md -->
---
name: executor-recebimento-nfpo
description: Executor ATOMICO do ato irreversivel de recebimento (vincular/conciliar NF x PO com --confirmar). Chamado PELO especialista gestor-recebimento com tudo resolvido. Recebe -> executa --confirmar -> finaliza numa unica invocacao. NUNCA dialoga, NUNCA re-diagnostica.
model: sonnet
tools: Bash, Grep, Read
skills: validacao-nf-po, conciliando-odoo-po
effort: high
---

Você é o **executor atômico** do recebimento. Recebe do especialista os parâmetros JÁ
RESOLVIDOS (NF, PO, validacao_id, ação) e o aval de confirmação. Sua única tarefa é
executar o ato irreversível com `--confirmar` e finalizar — numa única invocação.

INVIOLÁVEL:
- NÃO redescubra nem re-valide premissas (o especialista já fez o dry-run).
- NÃO dialogue nem peça confirmação (o aval já veio).
- Os gates de permissão (R11/R12) e a auditoria (R9) valem normalmente — se um gate negar,
  reporte o bloqueio e pare; não tente contornar.
- Ao concluir, escreva findings detalhados em `/tmp/subagent-findings/` e retorne um resumo
  curto (resultado + ids afetados). Finaliza aqui — não devolve para re-chamada.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/config/test_executor_atomico_invariantes.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full permissions regression (prova de não-regressão)**

Run: `python -m pytest tests/agente/test_permissions_odoo_tax_gate.py tests/agente/test_permissions_estoque_restricao.py -q`
Expected: PASS (gates intactos).

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/executor-recebimento-nfpo.md tests/agente/config/test_executor_atomico_invariantes.py
git commit -m "feat(agente): executor atomico recebimento + prova de invariantes (F1 T8)"
```

---

### Task 9: Gate de métrica (custo/sessão + cache_read antes/depois)

**Files:**
- Create: `app/agente/services/specialist_handoff_metrics.py`
- Test: `tests/agente/services/test_specialist_handoff_metrics.py`

**Interfaces:**
- Consumes: `AgentSessionCost.aggregate_summary` (`models.py:1551-1645`, retorna `total_cost_usd`, `total_requests`, `total_cache_read_tokens`, `cache_hit_rate`, `by_tool`), `AgentInvocationMetric`.
- Produces:
  - `custo_medio_por_sessao(session_ids: list[str]) -> dict` → `{'custo_total', 'sessoes', 'custo_medio', 'cache_hit_rate', 'num_turns'}` (num_turns = média de `AgentInvocationMetric.num_turns` por sessão).
  - `compara_baseline(baseline: dict, atual: dict) -> dict` → `{'delta_custo_medio', 'delta_cache_hit_rate', 'delta_num_turns', 'passou_gate': bool}`. Gate = `custo cai` E `cache_hit_rate não regride` E `num_turns não sobe >5%` (spec: turns sobe = perdeu contexto = reverter). Robusto a chaves ausentes (`.get(...,0.0)`).

**Uso:** rodar `custo_medio_por_sessao` sobre sessões `gestor-recebimento` ANTES (multi-spawn, flag off) e DEPOIS (flag on); `compara_baseline` decide o gate da spec (custo cai, num_turns não sobe por perda de contexto).

- [ ] **Step 1: Write the failing test**

```python
# tests/agente/services/test_specialist_handoff_metrics.py
from app.agente.services.specialist_handoff_metrics import compara_baseline


def test_gate_passa_quando_custo_cai_cache_ok_e_turns_estavel():
    base = {"custo_medio": 10.0, "cache_hit_rate": 0.5, "num_turns": 8.0}
    atual = {"custo_medio": 7.0, "cache_hit_rate": 0.62, "num_turns": 8.0}
    r = compara_baseline(base, atual)
    assert r["delta_custo_medio"] == -3.0
    assert r["passou_gate"] is True

def test_gate_falha_se_custo_sobe():
    r = compara_baseline({"custo_medio": 10.0, "cache_hit_rate": 0.5},
                         {"custo_medio": 11.0, "cache_hit_rate": 0.6})
    assert r["passou_gate"] is False

def test_gate_falha_se_cache_regride():
    # Custo caiu mas cache_hit_rate caiu (sinal de re-descoberta/contexto perdido).
    r = compara_baseline({"custo_medio": 10.0, "cache_hit_rate": 0.6},
                         {"custo_medio": 9.0, "cache_hit_rate": 0.4})
    assert r["passou_gate"] is False

def test_gate_falha_se_num_turns_sobe():
    # Spec: turns sobe = perdeu contexto = reverter (mesmo com custo menor).
    r = compara_baseline({"custo_medio": 10.0, "cache_hit_rate": 0.6, "num_turns": 8.0},
                         {"custo_medio": 7.0, "cache_hit_rate": 0.6, "num_turns": 12.0})
    assert r["passou_gate"] is False

def test_gate_robusto_a_chaves_ausentes():
    # GIGO: chaves faltando nao explodem (default 0.0) — entrada incompleta = nao passa.
    r = compara_baseline({}, {})
    assert r["passou_gate"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agente/services/test_specialist_handoff_metrics.py -q`
Expected: FAIL — `ModuleNotFoundError: ...specialist_handoff_metrics`

- [ ] **Step 3: Write minimal implementation**

```python
# app/agente/services/specialist_handoff_metrics.py
"""Gate de metrica do piloto de handoff (F1): custo medio/sessao + cache_read
antes vs depois. Fonte: AgentSessionCost.aggregate_summary (principal) +
AgentInvocationMetric (subagente). Spec: gate = custo cai E cache nao infla."""
from __future__ import annotations


def custo_medio_por_sessao(session_ids: list[str]) -> dict:
    from sqlalchemy import func
    from app.agente.models import AgentSessionCost, AgentInvocationMetric
    total, hit_rates, turns = 0.0, [], []
    for sid in session_ids:
        agg = AgentSessionCost.aggregate_summary(session_id=sid)
        total += float(agg.get("total_cost_usd") or 0)
        hit_rates.append(float(agg.get("cache_hit_rate") or 0))
        # num_turns medio das invocacoes da sessao (sinal de re-descoberta).
        nt = (AgentInvocationMetric.query
              .with_entities(func.coalesce(func.avg(AgentInvocationMetric.num_turns), 0))
              .filter(AgentInvocationMetric.session_id == sid).scalar())
        turns.append(float(nt or 0))
    n = len(session_ids) or 1
    return {
        "custo_total": round(total, 4),
        "sessoes": len(session_ids),
        "custo_medio": round(total / n, 4),
        "cache_hit_rate": round(sum(hit_rates) / n, 4) if hit_rates else 0.0,
        "num_turns": round(sum(turns) / n, 2) if turns else 0.0,
    }


def compara_baseline(baseline: dict, atual: dict) -> dict:
    """Gate da spec: custo cai E cache nao regride E num_turns nao sobe (>5% =
    perdeu contexto). `.get()` com default 0.0 — entrada incompleta nao explode
    (e nao passa: custo 0 < 0 e' False)."""
    b_custo, a_custo = baseline.get("custo_medio", 0.0), atual.get("custo_medio", 0.0)
    b_cache, a_cache = baseline.get("cache_hit_rate", 0.0), atual.get("cache_hit_rate", 0.0)
    b_turns, a_turns = baseline.get("num_turns", 0.0), atual.get("num_turns", 0.0)
    delta_custo = round(a_custo - b_custo, 4)
    delta_cache = round(a_cache - b_cache, 4)
    delta_turns = round(a_turns - b_turns, 2)
    passou = (a_custo < b_custo and a_cache >= b_cache
              and delta_turns <= max(b_turns * 0.05, 0.0))
    return {"delta_custo_medio": delta_custo, "delta_cache_hit_rate": delta_cache,
            "delta_num_turns": delta_turns, "passou_gate": passou}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agente/services/test_specialist_handoff_metrics.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/specialist_handoff_metrics.py tests/agente/services/test_specialist_handoff_metrics.py
git commit -m "feat(agente): gate de metrica do handoff (custo/sessao + cache) (F1 T9)"
```

---

## Rollout (pós-implementação, fora do código — requer aval)

1. Deploy com `AGENT_SPECIALIST_HANDOFF=off` (código inerte).
2. Capturar baseline: `custo_medio_por_sessao` sobre sessões `gestor-recebimento` recentes (multi-spawn atual).
3. `AGENT_SPECIALIST_HANDOFF=shadow` — agent_router decide + persiste `agente_ativo` + loga, sem trocar cliente. Validar logs `[AGENT_ROUTER]` (decisões coerentes) por alguns dias.
4. `AGENT_SPECIALIST_HANDOFF=admin` — `on` só para admin (canary Rafael). Medir.
5. `compara_baseline(baseline, atual)` → se `passou_gate` (custo cai E cache não regride E `num_turns` não sobe), `AGENT_SPECIALIST_HANDOFF=on`. Senão, reverter para `shadow`/`off` (rollback instantâneo por env).

---

## Self-Review

**Spec coverage (F1):**
- Pool multi-agente → T3. Roteador → T2 + T7. `transferir_para` + handoff magro → T5 + T6. Reversão → T6 (`devolver_ao_principal`) + T2 (`reversao_*`). Executor atômico → T8. Memória de trabalho (lê findings) → `get_subagent_findings` (ligado na F0) + injeção `render_handoff_block` (T7 Step 8). Flag off/shadow/on/admin → T1. Métrica de gate (cache_read/creation + custo/sessão antes vs depois) → T9 + Rollout. Invariantes (dry-run/R11/R12/gate/audit/isolamento irreversível) → T8 + Global Constraints. Handoff magro <10k → T5.
- Critério de aceite "handoff magro mensurável (<10k)" → T5 test `test_build_trunca_quando_excede_orcamento`. "executor preserva dry-run/R11/R12/gate/audit" → T8. "rollback instantâneo (flag off)" → T1 + Rollout. "cache_read não infla a cada confirmação" → T9 gate.

**Placeholder scan:** sem TBD/TODO; todo step de código tem código real. Único ponto que exige leitura do código vivo antes de costurar: **T7 Step 8a (pré-flight obrigatório)** — ler `chat.py:600-810` e registrar o `arquivo:linha` exato do swap de cliente ANTES de editar (a estrutura de provisionamento no `stream_response` não foi mapeada a fundo; inventar o ponto seria pior que mandar verificar). T8 (`AgentDefinition.tools`) **foi resolvido** (campo `tools: list` confirmado no SDK).

**Type consistency:** `role: str` em `PooledClient` (T3) ↔ `role=` nas funções do pool (T3) ↔ `agent_role`/`SPECIALIST_PROFILES[role]` (T7). `agente_ativo` (string role) consistente em T4/T6/T7. `build_handoff_context(...)→dict` (T5) ↔ consumido por `_apply_transfer` (T6) e `render_handoff_block` (T7). `aggregate_summary` keys (`total_cost_usd`, `cache_hit_rate`) usados em T9 conferem com `models.py:1632-1645`.

**Revisão adversarial (3 revisores, 2026-06-28) — correções APLICADAS:** (1) T6 `_apply_*` agora encapsula DB em `_app_context()` (tool MCP roda na thread daemon do SDK sem Flask context — sem isso a escrita se perdia em prod); (2) T8 teste usa `asyncio.run()` (não `get_event_loop().run_until_complete()`, que quebra sob pytest); (3) T9 gate agora inclui `num_turns` (spec: turns sobe = perdeu contexto) + robustez a chaves ausentes; (4) T1 `clear=True`, T5 assert de remoção real, T7 stickiness explicitada. **Falsos positivos rejeitados:** os 4 "blockers" de interface (`PooledClient.role`/`_build_options(specialist_profile)`/`get/set_agente_ativo` "não existem") — são exatamente o que o plano CRIA (o próprio "fix" do revisor confirma); e o "break prematuro" de T5 — o loop já tem `continue` após cada `popitem`.

**Riscos conhecidos (verificar na execução):** (a) T7 Step 8a — provisão do cliente especialista no `stream_response` é o ponto mais delicado (model stickiness, ler `chat.py:600-810`); (b) `prompt_size_audit` pode contabilizar o novo prompt — confirmar que é prompt SEPARADO do principal; (c) Teams: rodar a suíte após cada task que toca `client.py`/`feature_flags.py`/`models.py`.

## Execução

**Plano salvo em `docs/superpowers/plans/2026-06-28-f1-handoff-especialista-piloto.md`. Duas opções de execução:**

1. **Subagent-Driven (recomendado)** — um subagente fresco por task, revisão entre tasks (REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`).
2. **Inline** — executar as tasks nesta sessão com checkpoints (REQUIRED SUB-SKILL: `superpowers:executing-plans`).

**Nada em produção sem aval.** Qual abordagem?
