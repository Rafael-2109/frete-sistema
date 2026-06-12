<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano executavel da Fase 2 (captura de scripts ad-hoc -> cluster de demanda -> sugestao de skill na Inbox)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->

# Aprendizado ad-hoc → skill (Fase 2) — Implementation Plan

> **Papel:** plano executavel task-by-task da Fase 2 da spec
> `docs/superpowers/specs/2026-06-12-aprendizado-adhoc-fase2-design.md` —
> captura de Bash substantivo pos-sessao, cluster de demanda e sugestao de
> skill na Inbox de Aprovacao. **Abra quando:** for implementar a Fase 2.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capturar Bash substantivo dos transcripts pos-sessao do Agente Web, clusterizar por demanda (pgvector) e propor na Inbox de Aprovacao: skill nova, extensao de skill, conserto de roteamento (Fase 1) ou descarte com trava.

**Architecture:** Job RQ pos-sessao (espelho exato da Fase 1) le o transcript cru via SQL sincrono em `claude_session_store`, extrai candidatos Bash (parser puro), enriquece com Haiku (`problema` ≤100c), embedda via Voyage, clusteriza incrementalmente (vizinho cosine ≥0.85) e dispara Sonnet (cap diario) quando threshold cruza ou gap nomeado aparece → `AgentImprovementDialogue(category='skill_suggestion')`.

**Tech Stack:** Flask/SQLAlchemy, RQ, pgvector (`Vector(1024)`), Voyage `voyage-4-lite`, Anthropic Haiku/Sonnet (reuso `_call_anthropic` da Fase 1), pytest.

## Indice

- [Decisoes de implementacao](#decisoes-de-implementacao-refinam-a-spec--registradas-na-task-9)
- [File Structure](#file-structure)
- [Task 0: Worktree](#task-0-worktree)
- [Task 1: Migração par + model `AgentAdhocScript`](#task-1-migracao-par--model-agentadhocscript)
- [Task 2: Parser do transcript](#task-2-parser-do-transcript-funcoes-puras)
- [Task 3: Filtro "Bash substantivo"](#task-3-filtro-bash-substantivo)
- [Task 4: Extração Haiku com fallback](#task-4-extracao-haiku-problema--motivo_fallback-com-fallback)
- [Task 5: Embedding + clustering incremental](#task-5-embedding--clustering-incremental)
- [Task 6: Flags](#task-6-flags)
- [Task 7: Disparo](#task-7-disparo-thresholds--bypass--caps--dedup--dialogue)
- [Task 8: Orquestração + job RQ + gatilho](#task-8-orquestracao--job-rq--gatilho-pos-sessao)
- [Task 9: Validação com transcript real + spec/memória](#task-9-validacao-com-transcript-real--atualizacoes-de-specmemoria)
- [Task 10: Finalização](#task-10-finalizacao)
- [Self-review](#self-review-executado-na-escrita)

---

## Decisoes de implementacao (refinam a spec — registradas na Task 9)

1. **Fonte do transcript = SQL SINCRONO direto em `claude_session_store`**
   (`SELECT entry ... WHERE session_id=:sdk_sid AND subpath='' ORDER BY seq`) em vez
   do adapter async (`session_store_adapter.load` exige asyncpg/event loop — ruim em
   job RQ). Mesma tabela, mesmo conteudo. `sdk_session_id` via
   `AgentSession.get_sdk_session_id()` (`app/agente/models.py:288`).
2. **`skill_relacionada` vem do transcript cru** (block `tool_use` name=`Skill`
   anterior ao Bash) — superficie-agnostico: cobre Teams nativamente. O edge case
   "Teams degradado" da spec esta RESOLVIDO por construcao.
3. **Debito Teams `tool_name` JA FECHADO** (commit `ede93a0e2`,
   `app/teams/services.py:515` `_enrich_tool_name`) — a task prevista caiu do plano.
4. tipo_gap na captura: `skill_insuficiente` exige skill na janela E motivo extraido;
   skill na janela sem motivo conclusivo → `desconhecido`; sem skill → `sem_skill`.
   `skill_nao_usada`/`one_off` so existem pos-julgamento Sonnet (Task 7).

## File Structure

| Arquivo | Responsabilidade |
|---------|------------------|
| `scripts/migrations/2026_06_12_agent_adhoc_script.sql` + `.py` (Create) | tabela + indices (par DDL+Python) |
| `app/agente/models.py` (Modify) | model `AgentAdhocScript` (apos `AgentSkillEffectiveness`, ~linha 2453) |
| `app/agente/services/adhoc_capture_service.py` (Create) | TODO o pipeline: parser, filtro, Haiku, embed, cluster, disparo, orquestracao |
| `app/agente/config/feature_flags.py` (Modify) | 6 flags (apos bloco AGENT_SKILL_EVAL, ~linha 1202) |
| `app/agente/workers/background_jobs.py` (Modify) | `adhoc_capture_job` + `try_enqueue_adhoc_capture` (apos skill_effectiveness, ~linha 280) |
| `app/agente/routes/_helpers.py` (Modify) | `_maybe_trigger_adhoc_capture` + chamada em `run_post_session_processing` |
| `tests/agente/services/test_adhoc_capture.py` (Create) | toda a cobertura pytest |

---

### Task 0: Worktree

- [ ] **Step 0.1:** Usar a skill `superpowers:using-git-worktrees` para criar worktree `feat/agente-adhoc-fase2` a partir de `origin/main` (regra Rafael: tarefa nova = worktree). Symlink `.env` da raiz (gotcha worktree: sem `.env` cai em SQLite): `ln -s /home/rafaelnascimento/projetos/frete_sistema/.env <worktree>/.env`. Validar: `git branch --show-current` → `feat/agente-adhoc-fase2`.

---

### Task 1: Migracao par + model AgentAdhocScript

**Files:**
- Create: `scripts/migrations/2026_06_12_agent_adhoc_script.sql`
- Create: `scripts/migrations/2026_06_12_agent_adhoc_script.py`
- Modify: `app/agente/models.py` (inserir apos `AgentSkillEffectiveness`, que termina ~linha 2452)
- Test: `tests/agente/services/test_adhoc_capture.py`

- [ ] **Step 1.1: Escrever o teste que falha**

```python
"""Testes da Fase 2 — captura de scripts ad-hoc (spec 2026-06-12)."""
import pytest


class TestModel:
    def test_model_roundtrip(self, db):
        from app.agente.models import AgentAdhocScript
        row = AgentAdhocScript(
            session_id="sess-test-adhoc-1", user_id=1,
            problema="exportar excel multi-aba",
            command_masked="python -c 'import pandas...'",
            contexto_user_msg="exporta em 3 abas",
            skill_relacionada="exportando-arquivos",
            tipo_gap="skill_insuficiente",
            motivo_fallback="exportar.py so gera 1 aba",
            retries_sessao=2,
        )
        db.session.add(row)
        db.session.flush()
        assert row.id is not None
        assert row.cluster_id is None  # setado pelo clustering, nao pelo insert
        db.session.rollback()
```

- [ ] **Step 1.2: Rodar e ver falhar**

Run: `pytest tests/agente/services/test_adhoc_capture.py::TestModel -x -q`
Expected: FAIL `ImportError: cannot import name 'AgentAdhocScript'`

- [ ] **Step 1.3: DDL** — `scripts/migrations/2026_06_12_agent_adhoc_script.sql`:

```sql
CREATE TABLE IF NOT EXISTS agent_adhoc_script (
    id               SERIAL PRIMARY KEY,
    session_id       VARCHAR(64) NOT NULL,
    user_id          INTEGER NOT NULL REFERENCES usuarios(id),
    problema         VARCHAR(120),
    command_masked   TEXT NOT NULL,
    contexto_user_msg TEXT,
    skill_relacionada VARCHAR(80),
    tipo_gap         VARCHAR(20) NOT NULL DEFAULT 'desconhecido',
    motivo_fallback  VARCHAR(200),
    retries_sessao   SMALLINT DEFAULT 0,
    embedding        vector(1024),
    cluster_id       INTEGER,
    criado_em        TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_adhoc_session ON agent_adhoc_script (session_id);
CREATE INDEX IF NOT EXISTS ix_adhoc_user ON agent_adhoc_script (user_id);
CREATE INDEX IF NOT EXISTS ix_adhoc_cluster ON agent_adhoc_script (cluster_id);
CREATE INDEX IF NOT EXISTS ix_adhoc_criado ON agent_adhoc_script (criado_em);
CREATE INDEX IF NOT EXISTS ix_adhoc_embedding ON agent_adhoc_script
    USING hnsw (embedding vector_cosine_ops);
```

- [ ] **Step 1.4: Migracao Python** — `scripts/migrations/2026_06_12_agent_adhoc_script.py` (padrao identico a `2026_06_07_agent_skill_effectiveness.py`):

```python
"""Cria a tabela agent_adhoc_script (Fase 2 aprendizado ad-hoc -> skill)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app import create_app, db
from sqlalchemy import text, inspect

SQL = open(os.path.join(os.path.dirname(__file__),
           "2026_06_12_agent_adhoc_script.sql")).read()


def main():
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        before = 'agent_adhoc_script' in insp.get_table_names()
        print(f"[before] tabela existe? {before}")
        for stmt in [s.strip() for s in SQL.split(';') if s.strip()]:
            db.session.execute(text(stmt))
        db.session.commit()
        insp = inspect(db.engine)
        after = 'agent_adhoc_script' in insp.get_table_names()
        print(f"[after] tabela existe? {after}")
        assert after, "tabela nao foi criada"


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.5: Model** — em `app/agente/models.py`, apos a classe `AgentSkillEffectiveness`:

```python
class AgentAdhocScript(db.Model):
    """Script ad-hoc (Bash substantivo) capturado do transcript pos-sessao (Fase 2).

    Spec: docs/superpowers/specs/2026-06-12-aprendizado-adhoc-fase2-design.md
    cluster_id incremental: vizinho cosine >= AGENT_ADHOC_SIM herda; senao = proprio id.
    """
    __tablename__ = 'agent_adhoc_script'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    problema = db.Column(db.String(120), nullable=True)
    command_masked = db.Column(db.Text, nullable=False)
    contexto_user_msg = db.Column(db.Text, nullable=True)
    skill_relacionada = db.Column(db.String(80), nullable=True)
    tipo_gap = db.Column(db.String(20), nullable=False, default='desconhecido')
    motivo_fallback = db.Column(db.String(200), nullable=True)
    retries_sessao = db.Column(db.SmallInteger, default=0)
    embedding = db.Column(EMBEDDING_VECTOR_TYPE, nullable=True)
    cluster_id = db.Column(db.Integer, nullable=True, index=True)
    criado_em = db.Column(db.DateTime, default=lambda: agora_utc_naive(), index=True)

    def __repr__(self):
        return f'<AgentAdhocScript {self.id} gap={self.tipo_gap} cluster={self.cluster_id}>'
```

Import no topo de `models.py` (se ainda nao existir): `from app.embeddings.models import EMBEDDING_VECTOR_TYPE` — CONFERIR import circular; se houver, replicar o guard de `app/embeddings/models.py:18-22` localmente:

```python
try:
    from pgvector.sqlalchemy import Vector
    EMBEDDING_VECTOR_TYPE = Vector(1024)
except ImportError:
    EMBEDDING_VECTOR_TYPE = db.Text
```

- [ ] **Step 1.6: Rodar migracao local + teste**

Run: `source .venv/bin/activate && python scripts/migrations/2026_06_12_agent_adhoc_script.py && pytest tests/agente/services/test_adhoc_capture.py::TestModel -x -q`
Expected: `[after] tabela existe? True` e `1 passed`

- [ ] **Step 1.7: Commit** — `git add -A && git commit -m "feat(agente): F2 ad-hoc - model AgentAdhocScript + migracao par"`

---

### Task 2: Parser do transcript (funcoes puras)

**Files:**
- Create: `app/agente/services/adhoc_capture_service.py`
- Test: `tests/agente/services/test_adhoc_capture.py` (append)

O transcript JSONL do SDK tem entries `{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_X", "name": "Bash", "input": {"command": "..."}}]}}` e resultados `{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_X", "is_error": true}]}}`. Mensagens do usuario: `{"type": "user", "message": {"content": "texto"}}` (ou lista com blocks `{"type": "text", "text": ...}`). **Validar contra transcript real na Task 9 antes do merge.**

- [ ] **Step 2.1: Testes que falham** (append em `test_adhoc_capture.py`):

```python
def _tu(name, tid, **inp):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def _tr(tid, is_error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "is_error": is_error}]}}


def _user(texto):
    return {"type": "user", "message": {"content": texto}}


class TestParser:
    def test_extrai_bash_com_skill_e_retry(self):
        from app.agente.services.adhoc_capture_service import extract_adhoc_candidates
        entries = [
            _user("exporta as 3 carteiras em abas"),
            _tu("Skill", "t1", skill="exportando-arquivos"),
            _tr("t1"),
            _tu("Bash", "t2", command="python -c 'tenta1'" + "x" * 300),
            _tr("t2", is_error=True),
            _tu("Bash", "t3", command="python -c 'tenta2'" + "x" * 300),
            _tr("t3"),
        ]
        cands = extract_adhoc_candidates(entries)
        assert len(cands) == 2
        assert cands[0]["skill_ativa"] == "exportando-arquivos"
        assert cands[0]["user_msg"] == "exporta as 3 carteiras em abas"
        assert cands[0]["teve_erro"] is True
        assert cands[1]["teve_erro"] is False

    def test_sem_skill_anterior(self):
        from app.agente.services.adhoc_capture_service import extract_adhoc_candidates
        entries = [_user("soma os fretes"),
                   _tu("Bash", "t1", command="python -c 'x'" + "y" * 300), _tr("t1")]
        cands = extract_adhoc_candidates(entries)
        assert cands[0]["skill_ativa"] is None

    def test_user_msg_em_blocks(self):
        from app.agente.services.adhoc_capture_service import extract_adhoc_candidates
        entries = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "oi"}]}},
            _tu("Bash", "t1", command="psql -c 'SELECT 1'" + "z" * 300), _tr("t1"),
        ]
        assert extract_adhoc_candidates(entries)[0]["user_msg"] == "oi"
```

- [ ] **Step 2.2: Rodar e ver falhar**

Run: `pytest tests/agente/services/test_adhoc_capture.py::TestParser -x -q`
Expected: FAIL `ModuleNotFoundError` ou `ImportError`

- [ ] **Step 2.3: Implementar** — inicio de `adhoc_capture_service.py`:

```python
"""Fase 2 aprendizado ad-hoc -> skill: captura, cluster e sugestao.

Spec: docs/superpowers/specs/2026-06-12-aprendizado-adhoc-fase2-design.md
Padrao espelhado da Fase 1 (skill_effectiveness_service.py).
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _entry_blocks(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    content = (entry.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def _entry_user_text(entry: Dict[str, Any]) -> Optional[str]:
    if entry.get("type") != "user":
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        joined = " ".join(t for t in texts if t).strip()
        return joined or None
    return None


def extract_adhoc_candidates(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Percorre o transcript cru e retorna candidatos Bash substantivos.

    Cada candidato: {command, skill_ativa, user_msg, teve_erro}.
    skill_ativa = ultimo tool_use Skill ANTES do Bash (superficie-agnostico —
    cobre Teams, diferente do tools_used do DB).
    """
    out: List[Dict[str, Any]] = []
    last_skill: Optional[str] = None
    last_user_msg: Optional[str] = None
    error_ids: set = set()

    # 1o passe: tool_results com erro (chegam DEPOIS do tool_use)
    for e in entries:
        for b in _entry_blocks(e):
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                error_ids.add(b.get("tool_use_id"))

    for e in entries:
        utext = _entry_user_text(e)
        if utext:
            last_user_msg = utext
        for b in _entry_blocks(e):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name = b.get("name", "")
            tinput = b.get("input") or {}
            if name == "Skill" and isinstance(tinput, dict):
                last_skill = (tinput.get("skill") or "").strip() or last_skill
            elif name == "Bash" and isinstance(tinput, dict):
                cmd = tinput.get("command") or ""
                if is_substantive(cmd):
                    out.append({
                        "command": cmd,
                        "skill_ativa": last_skill,
                        "user_msg": last_user_msg,
                        "teve_erro": b.get("id") in error_ids,
                    })
    return out
```

Nota: `is_substantive` vem da Task 3 — implementar as duas tasks em sequencia no mesmo arquivo (o teste da Task 2 usa comandos longos > limiar para ja passar no filtro).

- [ ] **Step 2.4:** Implementar Task 3 (abaixo) e SO ENTAO rodar: `pytest tests/agente/services/test_adhoc_capture.py::TestParser -x -q` → PASS. Commit unico na Task 3.

---

### Task 3: Filtro "Bash substantivo"

**Files:**
- Modify: `app/agente/services/adhoc_capture_service.py` (append)
- Test: `tests/agente/services/test_adhoc_capture.py` (append)

- [ ] **Step 3.1: Testes que falham**

```python
class TestFiltro:
    @pytest.mark.parametrize("cmd,esperado", [
        ("python -c 'import pandas; ...'", True),
        ("psql $DATABASE_URL -c \"SELECT count(*) FROM fretes\"", True),
        ("python << 'EOF'\nimport app\nEOF", True),
        ("x" * 250, True),                                     # longo = substantivo
        ("ls -la", False),
        ("git status", False),
        ("cat arquivo.txt", False),
        ("python .claude/skills/consultando-sql/scripts/consultar.py --q 'x'", False),  # script de skill
        ("source .venv/bin/activate && python app/odoo/scripts/foo.py", False),         # script persistido
    ])
    def test_substantivo(self, cmd, esperado):
        from app.agente.services.adhoc_capture_service import is_substantive
        assert is_substantive(cmd) is esperado
```

- [ ] **Step 3.2: Rodar e ver falhar** — `pytest tests/agente/services/test_adhoc_capture.py::TestFiltro -x -q` → FAIL (`is_substantive` indefinido)

- [ ] **Step 3.3: Implementar** (append no service):

```python
# Limiar de comprimento: comandos acima disso sao "substantivos" mesmo sem
# python/SQL explicito (heredocs, pipelines longos). Spec: decisao em aberto
# calibrada na Task 9 com transcripts reais.
SUBSTANTIVE_MIN_CHARS = 200

_TRIVIAL_PREFIXES = (
    "ls", "cat ", "head ", "tail ", "grep ", "find ", "echo ", "pwd", "wc ",
    "git status", "git log", "git diff", "git show", "which ", "env", "date",
)
_SCRIPT_FILE_RE = re.compile(r"python3?\s+\S*(\.claude/skills/|scripts/|app/\S+/scripts/)\S*\.py")
_INLINE_CODE_RE = re.compile(
    r"python3?\s+-c\s|<<\s*['\"]?EOF|psql\b|"
    r"\b(SELECT|INSERT|UPDATE|DELETE)\b.*\b(FROM|INTO|SET)\b", re.IGNORECASE)


def is_substantive(command: str) -> bool:
    """Filtro deterministico (zero token) do que e 'script ad-hoc'.

    Inclui: python -c / heredoc / SQL inline, ou comando longo.
    Exclui: triviais e execucao de scripts PERSISTIDOS (skill ou repo) —
    esses ja tem dono; o alvo da Fase 2 e codigo improvisado inline.
    """
    cmd = (command or "").strip()
    if not cmd:
        return False
    # remove prefixo de env injetado pelo hook (bash_prefix_propagacao)
    cmd_clean = re.sub(r"^(export\s+\w+=\S+;\s*)+", "", cmd)
    low = cmd_clean.lower()
    if _SCRIPT_FILE_RE.search(cmd_clean):
        return False
    if any(low.startswith(p) for p in _TRIVIAL_PREFIXES):
        return False
    if _INLINE_CODE_RE.search(cmd_clean):
        return True
    return len(cmd_clean) >= SUBSTANTIVE_MIN_CHARS
```

- [ ] **Step 3.4: Rodar Tasks 2+3** — `pytest tests/agente/services/test_adhoc_capture.py::TestParser tests/agente/services/test_adhoc_capture.py::TestFiltro -q` → PASS (todos)

- [ ] **Step 3.5: Commit** — `git add -A && git commit -m "feat(agente): F2 ad-hoc - parser de transcript + filtro substantivo"`

---

### Task 4: Extracao Haiku (`problema` + `motivo_fallback`) com fallback

**Files:**
- Modify: `app/agente/services/adhoc_capture_service.py` (append)
- Test: `tests/agente/services/test_adhoc_capture.py` (append)

- [ ] **Step 4.1: Testes que falham**

```python
class TestExtracao:
    def test_haiku_ok(self, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic",
            lambda model, system, user, max_tokens=300:
                '{"problema": "exportar excel multi-aba", "motivo_fallback": "exportar.py so gera 1 aba"}')
        prob, motivo = svc.extract_problema(
            command="python -c '...'", user_msg="exporta em 3 abas",
            skill_ativa="exportando-arquivos")
        assert prob == "exportar excel multi-aba"
        assert motivo == "exportar.py so gera 1 aba"

    def test_fallback_truncate(self, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        def _boom(*a, **k):
            raise RuntimeError("api down")
        monkeypatch.setattr(svc, "_call_anthropic", _boom)
        prob, motivo = svc.extract_problema(
            command="python -c 'x'", user_msg="m" * 300, skill_ativa=None)
        assert prob == "m" * 100
        assert motivo is None

    def test_trunca_limites(self, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic",
            lambda *a, **k: '{"problema": "' + "p" * 200 + '", "motivo_fallback": "' + "q" * 300 + '"}')
        prob, motivo = svc.extract_problema("cmd", "msg", "skill-x")
        assert len(prob) <= 100 and len(motivo) <= 150
```

- [ ] **Step 4.2: Rodar e ver falhar** — `pytest tests/agente/services/test_adhoc_capture.py::TestExtracao -x -q` → FAIL

- [ ] **Step 4.3: Implementar** (append; reusa `_call_anthropic` e `_parse_json` da Fase 1 por import — re-export local para monkeypatch):

```python
from app.agente.services.skill_effectiveness_service import (  # noqa: E402
    _call_anthropic, _parse_json,
)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"  # mesmo da Fase 1 stage1

_EXTRACT_SYSTEM = (
    "Voce extrai metadados de um script ad-hoc executado por um agente. "
    "Responda APENAS JSON: {\"problema\": \"<=100 chars, o problema de negocio "
    "que o script resolve>\", \"motivo_fallback\": \"<=150 chars, por que o "
    "agente usou script em vez da skill ativa — ou null se nao houver skill\"}."
)


def extract_problema(command: str, user_msg: Optional[str],
                     skill_ativa: Optional[str]) -> tuple:
    """(problema <=100c, motivo_fallback <=150c|None). Fallback = truncate da msg."""
    try:
        user = (f"Skill ativa: {skill_ativa or 'nenhuma'}\n"
                f"Pedido do usuario: {(user_msg or '')[:500]}\n"
                f"Comando: {command[:1500]}")
        raw = _call_anthropic(_HAIKU_MODEL, _EXTRACT_SYSTEM, user, max_tokens=300)
        data = _parse_json(raw)
        prob = (data.get("problema") or "")[:100] or None
        motivo = data.get("motivo_fallback")
        motivo = str(motivo)[:150] if motivo and skill_ativa else None
        if prob:
            return prob, motivo
    except Exception as e:
        logger.warning(f"[ADHOC] extracao Haiku falhou (fallback): {e}")
    return ((user_msg or command or "")[:100] or None), None
```

CONFERIR na implementacao: assinatura real de `_parse_json` (`skill_effectiveness_service.py:199`) — se retornar dict vazio em erro, o `if prob` ja cobre.

- [ ] **Step 4.4: Rodar** — `pytest tests/agente/services/test_adhoc_capture.py::TestExtracao -q` → PASS

- [ ] **Step 4.5: Commit** — `git commit -am "feat(agente): F2 ad-hoc - extracao problema/motivo via Haiku com fallback"`

---

### Task 5: Embedding + clustering incremental

**Files:**
- Modify: `app/agente/services/adhoc_capture_service.py` (append)
- Test: `tests/agente/services/test_adhoc_capture.py` (append)

- [ ] **Step 5.1: Testes que falham** (pgvector real do DB local; vetores sinteticos)

```python
def _vec(direcao: int) -> list:
    """Vetor 1024-dim quase-unitario numa 'direcao' sintetica."""
    v = [0.001] * 1024
    v[direcao] = 1.0
    return v


class TestCluster:
    def test_primeiro_vira_proprio_cluster(self, db):
        pytest.importorskip("pgvector")
        from app.agente.services.adhoc_capture_service import assign_cluster
        from app.agente.models import AgentAdhocScript
        row = AgentAdhocScript(session_id="s-c1", user_id=1, command_masked="x",
                               embedding=_vec(0))
        db.session.add(row); db.session.flush()
        assign_cluster(row)
        assert row.cluster_id == row.id
        db.session.rollback()

    def test_vizinho_proximo_herda(self, db):
        pytest.importorskip("pgvector")
        from app.agente.services.adhoc_capture_service import assign_cluster
        from app.agente.models import AgentAdhocScript
        a = AgentAdhocScript(session_id="s-c2", user_id=1, command_masked="a",
                             embedding=_vec(5))
        db.session.add(a); db.session.flush()
        a.cluster_id = a.id; db.session.flush()
        b = AgentAdhocScript(session_id="s-c2", user_id=1, command_masked="b",
                             embedding=_vec(5))  # identico -> sim 1.0
        db.session.add(b); db.session.flush()
        assign_cluster(b)
        assert b.cluster_id == a.id
        db.session.rollback()

    def test_distante_abre_cluster(self, db):
        pytest.importorskip("pgvector")
        from app.agente.services.adhoc_capture_service import assign_cluster
        from app.agente.models import AgentAdhocScript
        a = AgentAdhocScript(session_id="s-c3", user_id=1, command_masked="a",
                             embedding=_vec(10))
        db.session.add(a); db.session.flush()
        a.cluster_id = a.id; db.session.flush()
        b = AgentAdhocScript(session_id="s-c3", user_id=1, command_masked="b",
                             embedding=_vec(900))  # ortogonal -> sim ~0
        db.session.add(b); db.session.flush()
        assign_cluster(b)
        assert b.cluster_id == b.id
        db.session.rollback()
```

- [ ] **Step 5.2: Rodar e ver falhar** — `pytest tests/agente/services/test_adhoc_capture.py::TestCluster -x -q` → FAIL

- [ ] **Step 5.3: Implementar** (append; padrao de query igual `sql_evaluator_falses_service.py:237-240`):

```python
def gerar_embedding(texto: str) -> Optional[list]:
    """Embedding Voyage do texto (problema + comando). None em falha (best-effort)."""
    try:
        from app.embeddings.client import embed_with_retry
        from app.embeddings.config import VOYAGE_DEFAULT_MODEL
        vecs = embed_with_retry([texto[:4000]], model=VOYAGE_DEFAULT_MODEL,
                                input_type="document")
        return vecs[0] if vecs else None
    except Exception as e:
        logger.warning(f"[ADHOC] embedding falhou (segue sem cluster): {e}")
        return None


def assign_cluster(row) -> None:
    """Clustering incremental: vizinho cosine >= AGENT_ADHOC_SIM herda cluster_id;
    senao abre cluster proprio (cluster_id = id). Requer row.id e row.embedding."""
    from app import db
    from sqlalchemy import text as _text
    from app.agente.config import feature_flags as ff

    if row.embedding is None:
        row.cluster_id = row.id
        return
    sim_min = getattr(ff, "AGENT_ADHOC_SIM", 0.85)
    emb_str = "[" + ",".join(str(float(x)) for x in row.embedding) + "]"
    res = db.session.execute(_text("""
        SELECT cluster_id, 1 - (embedding <=> CAST(:q AS vector)) AS similarity
        FROM agent_adhoc_script
        WHERE id != :rid AND embedding IS NOT NULL AND cluster_id IS NOT NULL
        ORDER BY embedding <=> CAST(:q AS vector)
        LIMIT 1
    """), {"q": emb_str, "rid": row.id}).first()
    if res is not None and float(res.similarity) >= sim_min:
        row.cluster_id = int(res.cluster_id)
    else:
        row.cluster_id = row.id
```

- [ ] **Step 5.4: Rodar** — `pytest tests/agente/services/test_adhoc_capture.py::TestCluster -q` → PASS
- [ ] **Step 5.5: Commit** — `git commit -am "feat(agente): F2 ad-hoc - embedding voyage + clustering incremental pgvector"`

---

### Task 6: Flags

**Files:**
- Modify: `app/agente/config/feature_flags.py` (apos bloco `AGENT_SKILL_EVAL_*`, ~linha 1202)

- [ ] **Step 6.1: Adicionar** (mesmo padrao das vizinhas):

```python
# --- Fase 2 aprendizado ad-hoc -> skill (spec 2026-06-12) ---
AGENT_ADHOC_CAPTURE = os.getenv("AGENT_ADHOC_CAPTURE", "true").lower() == "true"
AGENT_ADHOC_SIM = float(os.getenv("AGENT_ADHOC_SIM", "0.85"))
AGENT_ADHOC_THRESHOLD_USER = int(os.getenv("AGENT_ADHOC_THRESHOLD_USER", "3"))
AGENT_ADHOC_THRESHOLD_GLOBAL = int(os.getenv("AGENT_ADHOC_THRESHOLD_GLOBAL", "5"))
AGENT_ADHOC_MAX_HAIKU_DAY = int(os.getenv("AGENT_ADHOC_MAX_HAIKU_DAY", "100"))
AGENT_ADHOC_MAX_SONNET_DAY = int(os.getenv("AGENT_ADHOC_MAX_SONNET_DAY", "2"))
```

- [ ] **Step 6.2: Smoke** — `python -c "from app.agente.config import feature_flags as f; print(f.AGENT_ADHOC_CAPTURE, f.AGENT_ADHOC_SIM)"` → `True 0.85`
- [ ] **Step 6.3: Commit** — `git commit -am "feat(agente): F2 ad-hoc - 6 feature flags"`

---

### Task 7: Disparo (thresholds + bypass + caps + dedup → dialogue)

**Files:**
- Modify: `app/agente/services/adhoc_capture_service.py` (append)
- Test: `tests/agente/services/test_adhoc_capture.py` (append)

- [ ] **Step 7.1: Testes que falham**

```python
class TestDisparo:
    def _mk(self, db, cluster_id, n, user_id=1, **kw):
        from app.agente.models import AgentAdhocScript
        rows = []
        for i in range(n):
            r = AgentAdhocScript(session_id=f"s-d{cluster_id}-{i}", user_id=user_id,
                                 command_masked=f"cmd{i}", problema=f"prob {cluster_id}",
                                 cluster_id=cluster_id, **kw)
            db.session.add(r); rows.append(r)
        db.session.flush()
        return rows

    def test_threshold_user_dispara_dialogue(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        from app.agente.models import AgentImprovementDialogue
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k:
            '{"vale_skill": true, "tipo_gap": "sem_skill", "titulo": "skill p/ X", "descricao": "cluster de 3"}')
        rows = self._mk(db, cluster_id=777001, n=3)
        ref = svc.maybe_fire_suggestion(rows[-1])
        assert ref and ref.startswith("dialogue:")
        d = AgentImprovementDialogue.query.filter_by(
            suggestion_key="adhoc-cluster-777001").first()
        assert d is not None and d.category == "skill_suggestion"
        db.session.rollback()

    def test_abaixo_threshold_nao_dispara(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        called = []
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k: called.append(1) or "{}")
        rows = self._mk(db, cluster_id=777002, n=2)
        assert svc.maybe_fire_suggestion(rows[-1]) is None
        assert not called  # Sonnet nem foi chamado
        db.session.rollback()

    def test_bypass_gap_nomeado(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k:
            '{"vale_skill": true, "tipo_gap": "skill_insuficiente", "titulo": "estender exportar", "descricao": "1 aba"}')
        rows = self._mk(db, cluster_id=777003, n=1,
                        skill_relacionada="exportando-arquivos",
                        tipo_gap="skill_insuficiente", motivo_fallback="so 1 aba")
        ref = svc.maybe_fire_suggestion(rows[-1])
        assert ref is not None  # 1 ocorrencia ja basta
        db.session.rollback()

    def test_dedup_suggestion_key(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k:
            '{"vale_skill": true, "tipo_gap": "sem_skill", "titulo": "t", "descricao": "d"}')
        rows = self._mk(db, cluster_id=777004, n=3)
        assert svc.maybe_fire_suggestion(rows[-1]) is not None
        assert svc.maybe_fire_suggestion(rows[-1]) is None  # 2a vez trava
        db.session.rollback()
```

- [ ] **Step 7.2: Rodar e ver falhar** — `pytest tests/agente/services/test_adhoc_capture.py::TestDisparo -x -q` → FAIL

- [ ] **Step 7.3: Implementar** (append):

```python
_SONNET_MODEL = "claude-sonnet-4-6"  # mesmo da Fase 1 stage2

_JUDGE_SYSTEM = (
    "Voce julga se um cluster de scripts ad-hoc recorrentes de um agente "
    "justifica criar/estender uma skill. Criterios: C2 generalizavel (parametros "
    "variam entre membros? comando identico sempre = fast-path/cron, nao skill); "
    "C3 cobertura (skill_relacionada presente e insuficiente -> extensao; "
    "presente mas nao invocada -> skill_nao_usada; ausente -> sem_skill; "
    "nao generaliza -> one_off); C6 friccao (retries indicam conhecimento "
    "nao-derivavel = skill agrega muito). Responda APENAS JSON: "
    '{"vale_skill": bool, "tipo_gap": "sem_skill|skill_nao_usada|'
    'skill_insuficiente|one_off", "titulo": "<=180 chars", "descricao": "<=800 chars"}'
)


def _suggestion_key(row) -> str:
    if row.tipo_gap == "skill_insuficiente" and row.skill_relacionada:
        slug = re.sub(r"[^a-z0-9]+", "-", (row.motivo_fallback or "")[:40].lower()).strip("-")
        return f"skill-gap-{row.skill_relacionada}-{slug or row.cluster_id}"[:100]
    return f"adhoc-cluster-{row.cluster_id}"[:100]


def _sonnet_cap_ok() -> bool:
    from app.agente.models import AgentImprovementDialogue
    from app.agente.config import feature_flags as ff
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    cap = getattr(ff, "AGENT_ADHOC_MAX_SONNET_DAY", 2)
    desde = agora_utc_naive() - timedelta(days=1)
    n = AgentImprovementDialogue.query.filter(
        AgentImprovementDialogue.suggestion_key.like("adhoc-%") |
        AgentImprovementDialogue.suggestion_key.like("skill-gap-%"),
        AgentImprovementDialogue.created_at >= desde).count()
    return n < cap


def maybe_fire_suggestion(row) -> Optional[str]:
    """Avalia disparo p/ o cluster do row. Retorna 'dialogue:<id>' ou None."""
    from app import db
    from app.agente.models import AgentAdhocScript, AgentImprovementDialogue
    from app.agente.config import feature_flags as ff
    from app.utils.json_helpers import sanitize_for_json

    if row.cluster_id is None:
        return None
    membros = AgentAdhocScript.query.filter_by(cluster_id=row.cluster_id).all()
    por_user = sum(1 for m in membros if m.user_id == row.user_id)
    bypass = (row.tipo_gap == "skill_insuficiente"
              and row.skill_relacionada and row.motivo_fallback)
    if not bypass and por_user < getattr(ff, "AGENT_ADHOC_THRESHOLD_USER", 3) \
            and len(membros) < getattr(ff, "AGENT_ADHOC_THRESHOLD_GLOBAL", 5):
        return None
    key = _suggestion_key(row)
    if AgentImprovementDialogue.query.filter_by(suggestion_key=key).first():
        return None  # checkpoint: ja proposto (inclusive rejeitado — trava)
    if not _sonnet_cap_ok():
        logger.info("[ADHOC] cap diario Sonnet atingido — adiado")
        return None

    resumo = "\n".join(
        f"- problema: {m.problema} | skill: {m.skill_relacionada or '-'} | "
        f"motivo: {m.motivo_fallback or '-'} | retries: {m.retries_sessao} | "
        f"cmd: {(m.command_masked or '')[:300]}"
        for m in membros[:10])
    try:
        raw = _call_anthropic(_SONNET_MODEL, _JUDGE_SYSTEM,
                              f"Cluster {row.cluster_id} ({len(membros)} membros):\n{resumo}",
                              max_tokens=600)
        veredito = _parse_json(raw)
    except Exception as e:
        logger.warning(f"[ADHOC] julgamento Sonnet falhou: {e}")
        return None
    if not veredito.get("vale_skill"):
        # trava barata: marca cluster como one_off (sem poluir a Inbox).
        # Se o cluster dobrar de tamanho depois, reavaliar e' melhoria futura (YAGNI).
        for m in membros:
            m.tipo_gap = "one_off"
        return None

    d = AgentImprovementDialogue(
        suggestion_key=key, version=1, author="agent_sdk", status="proposed",
        category="skill_suggestion", severity="info",
        title=(veredito.get("titulo") or f"Skill para cluster {row.cluster_id}")[:200],
        description=(veredito.get("descricao") or "")[:4000],
        evidence_json=sanitize_for_json({
            "tipo_gap": veredito.get("tipo_gap", row.tipo_gap),
            "skill_relacionada": row.skill_relacionada,
            "cluster_id": row.cluster_id,
            "n_membros": len(membros),
            "membros": [{"problema": m.problema, "session_id": m.session_id,
                         "motivo": m.motivo_fallback} for m in membros[:10]],
        }),
    )
    db.session.add(d)
    db.session.flush()
    return f"dialogue:{d.id}"
```

CONFERIR na implementacao: campos exatos de `AgentImprovementDialogue` (`models.py:1196-1240` — nome do campo de data de criacao; ajustar `_sonnet_cap_ok` se nao for `created_at`).

- [ ] **Step 7.4: Rodar** — `pytest tests/agente/services/test_adhoc_capture.py::TestDisparo -q` → PASS
- [ ] **Step 7.5: Commit** — `git commit -am "feat(agente): F2 ad-hoc - disparo com thresholds, bypass gap nomeado, cap e dedup"`

---

### Task 8: Orquestracao + job RQ + gatilho pos-sessao

**Files:**
- Modify: `app/agente/services/adhoc_capture_service.py` (append `capture_session`)
- Modify: `app/agente/workers/background_jobs.py` (apos `try_enqueue_skill_effectiveness`, ~linha 280)
- Modify: `app/agente/routes/_helpers.py` (apos `_maybe_trigger_skill_eval`, ~linha 286; chamada apos a linha 549)
- Test: `tests/agente/services/test_adhoc_capture.py` (append)

- [ ] **Step 8.1: Teste que falha** (integracao com mocks):

```python
class TestCapture:
    def test_capture_session_persiste(self, db, monkeypatch):
        from app.agente.services import adhoc_capture_service as svc
        from app.agente.models import AgentSession, AgentAdhocScript
        import uuid
        sid = f"test-adhoc-{uuid.uuid4().hex[:12]}"
        sess = AgentSession(session_id=sid, user_id=1, data={"sdk_session_id": f"sdk-{sid}"})
        db.session.add(sess); db.session.flush()

        entries = [
            _user("exporta 3 abas"),
            _tu("Skill", "t1", skill="exportando-arquivos"), _tr("t1"),
            _tu("Bash", "t2", command="python -c 'pandas'" + "x" * 300),
            _tr("t2", is_error=True),
        ]
        monkeypatch.setattr(svc, "_load_transcript_entries", lambda sdk_sid: entries)
        monkeypatch.setattr(svc, "extract_problema",
                            lambda c, u, s: ("exportar multi-aba", "so 1 aba"))
        monkeypatch.setattr(svc, "gerar_embedding", lambda t: None)  # sem voyage no teste
        monkeypatch.setattr(svc, "maybe_fire_suggestion", lambda r: None)

        res = svc.capture_session(session_id=sid, user_id=1)
        assert res["capturados"] == 1
        row = AgentAdhocScript.query.filter_by(session_id=sid).first()
        assert row.skill_relacionada == "exportando-arquivos"
        assert row.tipo_gap == "skill_insuficiente"
        assert row.retries_sessao == 1
        assert row.cluster_id == row.id  # embedding None -> cluster proprio
        db.session.rollback()

    def test_flag_off_no_op(self, monkeypatch):
        from app.agente.config import feature_flags as ff
        from app.agente.services import adhoc_capture_service as svc
        monkeypatch.setattr(ff, "AGENT_ADHOC_CAPTURE", False)
        assert svc.capture_session("qualquer", 1) == {"capturados": 0, "skip": "flag_off"}
```

Nota: `capture_session` persiste com `db.session.commit()` — seguir o padrao de cleanup da suite (id unico + rollback; ver gotcha `gotcha_commit_service_vaza_savepoint`): usar session_id unico (uuid) e deletar os rows criados no fim do teste se o rollback nao bastar.

- [ ] **Step 8.2: Rodar e ver falhar** — `pytest tests/agente/services/test_adhoc_capture.py::TestCapture -x -q` → FAIL

- [ ] **Step 8.3: Implementar `capture_session`** (append no service):

```python
def _load_transcript_entries(sdk_session_id: str) -> List[Dict[str, Any]]:
    """Le o transcript cru via SQL sincrono (decisao impl. 1 — sem asyncio em RQ)."""
    from app import db
    from sqlalchemy import text as _text
    import json as _json
    rows = db.session.execute(_text("""
        SELECT entry FROM claude_session_store
        WHERE session_id = :sid AND subpath = ''
        ORDER BY seq
    """), {"sid": sdk_session_id}).fetchall()
    out = []
    for r in rows:
        v = r[0]
        out.append(_json.loads(v) if isinstance(v, (str, bytes)) else v)
    return out


def _haiku_cap_ok() -> bool:
    from app.agente.models import AgentAdhocScript
    from app.agente.config import feature_flags as ff
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    desde = agora_utc_naive() - timedelta(days=1)
    n = AgentAdhocScript.query.filter(AgentAdhocScript.criado_em >= desde).count()
    return n < getattr(ff, "AGENT_ADHOC_MAX_HAIKU_DAY", 100)


def capture_session(session_id: str, user_id: int, app=None) -> Dict[str, Any]:
    """Entry-point do job: captura Bash substantivo da sessao (best-effort total)."""
    if app is not None:
        with app.app_context():
            return _capture_inner(session_id, user_id)
    return _capture_inner(session_id, user_id)


def _capture_inner(session_id: str, user_id: int) -> Dict[str, Any]:
    from app import db
    from app.agente.models import AgentSession, AgentAdhocScript
    from app.agente.config import feature_flags as ff
    from app.agente.utils.pii_masker import mask_pii

    if not getattr(ff, "AGENT_ADHOC_CAPTURE", True):
        return {"capturados": 0, "skip": "flag_off"}
    result = {"capturados": 0}
    try:
        sess = AgentSession.query.filter_by(session_id=session_id).first()
        sdk_sid = sess.get_sdk_session_id() if sess else None
        if not sdk_sid:
            return {**result, "skip": "sem_sdk_session_id"}
        entries = _load_transcript_entries(sdk_sid)
        if not entries:
            return {**result, "skip": "transcript_vazio"}
        vistos: set = set()
        for cand in extract_adhoc_candidates(entries):
            cmd = cand["command"]
            if cmd in vistos:  # dedup exato intra-sessao
                continue
            vistos.add(cmd)
            problema, motivo = (None, None)
            if _haiku_cap_ok():
                problema, motivo = extract_problema(cmd, cand["user_msg"], cand["skill_ativa"])
            problema = problema or (cand["user_msg"] or cmd)[:100]
            tipo_gap = ("skill_insuficiente" if (cand["skill_ativa"] and motivo)
                        else "desconhecido" if cand["skill_ativa"] else "sem_skill")
            row = AgentAdhocScript(
                session_id=session_id, user_id=user_id,
                problema=problema,
                command_masked=mask_pii(cmd)[:8000],
                contexto_user_msg=mask_pii(cand["user_msg"] or "")[:1000] or None,
                skill_relacionada=cand["skill_ativa"],
                tipo_gap=tipo_gap, motivo_fallback=motivo,
                retries_sessao=1 if cand["teve_erro"] else 0,
                embedding=gerar_embedding(f"{problema}\n{cmd[:2000]}"),
            )
            db.session.add(row)
            db.session.flush()
            assign_cluster(row)
            try:
                maybe_fire_suggestion(row)
            except Exception as e:
                logger.warning(f"[ADHOC] disparo falhou (segue): {e}")
            result["capturados"] += 1
        db.session.commit()
    except Exception as e:
        logger.error(f"[ADHOC] capture_session falhou: {e}", exc_info=True)
        try:
            from app import db as _db
            _db.session.rollback()
        except Exception:
            pass
    return result
```

- [ ] **Step 8.4: Job + enqueue** em `background_jobs.py` (espelho exato de `skill_effectiveness_job`/`try_enqueue_skill_effectiveness`, linhas 249-279):

```python
def adhoc_capture_job(session_id: str, user_id: int) -> bool:
    """Job RQ: captura scripts ad-hoc do transcript da sessao (Fase 2)."""
    try:
        from app import create_app
        from app.agente.services.adhoc_capture_service import capture_session
        app = create_app()
        capture_session(session_id=session_id, user_id=user_id, app=app)
        return True
    except Exception as e:
        logger.error(f"[RQ_JOB adhoc] session={session_id[:8]}... erro: {e}", exc_info=True)
        return False


def try_enqueue_adhoc_capture(session_id: str, user_id: int) -> bool:
    """Enfileira captura ad-hoc. True se enfileirou; False = caller faz fallback."""
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            adhoc_capture_job,
            session_id, user_id,
            job_timeout=180,
            description=f"adhoc_capture {session_id[:8]}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue adhoc falhou (fallback inline): {e}")
        return False
```

- [ ] **Step 8.5: Gatilho** em `_helpers.py` (apos `_maybe_trigger_skill_eval`, espelho exato das linhas 271-285):

```python
def _maybe_trigger_adhoc_capture(session_id: str, user_id: int) -> None:
    """Best-effort: enfileira captura de scripts ad-hoc (Fase 2).

    Nunca propaga excecao — se quebrar, nao afeta pos-processamento web nem Teams.
    """
    try:
        from app.agente.config.feature_flags import AGENT_ADHOC_CAPTURE
        if not AGENT_ADHOC_CAPTURE:
            return
        from app.agente.workers.background_jobs import try_enqueue_adhoc_capture
        if not try_enqueue_adhoc_capture(session_id, user_id):
            from app.agente.services.adhoc_capture_service import capture_session
            capture_session(session_id=session_id, user_id=user_id)  # app_context ja ativo
    except Exception as e:
        logger.warning(f"[POST_SESSION] adhoc capture (ignorado): {e}")
```

E a chamada, logo apos `_maybe_trigger_skill_eval(session_id, user_id)` (linha 549):

```python
    # =================================================================
    # Fase 2: Captura de scripts ad-hoc (best-effort)
    # =================================================================
    _maybe_trigger_adhoc_capture(session_id, user_id)
```

- [ ] **Step 8.6: Rodar tudo** — `pytest tests/agente/services/test_adhoc_capture.py -q` → PASS (todos) e `pytest tests/agente/ -q` → sem regressao
- [ ] **Step 8.7: Commit** — `git commit -am "feat(agente): F2 ad-hoc - capture_session + job RQ + gatilho pos-sessao"`

---

### Task 9: Validacao com transcript real + atualizacoes de spec/memoria

**Files:**
- Modify: `docs/superpowers/specs/2026-06-12-aprendizado-adhoc-fase2-design.md` (edge case Teams + fonte SQL)
- Modify: memoria dev `aprendizado_efetividade_skills.md` (debito Teams ja fechado)

- [ ] **Step 9.1: Validar formato do transcript real** — pegar 1 sessao recente local:

```bash
source .venv/bin/activate && python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    row = db.session.execute(text(
        \"SELECT session_id FROM claude_session_store WHERE subpath='' ORDER BY seq DESC LIMIT 1\")).first()
    from app.agente.services.adhoc_capture_service import _load_transcript_entries, extract_adhoc_candidates
    entries = _load_transcript_entries(row[0])
    cands = extract_adhoc_candidates(entries)
    print(f'entries={len(entries)} candidatos={len(cands)}')
    for c in cands[:3]:
        print('skill:', c['skill_ativa'], '| erro:', c['teve_erro'], '| cmd:', c['command'][:80])
"
```
Expected: roda sem excecao; estrutura dos candidatos coerente. **Se o formato real divergir das fixtures** (ex.: blocks aninhados diferente), ajustar `_entry_blocks`/`_entry_user_text` + fixtures e re-rodar a suite.

- [ ] **Step 9.2: Calibrar `SUBSTANTIVE_MIN_CHARS`** — inspecionar os candidatos do passo 9.1: se comandos triviais longos passarem (ex. pipelines de log), subir p/ 300; se heredocs reais ficarem de fora, manter 200 e ampliar `_INLINE_CODE_RE`. Registrar o valor final na spec (secao "Decisoes em aberto" → resolvida).

- [ ] **Step 9.3: Atualizar spec** — na secao "Edge cases", substituir o paragrafo "Teams degradado" por: debito `tool_name` FECHADO (`ede93a0e2`) E `skill_relacionada` extraida do transcript cru (superficie-agnostico) — caso resolvido por construcao. Na secao "O que ja existe", anotar fonte = SQL sincrono direto em `claude_session_store` (decisao impl. 1). Atualizar `atualizado:`.

- [ ] **Step 9.4: Atualizar memoria dev** — em `aprendizado_efetividade_skills.md`: (a) debito Teams FECHADO por `ede93a0e2` (remover da fila estrategica item 1 e do PENDENTE da Fase 1); (b) estado Fase 2 = implementada em worktree.

- [ ] **Step 9.5: Suite completa + lint docs** — `pytest tests/agente/ -q && python scripts/audits/doc_audit.py --enforce-touched` → verde.
- [ ] **Step 9.6: Commit** — `git commit -am "docs(agente): F2 ad-hoc - spec atualizada (Teams resolvido, fonte SQL sync) + calibracao filtro"`

---

### Task 10: Finalizacao

- [ ] **Step 10.1:** Usar a skill `superpowers:finishing-a-development-branch` — merge na main local apos review.
- [ ] **Step 10.2:** Checklist de deploy (NAO executar sem OK explicito do Rafael):
  1. Push `origin/main` (= deploy web + worker via Render auto-deploy).
  2. Rodar migracao em PROD: `python scripts/migrations/2026_06_12_agent_adhoc_script.py` com `DATABASE_URL_PROD` (requer autorizacao explicita — memoria `database_url_prod_escrita_direta`).
  3. Flag `AGENT_ADHOC_CAPTURE` ja default `true` no codigo — sem env extra.
  4. Smoke PROD: 1 sessao web com Bash ad-hoc → `SELECT * FROM agent_adhoc_script ORDER BY id DESC LIMIT 3`.

---

## Self-review (executado na escrita)

- **Spec coverage:** captura (T2/T3/T8), problema/session_id/timestamp (T1/T4), embedding+cluster (T5), thresholds+bypass+caps+dedup (T7), 4 destinos (T7: dialogue p/ sem_skill e skill_insuficiente; skill_nao_usada/one_off via veredito Sonnet no `evidence_json` — a ACAO desses ramos e do Claude Code pos-aprovacao, conforme separacao de competencias), flags (T6), best-effort (T8), pytest sem evals LLM (todas), migracao par (T1), calibracao limiar (T9). Camada A: fora do escopo (fase seguinte, conforme spec).
- **Type consistency:** `extract_adhoc_candidates` → dict keys usadas em `_capture_inner` conferem (command/skill_ativa/user_msg/teve_erro); `extract_problema` retorna tupla; `assign_cluster(row)` muta in-place; `maybe_fire_suggestion(row)` → `Optional[str]`.
- **Pontos marcados CONFERIR** (intencionais, baratos de verificar na execucao): import circular EMBEDDING_VECTOR_TYPE (T1.5), assinatura `_parse_json` (T4.3), campo de data do dialogue (T7.3), formato real do transcript (T9.1).
