# Memory System Redesign — 3 Channels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar a necessidade de "esquentar" o agente em toda sessao nova — tornando as memorias do usuario **regras ativas** em vez de contexto passivo.

**Architecture:** Separar memorias em 3 canais com framing distinto no prompt: (1) `<user_rules priority="mandatory">` como extensao do system prompt, (2) `<operational_directives>` como pre-flight checks, (3) `<user_memories>` como contexto referencial. Auto-save detecta linguagem prescritiva e promove automaticamente. Consolidator protege regras mandatorias.

**Tech Stack:** Python 3.12, Flask 3.1, SQLAlchemy 2.0, PostgreSQL 18, Claude Agent SDK 0.1.60, pgvector para embeddings.

---

## Motivacao

O proprio codigo admite o problema em `app/agente/config/feature_flags.py:209-211`:

> *"meta-heuristica id=300 'Memorias de usuario devem funcionar como protocolo ativo' tem **12% efetividade**. O proprio sistema documenta que memorias sao lidas mas nao obedecidas. Causa e estrutural: onde a memoria aparece no prompt."*

**Caso concreto (16/04/2026)** — Marcus Lima (user_id=18, Controller Financeiro):

| Sessao | Msgs | Custo | Sintoma |
|--------|------|-------|---------|
| BASELINE (78dcb8fb) | 24 | $13 | Regenerou arquivo **7 vezes** por formato errado |
| Transferencia Interna (dc6af5f0) | 306 | $151 | Reusa sessao cross-day pra nao perder contexto |

Baseline canonico ja estava salvo em `/memories/preferences.xml`, mas o agente renderizou como `<memory>` passivo e ignorou. A documentacao do formato foi **lida** mas **nao obedecida** — exatamente o 12% que o proprio codigo admite.

## Diagnostico

### 4 problemas estruturais (todos no mesmo eixo: framing)

1. **Framing uniforme**: preferences.xml (Tier 1, sempre injetado) e heuristica rara aparecem no mesmo bloco `<user_memories>` — modelo trata as duas igual.
2. **Auto-save descritivo**: `pattern_analyzer.py:4,40,88` instrui a gerar patterns prescritivos, mas destino eh `/memories/empresa/heuristicas/` (shared). Preferencias pessoais do usuario ficam dispersas em `/corrections/`, `/context/`, sem framing de regra.
3. **Consolidator cega**: `memory_consolidator.py:62-65` protege apenas `user.xml` + `preferences.xml`. Protocolos uteis (ex: `baseline-de-extratos-pendentes-deve-ser-preservado`, id=436, 94 effective_count) viraram `_archived_` e a substituta `consolidated.xml` ficou **sem embedding** — retrieval zerou.
4. **Filtro estreito de `<operational_directives>`**: `memory_injection.py:360-368` so aceita `/heuristicas/` + importance>=0.7 + nivel 5. Protocolos de formato (como baseline) sao estruturalmente protocolos, nao heuristicas — ficam foraz do canal de regra.

### Insight central

O sistema ja tem 3 "camadas logicas" implicitas:
- **Protegidas** (user.xml, preferences.xml, perfil empresa): Tier 1/1.5, sempre injetadas
- **Promovidas** (heuristicas nivel 5): Tier 1.6 ou `<operational_directives>`
- **Candidatas semanticas**: Tier 2 via RAG

Mas todas as 3 viram `<memory>` no XML final. **O modelo nao distingue**. O fix eh tornar essa distincao explicita no framing.

---

## Arquitetura Alvo

### 3 Canais com framing distinto

| Canal | Tag XML | Quando Injeta | Framing Semantico | Obediencia Esperada | Salvar Quando |
|-------|---------|---------------|-------------------|---------------------|---------------|
| **L1 Rules** | `<user_rules priority="mandatory">` | Sempre (Tier 1) | Extensao do system prompt | **Obrigatoria** — violar = erro | Correcao forte, preferencia explicita, usuario disse "SEMPRE/NUNCA" |
| **L2 Directives** | `<operational_directives priority="critical">` | Sempre se matches dominio (Tier 0c) | Pre-flight conditional | **Verificar WHEN, aplicar DO** | Heuristica transferivel nivel 5 confirmada |
| **L3 Memories** | `<user_memories>` | Semantico (Tier 2) ou fallback | Contexto referencial | "Use se relevante" | Fato, historico, preferencia fraca |

### Ciclo de vida novo

```
[User diz algo prescritivo]
    ↓
[pattern_analyzer detecta gatilho mandatory]
    ↓
[Salva com priority=mandatory em preferences.xml do user]
    ↓
[memory_injection renderiza em <user_rules> (Tier 1, sempre)]
    ↓
[System_prompt R0e instrui: user_rules = regra igual ao meu]
    ↓
[Modelo obedece antes de responder]
    ↓
[memory_consolidator protege de arquivamento]
```

### Mudancas de schema

```sql
-- Nova coluna em agent_memories
ALTER TABLE agent_memories ADD COLUMN priority VARCHAR(20) DEFAULT 'contextual';
-- Valores validos: 'mandatory', 'advisory', 'contextual'
-- CHECK constraint para validar

-- Index parcial para lookup rapido de mandatory
CREATE INDEX idx_agent_memories_mandatory
  ON agent_memories (user_id, path)
  WHERE priority = 'mandatory' AND is_cold = false;
```

### Mudancas de injecao

```python
# memory_injection.py — novo layout
def _load_user_memories_for_context(user_id, prompt, model_name):
    sections = []

    # L1: RULES (always, mandatory) — NOVO
    rules_block = _build_user_rules(user_id)
    if rules_block:
        sections.append(rules_block)  # <user_rules priority="mandatory">

    # L2: DIRECTIVES (conditional) — EXISTENTE mas filtro expandido
    directives_block = _build_operational_directives(user_id)
    if directives_block:
        sections.append(directives_block)

    # L3: MEMORIES (semantic) — EXISTENTE
    memories_block = _build_user_memories_legacy(user_id, prompt, model_name)
    if memories_block:
        sections.append(memories_block)

    return '\n\n'.join(sections)
```

### Mudancas de system_prompt

Novo `R0e` em `app/agente/prompts/system_prompt.md`:

> Quando voce ver `<user_rules priority="mandatory">` no contexto, trate cada `<rule>` como extensao deste system prompt. Estas regras foram salvas pelo usuario e tem prioridade sobre qualquer heuristica propria. Violar uma rule = erro factual grave. ANTES de responder, mentalmente rode o checklist de qualquer rule aplicavel.

Update de `R0` (auto_save) para priorizar deteccao de linguagem prescritiva:

> Ao detectar linguagem prescritiva forte ("SEMPRE fazer X", "NUNCA fazer Y", "rejeitar Z", "o formato esta travado", "nao aceito variacao"), salve como `priority="mandatory"` em `/memories/preferences.xml` do usuario — NAO disperso em `/corrections/`.

---

## File Structure

### Novos arquivos

| Arquivo | Responsabilidade |
|---------|------------------|
| `scripts/migrations/add_priority_agent_memories.py` | Migration Python (ADD COLUMN + backfill) |
| `scripts/migrations/add_priority_agent_memories.sql` | Migration SQL idempotente |
| `app/agente/sdk/memory_injection_rules.py` | Funcao `_build_user_rules()` isolada |
| `tests/agente/test_memory_injection_rules.py` | Unit tests L1 Rules |
| `tests/agente/test_pattern_analyzer_mandatory.py` | Unit tests pattern mandatory detection |
| `tests/agente/test_memory_consolidator_protection.py` | Unit tests consolidator proteje mandatory |

### Arquivos modificados

| Arquivo | Mudanca |
|---------|---------|
| `app/agente/models.py` | Adicionar campo `priority` em AgentMemory |
| `app/agente/sdk/memory_injection.py` | Importar `_build_user_rules`, incluir no pipeline |
| `app/agente/services/pattern_analyzer.py` | Detectar gatilhos mandatory em `extrair_insights_pessoais_sessao` |
| `app/agente/services/memory_consolidator.py` | Adicionar `priority='mandatory'` a protecao |
| `app/agente/tools/memory_mcp_tool.py` | Save/update aceitam `priority` param |
| `app/agente/prompts/system_prompt.md` | Nova regra R0e + update R0 |
| `app/agente/config/feature_flags.py` | Nova flag `USE_USER_RULES_CHANNEL` (default false inicialmente) |

### Testes

- `pytest tests/agente/test_memory_injection_rules.py` — L1 render correto
- `pytest tests/agente/test_pattern_analyzer_mandatory.py` — Detecta prescritivo
- `pytest tests/agente/test_memory_consolidator_protection.py` — Nao arquiva mandatory

---

## Tasks

Todas as tasks assumem branch dedicada `feat/memory-3-channels` a partir de `main`.

### Task 1: Branch + feature flag kill switch

**Files:**
- Modify: `app/agente/config/feature_flags.py:204-217`

- [ ] **Step 1: Criar branch**

```bash
git checkout -b feat/memory-3-channels
```

- [ ] **Step 2: Adicionar flag `USE_USER_RULES_CHANNEL`**

Edit `app/agente/config/feature_flags.py` apos `USE_OPERATIONAL_DIRECTIVES`:

```python
# User Rules Channel (2026-04-16) — Mudanca 3
# Novo canal L1 <user_rules priority="mandatory"> separado de <user_memories>.
# Memorias com priority='mandatory' sao renderizadas como extensao do system prompt.
# Depende de coluna `priority` em agent_memories (migration prerequisite).
# Default false: ativar apos migration + backfill + testes em staging.
USE_USER_RULES_CHANNEL = os.getenv("AGENT_USER_RULES_CHANNEL", "false").lower() == "true"
```

- [ ] **Step 3: Commit flag**

```bash
git add app/agente/config/feature_flags.py
git commit -m "feat(agente): add USE_USER_RULES_CHANNEL flag (default off)"
```

---

### Task 2: Migration — coluna priority

**Files:**
- Create: `scripts/migrations/add_priority_agent_memories.py`
- Create: `scripts/migrations/add_priority_agent_memories.sql`

- [ ] **Step 1: Criar SQL idempotente**

Create `scripts/migrations/add_priority_agent_memories.sql`:

```sql
-- Migration: adicionar coluna priority em agent_memories
-- Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md
-- Data: 2026-04-16

BEGIN;

-- 1. ADD COLUMN com default seguro
ALTER TABLE agent_memories
  ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'contextual';

-- 2. CHECK constraint para validar valores
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agent_memories_priority_check') THEN
    ALTER TABLE agent_memories
      ADD CONSTRAINT agent_memories_priority_check
      CHECK (priority IN ('mandatory', 'advisory', 'contextual'));
  END IF;
END $$;

-- 3. Backfill heuristico (idempotente):
--   user.xml + preferences.xml com path em PROTECTED_PATHS → 'advisory' (Tier 1, sempre injetado mas nao mandatory por padrao)
--   heuristicas empresa nivel 5 + importance>=0.7 → 'advisory' (ja entram em operational_directives)
--   demais → 'contextual' (default)

-- 4. Index parcial para lookup rapido de mandatory
CREATE INDEX IF NOT EXISTS idx_agent_memories_mandatory
  ON agent_memories (user_id, path)
  WHERE priority = 'mandatory' AND is_cold = false;

COMMIT;

-- Verificacao pos-migration
SELECT priority, COUNT(*) FROM agent_memories GROUP BY priority;
```

- [ ] **Step 2: Criar Python migration com check_before/run/check_after**

Create `scripts/migrations/add_priority_agent_memories.py`:

```python
"""
Migration: adicionar coluna priority em agent_memories.

Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md
Data: 2026-04-16
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def check_before(conn):
    print("=== BEFORE ===")
    inspector = inspect(conn)
    cols = {c['name'] for c in inspector.get_columns('agent_memories')}
    print(f"  Coluna priority: {'EXISTS' if 'priority' in cols else 'NAO EXISTE'}")

    indexes = {idx['name'] for idx in inspector.get_indexes('agent_memories')}
    print(f"  Index idx_agent_memories_mandatory: {'EXISTS' if 'idx_agent_memories_mandatory' in indexes else 'NAO EXISTE'}")


def run_migration(conn):
    print("\n=== MIGRATION ===")

    # 1. ADD COLUMN
    conn.execute(text("""
        ALTER TABLE agent_memories
        ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'contextual'
    """))
    print("  OK: coluna priority adicionada")

    # 2. CHECK constraint
    result = conn.execute(text("""
        SELECT 1 FROM pg_constraint WHERE conname = 'agent_memories_priority_check'
    """)).fetchone()
    if not result:
        conn.execute(text("""
            ALTER TABLE agent_memories
            ADD CONSTRAINT agent_memories_priority_check
            CHECK (priority IN ('mandatory', 'advisory', 'contextual'))
        """))
        print("  OK: CHECK constraint adicionada")
    else:
        print("  SKIP: CHECK constraint ja existe")

    # 3. Index parcial
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_agent_memories_mandatory
          ON agent_memories (user_id, path)
          WHERE priority = 'mandatory' AND is_cold = false
    """))
    print("  OK: index idx_agent_memories_mandatory criado")

    conn.commit()


def check_after(conn):
    print("\n=== AFTER ===")
    result = conn.execute(text("""
        SELECT priority, COUNT(*) as total FROM agent_memories GROUP BY priority ORDER BY priority
    """))
    for row in result:
        print(f"  priority={row[0]}: {row[1]} memorias")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            check_before(conn)
        with db.engine.begin() as conn:
            run_migration(conn)
        with db.engine.connect() as conn:
            check_after(conn)


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Adicionar campo priority em models.py**

Edit `app/agente/models.py` — adicionar linha apos `escopo`:

```python
# Linha ~480 (dentro da classe AgentMemory)
priority = db.Column(db.String(20), default='contextual', nullable=False)
# Valores: 'mandatory' (user_rules), 'advisory' (operational_directives), 'contextual' (user_memories)
```

- [ ] **Step 4: Aplicar migration localmente e validar**

```bash
source .venv/bin/activate
python scripts/migrations/add_priority_agent_memories.py
```

Expected output: `OK: coluna priority adicionada` + `priority=contextual: N memorias`.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrations/add_priority_agent_memories.py scripts/migrations/add_priority_agent_memories.sql app/agente/models.py
git commit -m "feat(agente): add priority column to agent_memories"
```

---

### Task 3: Testes unitarios L1 Rules builder

**Files:**
- Create: `tests/agente/test_memory_injection_rules.py`
- Create: `app/agente/sdk/memory_injection_rules.py` (stub)

- [ ] **Step 1: Criar stub do builder**

Create `app/agente/sdk/memory_injection_rules.py`:

```python
"""
L1 Rules Channel — Builder de <user_rules priority="mandatory">.

Separa memorias com priority='mandatory' do usuario em bloco XML distinto,
renderizado como extensao do system prompt (vs contexto passivo).

Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md
"""
import logging
from typing import Optional, List
from ._sanitization import xml_escape, sanitize_memory_content

logger = logging.getLogger('sistema_fretes')


def _build_user_rules(user_id: int) -> Optional[str]:
    """
    Constroi bloco <user_rules priority="mandatory"> com memorias do usuario
    marcadas como regras obrigatorias.

    Sempre injetado (Tier 1-equivalente). Nao sofre corte por budget.
    Inclui memorias user_id do usuario E user_id=0 (empresa) com priority='mandatory'.

    Returns:
        String XML ou None se nenhuma regra ativa.
    """
    from ..models import AgentMemory
    try:
        rules = AgentMemory.query.filter(
            AgentMemory.user_id.in_([user_id, 0]),
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.priority == 'mandatory',
        ).order_by(AgentMemory.user_id.asc(), AgentMemory.path.asc()).all()

        if not rules:
            return None

        parts = [
            '<user_rules priority="mandatory">',
            '  <!-- Regras salvas pelo usuario. Trate como extensao do system prompt. -->',
            '  <!-- Verificar aplicabilidade antes de responder. Violar = erro grave. -->',
        ]
        for rule in rules:
            content = sanitize_memory_content(
                (rule.content or '').strip(),
                source=f"mem_id={rule.id} path={rule.path}"
            )
            parts.append(
                f'  <rule path="{xml_escape(rule.path)}" scope="'
                f'{"empresa" if rule.user_id == 0 else "pessoal"}">'
            )
            parts.append(f'    {content}')
            parts.append('  </rule>')
        parts.append('</user_rules>')

        result = '\n'.join(parts)
        logger.info(
            f"[USER_RULES] user_id={user_id} rules={len(rules)} "
            f"chars={len(result)}"
        )
        return result

    except Exception as e:
        logger.warning(f"[USER_RULES] Build failed (ignored): {e}")
        return None
```

- [ ] **Step 2: Criar teste que falha (sem regra)**

Create `tests/agente/test_memory_injection_rules.py`:

```python
"""Tests para L1 Rules channel."""
import pytest
from app import create_app, db
from app.agente.models import AgentMemory
from app.agente.sdk.memory_injection_rules import _build_user_rules


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def cleanup_memories(app):
    """Limpa memorias de teste apos cada teste."""
    created_ids = []
    yield created_ids
    for mid in created_ids:
        mem = AgentMemory.query.get(mid)
        if mem:
            db.session.delete(mem)
    db.session.commit()


def test_build_user_rules_returns_none_when_no_rules(app, cleanup_memories):
    """Sem regras mandatory, retorna None."""
    result = _build_user_rules(user_id=99999)  # user que nao existe
    assert result is None


def test_build_user_rules_returns_xml_with_mandatory_rule(app, cleanup_memories):
    """Com uma regra mandatory, retorna XML com <user_rules>."""
    mem = AgentMemory.create_file(99999, '/memories/test_rule.xml', 'SEMPRE X, NUNCA Y')
    mem.priority = 'mandatory'
    db.session.commit()
    cleanup_memories.append(mem.id)

    result = _build_user_rules(user_id=99999)
    assert result is not None
    assert '<user_rules priority="mandatory">' in result
    assert 'SEMPRE X, NUNCA Y' in result
    assert '</user_rules>' in result


def test_build_user_rules_excludes_contextual_memories(app, cleanup_memories):
    """Memorias com priority='contextual' NAO entram em user_rules."""
    mem = AgentMemory.create_file(99999, '/memories/test_contextual.xml', 'info contextual')
    mem.priority = 'contextual'
    db.session.commit()
    cleanup_memories.append(mem.id)

    result = _build_user_rules(user_id=99999)
    assert result is None


def test_build_user_rules_includes_empresa_mandatory(app, cleanup_memories):
    """Memorias empresa (user_id=0) com priority=mandatory entram."""
    mem = AgentMemory.create_file(0, '/memories/empresa/rules/test_empresa.xml', 'regra empresa')
    mem.priority = 'mandatory'
    db.session.commit()
    cleanup_memories.append(mem.id)

    result = _build_user_rules(user_id=99999)
    assert result is not None
    assert 'regra empresa' in result
    assert 'scope="empresa"' in result


def test_build_user_rules_excludes_cold_memories(app, cleanup_memories):
    """Regras em tier frio nao entram."""
    mem = AgentMemory.create_file(99999, '/memories/cold_rule.xml', 'frio')
    mem.priority = 'mandatory'
    mem.is_cold = True
    db.session.commit()
    cleanup_memories.append(mem.id)

    result = _build_user_rules(user_id=99999)
    assert result is None
```

- [ ] **Step 3: Rodar testes (devem passar — stub ja funciona)**

```bash
source .venv/bin/activate
pytest tests/agente/test_memory_injection_rules.py -v
```

Expected: 5 PASS.

- [ ] **Step 4: Commit**

```bash
git add app/agente/sdk/memory_injection_rules.py tests/agente/test_memory_injection_rules.py
git commit -m "feat(agente): add L1 user_rules builder + unit tests"
```

---

### Task 4: Integrar `_build_user_rules` no pipeline de injecao

**Files:**
- Modify: `app/agente/sdk/memory_injection.py:577-1149`

- [ ] **Step 1: Editar `_load_user_memories_for_context` para chamar `_build_user_rules`**

Edit `app/agente/sdk/memory_injection.py` — inserir apos linha 659 (antes de Tier 1):

```python
# ── L1: User Rules (SEMPRE, priority=mandatory) — NOVO CANAL ──
try:
    from ..config.feature_flags import USE_USER_RULES_CHANNEL
    if USE_USER_RULES_CHANNEL:
        from .memory_injection_rules import _build_user_rules
        rules_block = _build_user_rules(user_id)
        if rules_block:
            # Nao consome budget — sempre incluido no inicio
            tier0_parts.insert(0, rules_block)  # Primeiro no prompt
            tier0_chars += len(rules_block)
            logger.info(f"[MEMORY_INJECT] L1 user_rules injected: {len(rules_block)} chars")
except Exception as l1_err:
    logger.debug(f"[MEMORY_INJECT] L1 rules falhou (ignorado): {l1_err}")
```

- [ ] **Step 2: Rodar testes existentes para garantir nao-regressao**

```bash
source .venv/bin/activate
pytest tests/agente/ -v -k "memory" --timeout=30
```

Expected: todos os testes existentes ainda passam.

- [ ] **Step 3: Teste manual com flag OFF**

```bash
AGENT_USER_RULES_CHANNEL=false python -c "
from app import create_app
from app.agente.sdk.memory_injection import _load_user_memories_for_context
app = create_app()
with app.app_context():
    txt, ids = _load_user_memories_for_context(user_id=1, prompt='test', model_name='opus')
    assert '<user_rules' not in (txt or '')
    print('OK: flag OFF nao injeta user_rules')
"
```

Expected: `OK: flag OFF nao injeta user_rules`.

- [ ] **Step 4: Teste manual com flag ON + regra de seed**

```bash
AGENT_USER_RULES_CHANNEL=true python -c "
from app import create_app, db
from app.agente.models import AgentMemory
from app.agente.sdk.memory_injection import _load_user_memories_for_context
app = create_app()
with app.app_context():
    # Seed
    mem = AgentMemory.create_file(1, '/memories/_test_rule.xml', 'SEMPRE X')
    mem.priority = 'mandatory'
    db.session.commit()
    txt, ids = _load_user_memories_for_context(user_id=1, prompt='test', model_name='opus')
    assert '<user_rules priority=\"mandatory\">' in (txt or '')
    assert 'SEMPRE X' in (txt or '')
    # Cleanup
    db.session.delete(mem)
    db.session.commit()
    print('OK: flag ON injeta user_rules')
"
```

Expected: `OK: flag ON injeta user_rules`.

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/memory_injection.py
git commit -m "feat(agente): integrate L1 user_rules channel in injection pipeline"
```

---

### Task 5: Expandir filtro de `<operational_directives>` para aceitar `/protocolos/`

**Files:**
- Modify: `app/agente/sdk/memory_injection.py:322-453`

- [ ] **Step 1: Atualizar query em `_build_operational_directives`**

Edit `app/agente/sdk/memory_injection.py:360-368`:

```python
# ANTES
candidates = AgentMemory.query.filter(
    AgentMemory.user_id == 0,
    AgentMemory.is_directory == False,  # noqa: E712
    AgentMemory.is_cold == False,  # noqa: E712
    AgentMemory.path.like('/memories/empresa/heuristicas/%'),
    AgentMemory.importance_score >= MANDATORY_IMPORTANCE_THRESHOLD,
).order_by(...)

# DEPOIS
from sqlalchemy import or_ as sql_or
candidates = AgentMemory.query.filter(
    AgentMemory.user_id == 0,
    AgentMemory.is_directory == False,  # noqa: E712
    AgentMemory.is_cold == False,  # noqa: E712
    sql_or(
        AgentMemory.path.like('/memories/empresa/heuristicas/%'),
        AgentMemory.path.like('/memories/empresa/protocolos/%'),
    ),
    AgentMemory.importance_score >= MANDATORY_IMPORTANCE_THRESHOLD,
).order_by(
    AgentMemory.effective_count.desc()
).limit(MANDATORY_MAX_COUNT * 3).all()
```

- [ ] **Step 2: Rodar testes existentes**

```bash
pytest tests/agente/ -v -k "operational_directives or memory_injection" --timeout=30
```

Expected: passam.

- [ ] **Step 3: Commit**

```bash
git add app/agente/sdk/memory_injection.py
git commit -m "feat(agente): expand operational_directives filter to include protocolos"
```

---

### Task 6: Testes unitarios pattern_analyzer mandatory detection

**Files:**
- Create: `tests/agente/test_pattern_analyzer_mandatory.py`

- [ ] **Step 1: Criar teste que falha (deteccao ainda nao existe)**

Create `tests/agente/test_pattern_analyzer_mandatory.py`:

```python
"""Tests para deteccao de linguagem prescritiva → priority=mandatory."""
import pytest
from app import create_app
from app.agente.services.pattern_analyzer import _is_mandatory_trigger


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


def test_sempre_trigger_is_mandatory(app):
    assert _is_mandatory_trigger("SEMPRE usar Excel para relatorios") is True


def test_nunca_trigger_is_mandatory(app):
    assert _is_mandatory_trigger("NUNCA use tabela local") is True


def test_rejeitar_trigger_is_mandatory(app):
    assert _is_mandatory_trigger("Rejeitar HTML sem consultar") is True


def test_formato_travado_is_mandatory(app):
    assert _is_mandatory_trigger("O formato esta travado em 4 abas") is True


def test_nao_aceito_is_mandatory(app):
    assert _is_mandatory_trigger("nao aceito variacao de layout") is True


def test_descricao_not_mandatory(app):
    assert _is_mandatory_trigger("Marcus prefere Excel") is False


def test_observacao_not_mandatory(app):
    assert _is_mandatory_trigger("Este cliente pagou ontem") is False


def test_pergunta_not_mandatory(app):
    assert _is_mandatory_trigger("Qual e o formato esperado?") is False
```

- [ ] **Step 2: Rodar — deve falhar (funcao nao existe)**

```bash
pytest tests/agente/test_pattern_analyzer_mandatory.py -v
```

Expected: `ImportError: cannot import name '_is_mandatory_trigger'`.

- [ ] **Step 3: Implementar `_is_mandatory_trigger` em pattern_analyzer.py**

Edit `app/agente/services/pattern_analyzer.py` — adicionar apos imports (linha ~28):

```python
# Gatilhos de linguagem prescritiva (heuristica zero-LLM)
_MANDATORY_PATTERNS = [
    r'\bSEMPRE\b',
    r'\bNUNCA\b',
    r'\brejeit(ar|e|o)\b',
    r'\bnao acei(to|ta)\b',
    r'\bformato (esta )?travado\b',
    r'\bobriga(torio|toria)\b',
    r'\bexigir\b',
    r'\bimperati(vo|va)\b',
    r'\bestritamente\b',
]


def _is_mandatory_trigger(text: str) -> bool:
    """
    Detecta linguagem prescritiva forte que justifica salvar como priority='mandatory'.

    Zero-LLM — regex determinista. Complementar ao modelo pos-sessao que analisa
    contexto completo.
    """
    if not text:
        return False
    text_upper = text.upper()
    for pattern in _MANDATORY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
```

- [ ] **Step 4: Rodar — deve passar**

```bash
pytest tests/agente/test_pattern_analyzer_mandatory.py -v
```

Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/pattern_analyzer.py tests/agente/test_pattern_analyzer_mandatory.py
git commit -m "feat(agente): add _is_mandatory_trigger regex detector + tests"
```

---

### Task 7: Atualizar memory_mcp_tool para aceitar `priority`

**Files:**
- Modify: `app/agente/tools/memory_mcp_tool.py`

- [ ] **Step 1: Localizar funcao save_memory**

```bash
grep -n "def save_memory\|def _save_memory_impl" app/agente/tools/memory_mcp_tool.py | head -5
```

- [ ] **Step 2: Adicionar param `priority` opcional**

Edit `app/agente/tools/memory_mcp_tool.py` — na funcao de save:

```python
# Adicionar param priority na assinatura MCP
@enhanced_tool
async def save_memory(
    path: Annotated[str, "Caminho da memoria (ex: /memories/user.xml)"],
    content: Annotated[str, "Conteudo da memoria"],
    priority: Annotated[str, "Prioridade: 'mandatory' | 'advisory' | 'contextual'"] = 'contextual',
    target_user_id: Annotated[Optional[int], "Admin-only: user_id alvo"] = None,
):
    # ... codigo existente ...
    # Apos criar/atualizar mem:
    if priority in ('mandatory', 'advisory', 'contextual'):
        mem.priority = priority
        db.session.commit()
```

- [ ] **Step 3: Teste manual**

```bash
source .venv/bin/activate
python -c "
from app import create_app, db
from app.agente.models import AgentMemory
app = create_app()
with app.app_context():
    mem = AgentMemory.create_file(1, '/memories/_test_priority.xml', 'test')
    mem.priority = 'mandatory'
    db.session.commit()
    reloaded = AgentMemory.get_by_path(1, '/memories/_test_priority.xml')
    assert reloaded.priority == 'mandatory'
    db.session.delete(reloaded)
    db.session.commit()
    print('OK: priority persiste')
"
```

- [ ] **Step 4: Commit**

```bash
git add app/agente/tools/memory_mcp_tool.py
git commit -m "feat(agente): save_memory MCP tool accepts priority param"
```

---

### Task 8: Testes proteção memory_consolidator

**Files:**
- Create: `tests/agente/test_memory_consolidator_protection.py`

- [ ] **Step 1: Criar teste que falha**

Create `tests/agente/test_memory_consolidator_protection.py`:

```python
"""Tests: memorias priority=mandatory nunca viram cold nem sao consolidadas."""
import pytest
from app import create_app, db
from app.agente.models import AgentMemory
from app.agente.services.memory_consolidator import maybe_move_to_cold


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


def test_mandatory_memory_not_moved_to_cold(app):
    """Memoria mandatory com eficacia baixa NAO deve ir para cold."""
    mem = AgentMemory.create_file(99999, '/memories/_test_mandatory_cold.xml', 'regra')
    mem.priority = 'mandatory'
    mem.usage_count = 50  # acima do threshold MIN_USAGE
    mem.effective_count = 2  # eficacia < 10% (normalmente iria cold)
    db.session.commit()

    moved = maybe_move_to_cold(99999)

    reloaded = AgentMemory.query.get(mem.id)
    assert reloaded.is_cold is False, "Mandatory nao deve virar cold"

    # Cleanup
    db.session.delete(reloaded)
    db.session.commit()


def test_high_effective_count_not_moved_to_cold(app):
    """Memoria com effective_count>=50 NAO deve ir para cold."""
    mem = AgentMemory.create_file(99999, '/memories/_test_effective_cold.xml', 'util')
    mem.priority = 'contextual'
    mem.usage_count = 200
    mem.effective_count = 55  # acima do novo threshold
    db.session.commit()

    maybe_move_to_cold(99999)

    reloaded = AgentMemory.query.get(mem.id)
    assert reloaded.is_cold is False, "effective_count>=50 nao deve virar cold"

    db.session.delete(reloaded)
    db.session.commit()


def test_contextual_low_effective_moves_to_cold(app):
    """Memoria contextual com eficacia baixa — comportamento atual preservado."""
    mem = AgentMemory.create_file(99999, '/memories/_test_contextual_cold.xml', 'inutil')
    mem.priority = 'contextual'
    mem.usage_count = 50
    mem.effective_count = 2
    db.session.commit()

    maybe_move_to_cold(99999)

    reloaded = AgentMemory.query.get(mem.id)
    assert reloaded.is_cold is True, "Contextual inutil deve virar cold"

    db.session.delete(reloaded)
    db.session.commit()
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
pytest tests/agente/test_memory_consolidator_protection.py -v
```

Expected: 2 FAIL (proteção ainda não existe).

- [ ] **Step 3: Implementar proteção em `memory_consolidator.py`**

Edit `app/agente/services/memory_consolidator.py` — na funcao `maybe_move_to_cold`, filtro do candidates:

```python
# Localizar query que seleciona candidates (~linha 110-140, dentro de maybe_move_to_cold)
# Adicionar filtros no WHERE:

candidates_query = AgentMemory.query.filter(
    AgentMemory.user_id == user_id,
    AgentMemory.is_directory == False,  # noqa: E712
    AgentMemory.is_cold == False,  # noqa: E712
    AgentMemory.usage_count >= COLD_MOVE_MIN_USAGE,
    # NOVO: preservar mandatory
    AgentMemory.priority != 'mandatory',
    # NOVO: preservar memorias comprovadamente uteis
    AgentMemory.effective_count < 50,
)
```

- [ ] **Step 4: Rodar testes — devem passar**

```bash
pytest tests/agente/test_memory_consolidator_protection.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/memory_consolidator.py tests/agente/test_memory_consolidator_protection.py
git commit -m "feat(agente): consolidator protects mandatory + high effective_count memories"
```

---

### Task 9: Atualizar system_prompt.md (R0e nova + R0 update)

**Files:**
- Modify: `app/agente/prompts/system_prompt.md:60-102`

- [ ] **Step 1: Adicionar nova regra R0e apos R0d (linha 146)**

Edit `app/agente/prompts/system_prompt.md` — inserir apos `</rule>` de R0d:

```xml
  <rule id="R0e" name="User Rules Protocol">
    Quando voce ver um bloco &lt;user_rules priority="mandatory"&gt; no seu contexto,
    trate cada &lt;rule&gt; como extensao deste system prompt. Estas regras foram
    salvas pelo usuario e tem prioridade sobre heuristicas proprias ou defaults
    aprendidos.

    PROTOCOLO:
    1. ANTES de formar sua resposta, releia cada &lt;rule&gt; aplicavel ao pedido.
    2. Siga literalmente — nao interpretar, nao otimizar, nao sugerir variacao.
    3. Se a rule conflita com um pedido do usuario na mensagem atual:
       PERGUNTE antes de executar ("esta regra salva diz X, voce autoriza
       alterar para Y?"). NUNCA ignore silenciosamente.
    4. APLIQUE SILENCIOSAMENTE (nao cite a rule ao usuario, apenas obedeca).
    5. Self-check final: antes de entregar resposta/artefato, confirme que
       cada rule aplicavel foi respeitada.

    Violar uma rule = erro grave, equivalente a ignorar o system prompt.
    Estas sao preferencias fortes do usuario, salvas explicitamente como
    priority="mandatory" porque o fluxo anterior falhou em respeitar contexto passivo.
  </rule>
```

- [ ] **Step 2: Atualizar R0 (auto_save) para linguagem prescritiva**

Edit `app/agente/prompts/system_prompt.md:62-92` — substituir seção `<auto_save>`:

```xml
    <auto_save>
      Salve SILENCIOSAMENTE quando detectar:
      - Correcao: "na verdade...", "nao eh isso, eh..."
      - Preferencia: "prefiro tabela", "sempre mostre peso"
      - Regra de negocio: informacao sobre cliente/produto/processo
      - Info profissional: cargo, responsabilidade, dominio
      - Acao significativa: lancou pedidos em massa, conferiu faturas
      - Padrao repetido: 2+ vezes o mesmo comportamento
      - Erro tecnico recorrente: tool/skill falhou 2+ vezes com mesmo padrao
      - Workaround descoberto: tentei abordagem X, falhou, Y funcionou

      PRIORITY (escolher ao salvar):
      - mandatory: linguagem forte ("SEMPRE", "NUNCA", "rejeitar", "formato travado",
        "nao aceito"). Salva em /memories/preferences.xml do usuario. Vira &lt;user_rules&gt;.
      - advisory: heuristicas nivel 5 transferiveis. Salva em /memories/empresa/heuristicas/.
        Vira &lt;operational_directives&gt; se importance >= 0.7.
      - contextual: demais informacoes. Salva onde fizer sentido semanticamente.
        Vira &lt;user_memories&gt; via RAG.

      Memoria util responde: QUEM fez, O QUE, POR QUE, QUANDO.
      NAO salve: resultados pontuais, status temporarios, saudacoes.
      TIMING: Salve IMEDIATAMENTE ao detectar cada item.
      Em sessoes longas (10+ mensagens), verifique se houve correcoes ou aprendizados nao salvos.
    </auto_save>
```

- [ ] **Step 3: Verificar que nao quebrou markdown**

```bash
head -250 app/agente/prompts/system_prompt.md | grep -A2 "R0e\|auto_save"
```

- [ ] **Step 4: Commit**

```bash
git add app/agente/prompts/system_prompt.md
git commit -m "feat(agente): add R0e user_rules protocol + update R0 auto_save with priority"
```

---

### Task 10: Data migration — promover preferences Marcus + baseline

**Files:**
- Create: `scripts/migrations/backfill_priority_marcus_baseline_20260416.py`

- [ ] **Step 1: Criar migration de backfill**

Create `scripts/migrations/backfill_priority_marcus_baseline_20260416.py`:

```python
"""
Migration: backfill priority em memorias criticas do Marcus + baseline.

Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md
Data: 2026-04-16

Depende de: add_priority_agent_memories.py (coluna deve existir).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def check_before(conn):
    print("=== BEFORE ===")
    result = conn.execute(text("""
        SELECT id, user_id, path, priority FROM agent_memories
        WHERE (user_id = 18 AND path IN ('/memories/user.xml', '/memories/preferences.xml'))
           OR id IN (532, 536, 529, 531)
        ORDER BY user_id, path
    """))
    for row in result:
        print(f"  id={row[0]} user={row[1]} path={row[2]} priority={row[3]}")


def run_migration(conn):
    print("\n=== MIGRATION ===")

    # 1. preferences.xml do Marcus → mandatory
    conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'mandatory'
        WHERE user_id = 18 AND path = '/memories/preferences.xml'
    """))
    print("  OK: preferences.xml (user 18) -> mandatory")

    # 2. user.xml do Marcus → advisory (sempre injetado mas nao regra)
    conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'advisory'
        WHERE user_id = 18 AND path = '/memories/user.xml'
    """))
    print("  OK: user.xml (user 18) -> advisory")

    # 3. Heuristica baseline promovida → mandatory (alta criticidade)
    conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'mandatory'
        WHERE path LIKE '/memories/empresa/heuristicas/financeiro/baseline-de-extratos%'
    """))
    print("  OK: baseline heuristica -> mandatory")

    # 4. Heuristicas empresa nivel 5 com importance >= 0.7 → advisory
    conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'advisory'
        WHERE user_id = 0
          AND path LIKE '/memories/empresa/heuristicas/%'
          AND importance_score >= 0.7
          AND priority = 'contextual'
    """))
    print("  OK: heuristicas empresa nivel 5 -> advisory")

    conn.commit()


def check_after(conn):
    print("\n=== AFTER ===")
    result = conn.execute(text("""
        SELECT priority, COUNT(*) as total FROM agent_memories GROUP BY priority ORDER BY priority
    """))
    for row in result:
        print(f"  priority={row[0]}: {row[1]} memorias")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            check_before(conn)
        with db.engine.begin() as conn:
            run_migration(conn)
        with db.engine.connect() as conn:
            check_after(conn)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Rodar em staging/local (se aplicavel)**

```bash
source .venv/bin/activate
python scripts/migrations/backfill_priority_marcus_baseline_20260416.py
```

Expected output: lista de priority counts.

- [ ] **Step 3: Commit**

```bash
git add scripts/migrations/backfill_priority_marcus_baseline_20260416.py
git commit -m "feat(agente): backfill priority for Marcus + baseline heuristicas"
```

---

### Task 11: Deploy staged (feature flag + monitoramento)

- [ ] **Step 1: Push branch + PR**

```bash
git push origin feat/memory-3-channels
gh pr create --title "feat(agente): memory system redesign — 3 channels" --body "$(cat <<'EOF'
## Summary

- Separa memorias em 3 canais XML distintos no prompt:
  - `<user_rules priority="mandatory">` (NOVO): regras do usuario como extensao do system prompt
  - `<operational_directives priority="critical">` (expandido): aceita /protocolos/ alem de /heuristicas/
  - `<user_memories>` (existente): contexto passivo via RAG
- Auto-save detecta linguagem prescritiva (SEMPRE/NUNCA/rejeitar/travado) e promove para priority=mandatory
- Consolidator protege memorias mandatory + effective_count>=50 de virar cold
- System_prompt R0e novo: user_rules = regra, self-check obrigatorio antes de responder
- Flag `AGENT_USER_RULES_CHANNEL` (default off) para rollout gradual

## Test plan
- [x] Unit tests L1 rules builder (5 tests passando)
- [x] Unit tests pattern_analyzer mandatory detection (8 tests passando)
- [x] Unit tests consolidator protection (3 tests passando)
- [ ] Deploy staging com flag OFF — validar zero regressao
- [ ] Ativar flag em staging — validar Marcus nao precisa "esquentar"
- [ ] Monitorar `[USER_RULES]` logs por 48h
- [ ] Ativar em producao

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 2: Apos aprovacao da PR — deploy (Render auto-deploy)**

Push para main dispara deploy automatico.

- [ ] **Step 3: Rodar migrations em producao (Render Shell)**

```bash
cd /app && source .venv/bin/activate
python scripts/migrations/add_priority_agent_memories.py
python scripts/migrations/backfill_priority_marcus_baseline_20260416.py
```

- [ ] **Step 4: Ativar flag em staging primeiro**

```bash
# Via MCP Render update_environment_variables ou Dashboard
AGENT_USER_RULES_CHANNEL=true  # staging

# Apos 24h de sucesso, producao:
AGENT_USER_RULES_CHANNEL=true  # srv-d13m38vfte5s738t6p60 + worker
```

- [ ] **Step 5: Validar com Marcus amanha**

Pedir a Marcus que:
1. Abra sessao NOVA (nao reaproveitar dc6af5f0)
2. Peca "atualize a baseline"
3. Se sair no formato correto de primeira = sucesso

Monitorar logs:
```
mcp__render__list_logs(resource=['srv-d13m38vfte5s738t6p60'], text='USER_RULES user_id=18', limit=10)
```

---

## Verification

### Unit tests

```bash
source .venv/bin/activate
pytest tests/agente/test_memory_injection_rules.py -v              # 5 PASS
pytest tests/agente/test_pattern_analyzer_mandatory.py -v          # 8 PASS
pytest tests/agente/test_memory_consolidator_protection.py -v      # 3 PASS
```

### Integration test

```bash
AGENT_USER_RULES_CHANNEL=true python -c "
from app import create_app
from app.agente.sdk.memory_injection import _load_user_memories_for_context
app = create_app()
with app.app_context():
    txt, ids = _load_user_memories_for_context(
        user_id=18,
        prompt='atualize a baseline de extratos pendentes',
        model_name='claude-opus-4-7'
    )
    assert '<user_rules priority=\"mandatory\">' in (txt or '')
    assert 'baseline_conciliacoes' in (txt or '')
    print('OK: Marcus baseline entra como user_rule')
"
```

### Metric

Apos 7 dias em producao:

```sql
-- Memorias mandatory com maior uso
SELECT id, path, user_id, usage_count, effective_count,
       ROUND(effective_count::numeric / NULLIF(usage_count,0) * 100, 1) AS efetividade_pct
FROM agent_memories
WHERE priority = 'mandatory' AND is_cold = false
ORDER BY usage_count DESC
LIMIT 20;
```

**Alvo**: efetividade_pct >= 80% para regras mandatory (vs 12% hoje).

### Sinal negativo — rollback criterios

- `[USER_RULES]` logs aparecem mas usuarios reportam regras ignoradas → bug no framing, nao rollout
- memoria_errors.log spike → rollback flag
- Latencia `_load_user_memories_for_context` > 500ms p95 → revisar query priority index

### Rollback plano

- **Nivel 1** (zero downtime): `AGENT_USER_RULES_CHANNEL=false` — desativa canal, sistema volta ao anterior
- **Nivel 2** (db): migration de backfill e reversivel via `UPDATE agent_memories SET priority='contextual'`
- **Nivel 3** (schema): `ALTER TABLE agent_memories DROP COLUMN priority` (perde metadata mas nao dados)

---

## Referencias

### Codigo atual

- Framing passivo: `app/agente/sdk/memory_injection.py:1047-1061` (tier1_texts + selected_tier2 todos renderizam como `<memory>`)
- Filtro estreito: `app/agente/sdk/memory_injection.py:360-368` (_build_operational_directives)
- Consolidator cego: `app/agente/services/memory_consolidator.py:62-65` (PROTECTED_PATHS apenas 2)
- Auto-save descritivo: `app/agente/services/pattern_analyzer.py:39-107` (PATTERN_SYSTEM_PROMPT)
- R0d existente: `app/agente/prompts/system_prompt.md:127-146`
- Admissao do problema: `app/agente/config/feature_flags.py:209-211`

### Memorias impactadas (producao Render)

- user_id=18, `/memories/preferences.xml` (id=397) → priority=mandatory
- user_id=18, `/memories/user.xml` (id=368) → priority=advisory
- user_id=0, `/memories/empresa/heuristicas/financeiro/baseline-de-extratos-formato-fixo.xml` (id=536 migrada) → priority=mandatory
- 8+ heuristicas empresa nivel 5 com importance>=0.7 → priority=advisory
