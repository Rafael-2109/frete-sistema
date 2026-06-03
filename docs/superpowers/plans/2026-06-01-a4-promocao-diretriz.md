<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# A4 — Promoção Automática de Diretriz (batch) — Implementation Plan

> **Papel:** A4 — Promoção Automática de Diretriz (batch) — Implementation Plan.

## Indice

- [CONTEXTO ANTI-DRIFT (ler antes de codar)](#contexto-anti-drift-ler-antes-de-codar)
- [FILE STRUCTURE](#file-structure)
- [DECISÕES DE DESIGN JÁ FECHADAS (não re-decidir)](#decisões-de-design-já-fechadas-não-re-decidir)
- [ESCOPO DE ESCRITA — RESOLVIDO PELA DOC (2026-06-01)](#escopo-de-escrita-resolvido-pela-doc-2026-06-01)
- [Task 1: Migration dupla + coluna `directive_status` em `AgentMemory`](#task-1-migration-dupla-coluna-directive_status-em-agentmemory)
- [Task 2: `_build_operational_directives` filtra por `directive_status` (alavanca de ativação)](#task-2-_build_operational_directives-filtra-por-directive_status-alavanca-de-ativação)
- [Task 3: `_persist_directive` real (escreve `status='shadow'`) — [Opção A]](#task-3-_persist_directive-real-escreve-statusshadow-opção-a)
- [Task 4: `run_directive_promotion_batch` + módulo D8 32](#task-4-run_directive_promotion_batch-módulo-d8-32)
- [Task 5: Self-audit, suíte completa, EXECUCAO.md](#task-5-self-audit-suíte-completa-execucaomd)
- [Self-Review (preenchido)](#self-review-preenchido)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans para implementar task-by-task. Steps usam checkbox (`- [ ]`).

**Goal:** Fechar o flywheel construindo o atuador parado "Distill→Deploy" — um job batch (D8 módulo 32) que varre PlanStates bem-sucedidos, propõe candidatas a diretriz, aplica anti-gaming R9 + gate A3, e PERSISTE a candidata como `directive_status='shadow'` (persistida para revisão, NUNCA injetada) — tudo flag-OFF, zero mudança de comportamento.

**Architecture:** Reaproveita 100% da lógica shadow já existente (`directive_promotion_service.propose_directive_from_plan` + `evaluate_and_promote` + `_tem_falha_odoo`). A4-batch adiciona: (1) migration dupla `directive_status` (coluna NOVA, NÃO redefine `effective_count` — veredito #3 da crítica), (2) `_persist_directive` real escrevendo `status='shadow'`, (3) orquestração batch `run_directive_promotion_batch`, (4) integração de `_build_operational_directives` filtrando `directive_status` (a ATIVAÇÃO `shadow→ativa` vira a alavanca). **Dupla segurança:** uma diretriz A4 só é injetada se `directive_status='ativa'` **E** `USE_OPERATIONAL_DIRECTIVES=ON` — ambos OFF/inalcançáveis em V1.

**Tech Stack:** Python 3.12 · Flask-SQLAlchemy 2.0 · APScheduler (módulo D8 em `sincronizacao_incremental_definitiva.py`) · pytest. Sem LLM novo, sem `claude -p`, sem fila RQ nova (batch roda INLINE no ciclo D8, é leve).

---

## CONTEXTO ANTI-DRIFT (ler antes de codar)

- **A4 varia DIRETRIZ (heurística empresa), NÃO código** (a A3 varia código). Não confundir.
- **"Offline-gate vs A/B de produção" JÁ está decidido** pela spec + dados PROD: spec PERMITE offline (`eixos/A-flywheel.md:266`); PROD tem **0 judge signal, 0 PlanStates, 0 baseline** e a instrumentação "qual diretriz rodou em qual turno" NÃO existe (crítica §C2/§4.2) → A/B de produção é **A4 V2** (depende de A1, não construído). **V1 = offline.**
- **A "regression-gate" da spec = o A3 periódico GLOBAL (módulo 28), NÃO um run per-candidato.** Não há golden dataset do agente PRINCIPAL (só 4 de subagentes), e `<operational_directives>` injeta no principal → gate per-candidato mediria a superfície errada. Não construir gate per-candidato.
- **Âncora ambiental Odoo R9 DOMINA** (`_tem_falha_odoo`, conservador erro→bloqueia) — anti-reward-hacking, já implementado e verificado ANTES do gate de score.
- **Gotcha worktree:** `export DATABASE_URL` da raiz (localhost) antes de pytest.
- **Gotcha persistência:** SSL-drop em invokes longos — N/A aqui (batch é curto, sem LLM), mas usar SAVEPOINT + commit explícito no contexto de job.

---

## FILE STRUCTURE

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `app/agente/models.py` | Coluna `directive_status` em `AgentMemory` (~L552, após `escopo`) | Modify |
| `scripts/migrations/2026_06_01_agent_memories_directive_status.py` | Migration Python (create_app + before/after) | Create |
| `scripts/migrations/2026_06_01_agent_memories_directive_status.sql` | Migration SQL idempotente (`ADD COLUMN IF NOT EXISTS`) | Create |
| `app/agente/sdk/memory_injection.py` | Filtro `directive_status IN (NULL,'ativa')` no seletor (L462-473) | Modify |
| `app/agente/services/directive_promotion_service.py` | `_persist_directive` real (status='shadow') + `run_directive_promotion_batch` | Modify |
| `app/agente/config/feature_flags.py` | Constantes lookback/limit/floor do batch (perto de L934) | Modify |
| `app/scheduler/sincronizacao_incremental_definitiva.py` | Módulo D8 32 (espelha 28-31) | Modify |
| `tests/agente/models/test_agent_memory_directive_status.py` | Coluna persiste/lê os 4 estados | Create |
| `tests/agente/sdk/test_directives_status_filter.py` | shadow NÃO injeta; ativa/NULL injeta; despromovida NÃO | Create |
| `tests/agente/services/test_directive_promotion.py` | EXTENDER: `_persist_directive` real + `run_directive_promotion_batch` | Modify |

---

## DECISÕES DE DESIGN JÁ FECHADAS (não re-decidir)

1. **Coluna NOVA `directive_status`** (não redefinir `effective_count` — crítica veredito #3; 3 consumidores acoplados a `effective_count`). Valores: `candidata|shadow|ativa|despromovida`; `NULL` = memória comum.
2. **Dupla segurança de injeção:** `_build_operational_directives` passa a injetar só `directive_status IS NULL` (legado, retrocompat) **OU** `'ativa'`. Diretrizes A4 nascem `'shadow'` → nunca injetadas até ativação. E ainda gated por `USE_OPERATIONAL_DIRECTIVES=OFF`.
3. **`baseline_score` do gate = floor configurável** (`AGENT_DIRECTIVE_MIN_QUALITY`, default 0.7), NÃO o golden por-subagente (não há baseline do agente principal). `candidate_score` = qualidade da sessão de origem (judge). Gate vira "não promove diretriz vinda de sessão de qualidade abaixo do floor" — complementa R9.
4. **`candidate_score` ABSTÉM se ausente:** se a sessão de origem não tem `outcome_signal['judge']['score']` (PROD hoje = 0 judge), o batch PULA a candidata (conservador). Em PROD V1 isso = no-op natural até A1 acumular sinal.
5. **Batch roda INLINE no ciclo D8** (leve: sweep DB + scoring, sem LLM/`claude -p`) → SEM fila RQ nova, SEM editar `worker_render.py`/`start_worker_render.sh`.
6. **Ativação `shadow→ativa` NÃO é construída em V1** — é revisão manual do Rafael (feature_flags.py:214 "ativar apos revisao manual das candidatas"). V1 para em persistir candidatas shadow.

---

## ESCOPO DE ESCRITA — RESOLVIDO PELA DOC (2026-06-01)

`PROMPT_PROXIMA_SESSAO_A4.md:51-56` ("O QUE FALTA — a A4-batch") lista explicitamente
**migration `directive_status` + `_persist_directive` real (hoje stub)** como escopo da A4-batch;
`eixos/A-flywheel.md:272` pressupõe escrita ("estado de cada diretiva … numa tabela").
A ÚNICA decisão aberta que a doc registra (offline-gate vs A/B de produção) já se resolve para
offline. **Portanto: construir o caminho de escrita real** (`_persist_directive` grava `status='shadow'`),
gated por `AGENT_DIRECTIVE_PROMOTION=OFF` (escrita só dispara com a flag ON, que respeita os 3 pré-reqs
documentados). **Todas as 5 tasks abaixo.** Em PROD com inputs vazios (0 PlanStates/judge) o batch é
no-op natural; risco zero. (Uma alternativa "log-only" foi descartada — não está na doc.)

---

## Task 1: Migration dupla + coluna `directive_status` em `AgentMemory`

**Files:**
- Modify: `app/agente/models.py` (classe `AgentMemory`, após `escopo` ~L552)
- Create: `scripts/migrations/2026_06_01_agent_memories_directive_status.py`
- Create: `scripts/migrations/2026_06_01_agent_memories_directive_status.sql`
- Test: `tests/agente/models/test_agent_memory_directive_status.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/agente/models/test_agent_memory_directive_status.py
"""A4 — coluna directive_status em AgentMemory (candidata|shadow|ativa|despromovida)."""
import pytest
from app import db
from app.agente.models import AgentMemory


class TestDirectiveStatusColumn:
    def test_coluna_existe_e_default_none(self, app_context):
        mem = AgentMemory(user_id=0, path='/memories/empresa/heuristicas/t1.xml',
                          content='<nivel>5</nivel><prescricao>x</prescricao>')
        db.session.add(mem)
        db.session.flush()
        assert mem.directive_status is None  # memória comum
        db.session.rollback()

    def test_aceita_os_quatro_estados(self, app_context):
        for st in ('candidata', 'shadow', 'ativa', 'despromovida'):
            mem = AgentMemory(user_id=0, path=f'/memories/empresa/heuristicas/{st}.xml',
                              content='<nivel>5</nivel><prescricao>x</prescricao>',
                              directive_status=st)
            db.session.add(mem)
            db.session.flush()
            assert mem.directive_status == st
            db.session.rollback()
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `export DATABASE_URL=$(grep -E '^DATABASE_URL=' /home/rafaelnascimento/projetos/frete_sistema/.env | head -1 | cut -d= -f2-) && python -m pytest tests/agente/models/test_agent_memory_directive_status.py -v`
Expected: FAIL — `TypeError: 'directive_status' is an invalid keyword argument` (coluna inexistente).

- [ ] **Step 3: Adicionar a coluna no model**

Em `app/agente/models.py`, após a coluna `escopo` (~L552) e antes de `created_by`:

```python
    # ── A4 (Onda 3): promoção automática de diretriz ──
    # NULL = memória comum. candidata|shadow|ativa|despromovida = ciclo de vida
    # de diretriz promovida. Coluna NOVA (NÃO redefinir effective_count —
    # 3 consumidores acoplados). _build_operational_directives injeta só
    # NULL (legado) OU 'ativa'. Ativação shadow→ativa = revisão manual.
    directive_status = db.Column(db.String(20), nullable=True)
```

- [ ] **Step 4: Criar a migration Python (idempotente, before/after)**

```python
# scripts/migrations/2026_06_01_agent_memories_directive_status.py
"""A4: adiciona agent_memories.directive_status (candidata|shadow|ativa|despromovida)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text, inspect


def _tem_coluna():
    insp = inspect(db.engine)
    return any(c['name'] == 'directive_status' for c in insp.get_columns('agent_memories'))


def main():
    app = create_app()
    with app.app_context():
        antes = _tem_coluna()
        print(f"[A4 migration] directive_status existe ANTES? {antes}")
        if not antes:
            db.session.execute(text(
                "ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS directive_status VARCHAR(20)"
            ))
            db.session.commit()
        depois = _tem_coluna()
        print(f"[A4 migration] directive_status existe DEPOIS? {depois}")
        assert depois, "Falha: coluna não criada"
        print("[A4 migration] OK")


if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Criar a migration SQL idempotente (Render Shell)**

```sql
-- scripts/migrations/2026_06_01_agent_memories_directive_status.sql
-- A4: directive_status (candidata|shadow|ativa|despromovida). NULL = memória comum.
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS directive_status VARCHAR(20);
```

- [ ] **Step 6: Rodar a migration local**

Run: `export DATABASE_URL=$(grep -E '^DATABASE_URL=' /home/rafaelnascimento/projetos/frete_sistema/.env | head -1 | cut -d= -f2-) && python scripts/migrations/2026_06_01_agent_memories_directive_status.py`
Expected: imprime `existe DEPOIS? True` + `OK`.

- [ ] **Step 7: Rodar o teste e ver passar**

Run: `python -m pytest tests/agente/models/test_agent_memory_directive_status.py -v`
Expected: PASS (2 testes).

- [ ] **Step 8: Commit**

```bash
git add app/agente/models.py scripts/migrations/2026_06_01_agent_memories_directive_status.py scripts/migrations/2026_06_01_agent_memories_directive_status.sql tests/agente/models/test_agent_memory_directive_status.py
git commit -m "feat(a4): coluna directive_status em agent_memories (migration dupla)"
```

---

## Task 2: `_build_operational_directives` filtra por `directive_status` (alavanca de ativação)

**Files:**
- Modify: `app/agente/sdk/memory_injection.py:462-473` (query de candidatos)
- Test: `tests/agente/sdk/test_directives_status_filter.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/agente/sdk/test_directives_status_filter.py
"""A4 — _build_operational_directives injeta só directive_status NULL (legado) OU 'ativa'."""
from unittest.mock import patch
from app import db
from app.agente.models import AgentMemory
from app.agente.sdk.memory_injection import _build_operational_directives

_CONTENT = '<titulo>T</titulo><when>w</when><prescricao>faça x</prescricao><nivel>5</nivel>'


def _mk(path, status):
    m = AgentMemory(user_id=0, path=path, content=_CONTENT,
                    importance_score=0.9, directive_status=status)
    db.session.add(m)
    return m


class TestDirectiveStatusFilter:
    def test_shadow_nao_injeta_ativa_e_null_injetam(self, app_context):
        _mk('/memories/empresa/heuristicas/leg.xml', None)       # legado → injeta
        _mk('/memories/empresa/heuristicas/atv.xml', 'ativa')    # ativa → injeta
        _mk('/memories/empresa/heuristicas/shd.xml', 'shadow')   # shadow → NÃO
        _mk('/memories/empresa/heuristicas/dep.xml', 'despromovida')  # NÃO
        db.session.flush()
        with patch('app.agente.config.feature_flags.USE_OPERATIONAL_DIRECTIVES', True), \
             patch('app.agente.sdk.memory_injection.USE_OPERATIONAL_DIRECTIVES', True, create=True):
            out = _build_operational_directives(user_id=5) or ''
        assert 'faça x' in out          # injetou ao menos os 2 elegíveis
        # shadow/despromovida têm o MESMO conteúdo; provamos exclusão pela CONTAGEM:
        assert out.count('<directive') == 2
        db.session.rollback()
```

> Nota: a flag `USE_OPERATIONAL_DIRECTIVES` é importada DENTRO da função (L446-450), então o patch precisa alvejar o ponto de import. Confirmar o alvo correto ao rodar (pode ser só `app.agente.config.feature_flags.USE_OPERATIONAL_DIRECTIVES` já que é importado lazy).

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/sdk/test_directives_status_filter.py -v`
Expected: FAIL — `out.count('<directive')` == 4 (sem filtro, todos os 4 entram).

- [ ] **Step 3: Adicionar o filtro na query**

Em `app/agente/sdk/memory_injection.py`, dentro de `_build_operational_directives`, na query (~L462-473), adicionar a cláusula `directive_status`:

```python
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
            # A4: injeta só legado (NULL) OU ativa. Exclui shadow/candidata/despromovida.
            sql_or(
                AgentMemory.directive_status.is_(None),
                AgentMemory.directive_status == 'ativa',
            ),
        ).order_by(
            AgentMemory.effective_count.desc()
        ).limit(MANDATORY_MAX_COUNT * 3).all()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/agente/sdk/test_directives_status_filter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/memory_injection.py tests/agente/sdk/test_directives_status_filter.py
git commit -m "feat(a4): _build_operational_directives filtra directive_status (alavanca shadow->ativa)"
```

---

## Task 3: `_persist_directive` real (escreve `status='shadow'`) — [Opção A]

**Files:**
- Modify: `app/agente/services/directive_promotion_service.py` (substitui o stub L218-247)
- Test: `tests/agente/services/test_directive_promotion.py` (EXTENDER classe `TestPersistDirective`)

- [ ] **Step 1: Escrever os testes que falham**

```python
# adicionar em tests/agente/services/test_directive_promotion.py
class TestPersistDirectiveReal:
    def test_persiste_como_shadow_com_path_e_conteudo_selecionavel(self, app_context):
        from app.agente.services.directive_promotion_service import _persist_directive
        from app.agente.models import AgentMemory
        from app.agente.sdk.memory_injection import _is_nivel_5
        cand = {'titulo': 'Fluxo: consultar saldo [2 passos]',
                'when': 'Quando o agente executa: consultar saldo; validar lote',
                'prescricao': 'Sequência: consultar saldo → validar lote',
                'source_session_id': 'sess-1', 'status': 'candidata'}
        mem_id = _persist_directive(cand)
        mem = AgentMemory.query.get(mem_id)
        assert mem.user_id == 0
        assert mem.directive_status == 'shadow'
        assert mem.path.startswith('/memories/empresa/heuristicas/')
        assert mem.importance_score >= 0.7
        assert _is_nivel_5((mem.content or '').lower())     # selecionável pelo builder
        assert '<prescricao>' in mem.content                 # builder precisa de presc
        db.session.rollback()

    def test_idempotente_nao_duplica(self, app_context):
        from app.agente.services.directive_promotion_service import _persist_directive
        from app.agente.models import AgentMemory
        cand = {'titulo': 'Fluxo X', 'when': 'w', 'prescricao': 'faça y',
                'source_session_id': 's2', 'status': 'candidata'}
        id1 = _persist_directive(cand)
        id2 = _persist_directive(cand)          # mesmo título → mesmo path
        assert id1 == id2
        assert AgentMemory.query.filter_by(path=AgentMemory.query.get(id1).path).count() == 1
        db.session.rollback()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/services/test_directive_promotion.py::TestPersistDirectiveReal -v`
Expected: FAIL — `NotImplementedError` (stub atual).

- [ ] **Step 3: Implementar `_persist_directive` real**

Substituir o stub (L218-247) por:

```python
import re as _re


def _slug_titulo(titulo: str) -> str:
    """Slug kebab-case ASCII a partir do título (determinístico, idempotente)."""
    base = (titulo or 'diretriz').lower().strip()
    base = _re.sub(r'[^a-z0-9]+', '-', base).strip('-')
    return (base or 'diretriz')[:80]


def _formatar_xml_diretriz(candidata: dict) -> str:
    """Monta o conteúdo XML da diretriz. Inclui <nivel>5</nivel> (passa _is_nivel_5)
    e <prescricao> (exigido por _build_operational_directives)."""
    from app.agente.sdk._sanitization import xml_escape  # mesmo helper do builder
    titulo = xml_escape(candidata.get('titulo', ''))
    when = xml_escape(candidata.get('when', ''))
    presc = xml_escape(candidata.get('prescricao', ''))
    origem = xml_escape(candidata.get('source_session_id', ''))
    return (
        '<heuristica>\n'
        '  <nivel>5</nivel>\n'
        f'  <titulo>{titulo}</titulo>\n'
        f'  <when>{when}</when>\n'
        f'  <prescricao>{presc}</prescricao>\n'
        f'  <origem>promovida automaticamente da sessão {origem}</origem>\n'
        '</heuristica>'
    )


def _persist_directive(candidata: dict) -> int:
    """Persiste diretriz candidata como AgentMemory empresa, directive_status='shadow'.

    Idempotente por path (slug do título): se já existe, retorna o id existente
    sem duplicar. SHADOW = persistida mas NUNCA injetada (builder injeta só
    NULL/ativa). Ativação shadow→ativa = revisão manual (fora do escopo V1).

    Returns: id da AgentMemory (nova ou existente).
    """
    from app.agente.models import AgentMemory
    from app import db

    slug = _slug_titulo(candidata.get('titulo', ''))
    path = f'/memories/empresa/heuristicas/{slug}.xml'

    existente = AgentMemory.query.filter_by(user_id=0, path=path).first()
    if existente is not None:
        logger.info(f"[directive_promotion] _persist: já existe path={path!r} id={existente.id} → no-op")
        return existente.id

    mem = AgentMemory(
        user_id=0,
        path=path,
        content=_formatar_xml_diretriz(candidata),
        is_directory=False,
        importance_score=0.7,           # = MANDATORY_IMPORTANCE_THRESHOLD
        escopo='empresa',
        created_by=0,                   # Sistema
        directive_status='shadow',      # persistida, NÃO injetada
    )
    db.session.add(mem)
    db.session.flush()                  # popula mem.id; commit fica com o caller (job)
    logger.info(
        f"[directive_promotion] _persist: criada SHADOW id={mem.id} path={path!r} "
        f"origem={candidata.get('source_session_id', '?')!r}"
    )
    return mem.id
```

> **Verificar ao implementar:** o helper de escape — o builder usa `xml_escape` (memory_injection.py:531). Confirmar o módulo correto (`_sanitization.xml_escape` ou o import que o builder usa). Se vier de outro lugar, ajustar o import.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/agente/services/test_directive_promotion.py::TestPersistDirectiveReal -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Ajustar o teste legado do stub**

O teste `TestShadowFlag::test_persist_directive_e_stub_documentado` (L348-366) espera `NotImplementedError` — agora obsoleto. Substituir por um teste que confirma que `evaluate_and_promote` em shadow (flag OFF) NÃO chama `_persist_directive` (a dupla segurança continua):

```python
    def test_evaluate_shadow_nao_persiste_com_flag_off(self, app_context):
        """Mesmo com would_promote, flag OFF → _persist_directive NÃO é chamado."""
        from app.agente.services import directive_promotion_service as svc
        cand = {'titulo': 'X', 'when': 'w', 'prescricao': 'p', 'source_session_id': 's', 'status': 'candidata'}
        with patch.object(svc, '_tem_falha_odoo', return_value=False), \
             patch.object(svc, '_persist_directive') as mock_persist:
            r = svc.evaluate_and_promote(cand, baseline_score=0.7, candidate_score=0.8)
        assert r['decision'] == 'would_promote'
        mock_persist.assert_not_called()   # shadow: evaluate só LOGA (caller/batch decide persistir)
```

- [ ] **Step 6: Rodar e ver passar + commit**

Run: `python -m pytest tests/agente/services/test_directive_promotion.py -v`
Expected: PASS.

```bash
git add app/agente/services/directive_promotion_service.py tests/agente/services/test_directive_promotion.py
git commit -m "feat(a4): _persist_directive real escreve directive_status=shadow (idempotente)"
```

---

## Task 4: `run_directive_promotion_batch` + módulo D8 32

**Files:**
- Modify: `app/agente/services/directive_promotion_service.py` (nova função `run_directive_promotion_batch`)
- Modify: `app/agente/config/feature_flags.py` (constantes lookback/limit/floor, perto de L934)
- Modify: `app/scheduler/sincronizacao_incremental_definitiva.py` (módulo 32, após L2189)
- Test: `tests/agente/services/test_directive_promotion.py` (classe `TestRunBatch`)

- [ ] **Step 1: Escrever os testes que falham**

```python
class TestRunBatch:
    def _sess(self, sid, plan, steps_judge=None):
        """Mock de AgentSession com data['plan'] e (opcional) agent_step judge."""
        from unittest.mock import MagicMock
        s = MagicMock()
        s.session_id = sid
        s.data = {'plan': plan}
        return s

    def test_flag_off_no_op(self, app_context):
        from app.agente.services import directive_promotion_service as svc
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', False, create=True):
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r == {'candidatos': 0, 'promovidos': 0, 'abstencoes': 0, 'rejeitados': 0}

    def test_abstem_sem_judge_score(self, app_context):
        """Sessão com plano OK mas sem judge signal → abstém (não promove)."""
        from app.agente.services import directive_promotion_service as svc
        plan = {'steps': {'1': {'subject': 'consultar', 'status': 'completed'}}}
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', True, create=True), \
             patch.object(svc, '_buscar_sessoes_com_plano_concluido', return_value=[self._sess('s1', plan)]), \
             patch.object(svc, '_quality_score_da_sessao', return_value=None), \
             patch.object(svc, '_persist_directive') as mock_persist:
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r['abstencoes'] == 1 and r['promovidos'] == 0
        mock_persist.assert_not_called()

    def test_promove_quando_qualidade_e_sem_falha_odoo(self, app_context):
        from app.agente.services import directive_promotion_service as svc
        plan = {'steps': {'1': {'subject': 'consultar', 'status': 'completed'}}}
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', True, create=True), \
             patch.object(svc, '_buscar_sessoes_com_plano_concluido', return_value=[self._sess('s1', plan)]), \
             patch.object(svc, '_quality_score_da_sessao', return_value=0.85), \
             patch.object(svc, '_tem_falha_odoo', return_value=False), \
             patch.object(svc, '_persist_directive', return_value=123) as mock_persist:
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r['promovidos'] == 1
        mock_persist.assert_called_once()

    def test_rejeita_falha_odoo_dominante(self, app_context):
        from app.agente.services import directive_promotion_service as svc
        plan = {'steps': {'1': {'subject': 'x', 'status': 'completed'}}}
        with patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', True, create=True), \
             patch.object(svc, '_buscar_sessoes_com_plano_concluido', return_value=[self._sess('s1', plan)]), \
             patch.object(svc, '_quality_score_da_sessao', return_value=0.99), \
             patch.object(svc, '_tem_falha_odoo', return_value=True), \
             patch.object(svc, '_persist_directive') as mock_persist:
            r = svc.run_directive_promotion_batch(lookback_hours=24, limit=50)
        assert r['rejeitados'] == 1 and r['promovidos'] == 0
        mock_persist.assert_not_called()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/services/test_directive_promotion.py::TestRunBatch -v`
Expected: FAIL — `AttributeError: run_directive_promotion_batch`.

- [ ] **Step 3: Adicionar as constantes em feature_flags.py**

Perto de L934 (após `AGENT_DIRECTIVE_PROMOTION`):

```python
# A4-batch: parâmetros do varredor (módulo D8 32). Só atuam com AGENT_DIRECTIVE_PROMOTION=ON.
AGENT_DIRECTIVE_LOOKBACK_HOURS = int(os.getenv("AGENT_DIRECTIVE_LOOKBACK_HOURS", "24"))
AGENT_DIRECTIVE_BATCH_LIMIT = int(os.getenv("AGENT_DIRECTIVE_BATCH_LIMIT", "50"))
# floor de qualidade da sessão de origem (baseline do gate; não há golden do agente principal).
AGENT_DIRECTIVE_MIN_QUALITY = float(os.getenv("AGENT_DIRECTIVE_MIN_QUALITY", "0.7"))
```

- [ ] **Step 4: Implementar o batch no service**

Em `directive_promotion_service.py`, adicionar imports lazy + a função orquestradora + 2 helpers (`_buscar_sessoes_com_plano_concluido`, `_quality_score_da_sessao`):

```python
def _buscar_sessoes_com_plano_concluido(lookback_hours: int, limit: int) -> list:
    """Sessões recentes (lookback) cujo data['plan'] tem TODOS os steps completed.
    Filtro fino (all-completed) fica em propose_directive_from_plan; aqui só janela+plan."""
    from app.agente.models import AgentSession
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    corte = agora_utc_naive() - timedelta(hours=lookback_hours)
    # data->'plan' presente (data é JSONB) — usa o operador de existência.
    rows = AgentSession.query.filter(
        AgentSession.updated_at >= corte,
        AgentSession.data.isnot(None),
    ).order_by(AgentSession.updated_at.desc()).limit(limit).all()
    return [s for s in rows if isinstance(s.data, dict) and s.data.get('plan')]


def _quality_score_da_sessao(session_id: str):
    """Score de qualidade da sessão (média dos judge scores dos seus agent_step).
    None se não houver judge signal (conservador → abstém)."""
    from app.agente.models import AgentStep
    steps = AgentStep.query.filter_by(session_id=session_id).all()
    scores = []
    for st in steps:
        sig = st.outcome_signal or {}
        judge = sig.get('judge') if isinstance(sig, dict) else None
        if isinstance(judge, dict) and judge.get('score') is not None:
            try:
                scores.append(float(judge['score']))
            except (TypeError, ValueError):
                pass
    if not scores:
        return None
    # judge.score pode estar em 0-100 (step_judge) — normaliza p/ 0-1 se >1.
    media = sum(scores) / len(scores)
    return media / 100.0 if media > 1.0 else media


def run_directive_promotion_batch(lookback_hours: int = 24, limit: int = 50) -> dict:
    """Varredor A4-batch (D8 módulo 32). Flag-gated por AGENT_DIRECTIVE_PROMOTION.

    Para cada sessão recente com plano 100% concluído:
      propose → quality_score (abstém se None) → evaluate_and_promote
      (R9 anti-gaming DOMINA → gate vs floor) → se would_promote: _persist_directive (shadow).

    Best-effort: nunca levanta. Retorna contadores.
    """
    from app.agente.config.feature_flags import (
        AGENT_DIRECTIVE_PROMOTION, AGENT_DIRECTIVE_MIN_QUALITY,
    )
    contadores = {'candidatos': 0, 'promovidos': 0, 'abstencoes': 0, 'rejeitados': 0}
    if not AGENT_DIRECTIVE_PROMOTION:
        return contadores

    try:
        sessoes = _buscar_sessoes_com_plano_concluido(lookback_hours, limit)
    except Exception as exc:
        logger.error(f"[directive_promotion] batch: erro ao buscar sessões: {exc}")
        return contadores

    for s in sessoes:
        try:
            candidata = propose_directive_from_plan(s.data.get('plan'), s.session_id)
            if candidata is None:
                continue
            contadores['candidatos'] += 1

            score = _quality_score_da_sessao(s.session_id)
            if score is None:
                contadores['abstencoes'] += 1
                logger.info(f"[directive_promotion] batch: abstém session={s.session_id!r} (sem judge)")
                continue

            resultado = evaluate_and_promote(
                candidata,
                baseline_score=AGENT_DIRECTIVE_MIN_QUALITY,
                candidate_score=score,
            )
            if resultado.get('decision') == _DECISION_WOULD_PROMOTE:
                _persist_directive(candidata)      # escreve shadow (Opção A)
                contadores['promovidos'] += 1
            else:
                contadores['rejeitados'] += 1
        except Exception as exc:
            logger.error(f"[directive_promotion] batch: erro session={getattr(s, 'session_id', '?')!r}: {exc}")

    try:
        from app import db
        db.session.commit()
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
    logger.info(f"[directive_promotion] batch concluído: {contadores}")
    return contadores
```

> Adicionar no topo do módulo: `from app.agente.config.feature_flags import AGENT_DIRECTIVE_PROMOTION` NÃO — manter import lazy dentro da função (para os testes patcharem `svc.AGENT_DIRECTIVE_PROMOTION`). Conferir: os testes patcham `svc.AGENT_DIRECTIVE_PROMOTION` com `create=True`, então o import lazy precisa atribuir ao namespace do módulo OU os testes patcham o ponto de import. Ajuste recomendado: importar no topo `from app.agente.config.feature_flags import AGENT_DIRECTIVE_PROMOTION` para o patch `patch.object(svc, 'AGENT_DIRECTIVE_PROMOTION', ...)` funcionar sem `create=True`. (Decidir na implementação; espelha o padrão dos enqueuers que importam o `*_ENABLED` no módulo do scheduler.)

- [ ] **Step 5: Adicionar o módulo D8 32 (espelha 28-31)**

Em `sincronizacao_incremental_definitiva.py`, após o bloco do módulo 31 (L2189) e ANTES do "Limpar conexões" (L2191):

```python
        # ── 3️⃣2️⃣ DIRECTIVE PROMOTION — A4-batch (32º módulo, shadow/persist) ──
        # Onda 3 / A4. Flag AGENT_DIRECTIVE_PROMOTION default OFF → no-op.
        # Quando ON: varre AgentSessions recentes c/ plano 100% concluído → propõe
        # candidata → R9 anti-gaming DOMINA → gate vs floor → persiste directive_status='shadow'
        # (NUNCA injetada até ativação manual). Roda TODO ciclo (cap por limit).
        # Best-effort: nunca falha o cron. NÃO entra em modulos_sync.
        _t_step = time.time()

        if DIRECTIVE_PROMOTION_ENABLED:
            try:
                from app.agente.services.directive_promotion_service import run_directive_promotion_batch

                _dp_result = run_directive_promotion_batch(
                    lookback_hours=DIRECTIVE_LOOKBACK_HOURS,
                    limit=DIRECTIVE_BATCH_LIMIT,
                )
                logger.info(
                    f"[DIRECTIVE_PROMOTION] candidatos={_dp_result.get('candidatos', 0)} "
                    f"promovidos={_dp_result.get('promovidos', 0)} "
                    f"abstencoes={_dp_result.get('abstencoes', 0)} "
                    f"rejeitados={_dp_result.get('rejeitados', 0)}"
                )
            except Exception as e:
                logger.error(f"[DIRECTIVE_PROMOTION] Erro no modulo 32: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

        logger.info(f"   [TIMER] Step 32 (Directive Promotion): {time.time() - _t_step:.1f}s")
```

E no topo do arquivo (onde `JUDGE_ENQUEUER_ENABLED` etc. são definidos), adicionar:

```python
from app.agente.config.feature_flags import (
    AGENT_DIRECTIVE_PROMOTION as DIRECTIVE_PROMOTION_ENABLED,
    AGENT_DIRECTIVE_LOOKBACK_HOURS as DIRECTIVE_LOOKBACK_HOURS,
    AGENT_DIRECTIVE_BATCH_LIMIT as DIRECTIVE_BATCH_LIMIT,
)
```

> Conferir o ponto exato onde os outros `*_ENABLED` são importados (grep `JUDGE_ENQUEUER_ENABLED`) e adicionar junto.

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/agente/services/test_directive_promotion.py::TestRunBatch -v`
Expected: PASS (4 testes).

- [ ] **Step 7: Commit**

```bash
git add app/agente/services/directive_promotion_service.py app/agente/config/feature_flags.py app/scheduler/sincronizacao_incremental_definitiva.py tests/agente/services/test_directive_promotion.py
git commit -m "feat(a4): run_directive_promotion_batch + modulo D8 32 (flag-OFF, INLINE)"
```

---

## Task 5: Self-audit, suíte completa, EXECUCAO.md

- [ ] **Step 1: Suíte COMPLETA do agente (pega regressão que o teste isolado não vê — lição A3)**

Run: `export DATABASE_URL=$(grep -E '^DATABASE_URL=' /home/rafaelnascimento/projetos/frete_sistema/.env | head -1 | cut -d= -f2-) && python -m pytest tests/agente/ -q`
Expected: baseline anterior (668 na main; nesta branch confirmar nº pré-A4) + os novos testes A4, **0 regressões**. As 2 falhas `pending_questions` foram resolvidas (Tarefa 2a) — esperar 0 failed.

- [ ] **Step 2: Self-audit (precision-engineer)**

Verificar manualmente:
- [ ] `directive_status` NULL = comportamento legado intacto (builder injeta NULL/ativa).
- [ ] Dupla segurança: shadow nunca injetada (Task 2) + `USE_OPERATIONAL_DIRECTIVES` OFF.
- [ ] R9 `_tem_falha_odoo` verificado ANTES do gate (inalterado).
- [ ] Flag `AGENT_DIRECTIVE_PROMOTION` OFF → batch no-op (Task 4 test).
- [ ] Migration dupla (Python + SQL idempotente) presente.
- [ ] Nenhum import circular novo (service ↔ memory_injection ↔ models).
- [ ] `agora_utc_naive` usado (timezone hook não bloqueia).

- [ ] **Step 3: Atualizar EXECUCAO.md**

Marcar A4 (ONDA 3) como "✅ COMPLETO (V1 offline, flag-OFF)" com o nº do commit, e adicionar linha no LOG DE EXECUÇÃO descrevendo: migration directive_status, _persist_directive real (shadow), batch módulo 32, builder integration; pré-reqs PROD pendentes (PlanStates+judge+baseline acumularem); regression-gate = A3 periódico; ativação shadow→ativa = manual.

- [ ] **Step 4: Commit final**

```bash
git add docs/blueprint-agente/EXECUCAO.md
git commit -m "docs(a4): EXECUCAO.md — A4 V1 offline COMPLETO (flag-OFF)"
```

---

## Self-Review (preenchido)

**Spec coverage:** §2.3 pipeline (candidata→gate→promove) → Tasks 3+4; Ruptura #2 (ligar USE_OPERATIONAL_DIRECTIVES com segurança) → Task 2 (alavanca) + dupla segurança; anti-gaming C1/R9 → reusa `_tem_falha_odoo` (Task 4); migration `directive_status` (PROMPT "o que falta") → Task 1; `_persist_directive` real → Task 3; batch D8 → Task 4. A/B de produção + drift auto-despromove = **A4 V2** (fora de escopo, documentado).

**Placeholder scan:** sem TBD/TODO; código completo em cada step; pontos "conferir ao implementar" são verificações de import (helper xml_escape, ponto de patch da flag), não lacunas de lógica.

**Type consistency:** `directive_status` (str) consistente em model/migration/builder/persist; `run_directive_promotion_batch(lookback_hours, limit)→dict{candidatos,promovidos,abstencoes,rejeitados}` consistente entre teste, service e módulo 32; `_persist_directive(candidata: dict)→int` consistente.

**Lacuna conhecida (aceita):** `candidate_score` depende do judge signal (A1), vazio em PROD → batch abstém até acumular. Em V1 isso é no-op natural seguro, não bug.
