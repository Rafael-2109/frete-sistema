"""F5 PAD-CTX — proveniencia de memorias (source_session_id, last_confirmed, confidence).

Plano: docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md FASE 5
(tarefas 5.1-5.3). Contrato no PAD-CTX (ARQUITETURA_CONTEXTO_AGENTE.md §Memorias):

- 5.1: colunas novas em agent_memories (source_session_id TEXT, last_confirmed
  TIMESTAMP, confidence TEXT).
- 5.2: save_memory popula source_session_id via get_current_session_id (ContextVar
  canonico em app/agente/config/permissions.py); update toca last_confirmed e NUNCA
  reescreve a origem; daemons pos-sessao propagam session_id por parametro opcional
  (sem ele, NULL).
- 5.3: injecao expoe proveniencia cross-user-safe — memoria PESSOAL ganha
  session="..." + date="..."; memoria EMPRESA (user_id=0) ganha APENAS created_by=
  + date= (UUID de sessao alheia NUNCA vaza no tag).
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app import create_app, db
from app.agente.models import AgentMemory


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


_PREFIX = "/memories/empresa/heuristicas/_pytest_prov"
_PESSOAL_PREFIX = "/memories/context/_pytest_prov"


def _cleanup():
    AgentMemory.query.filter(
        AgentMemory.path.like(f"{_PREFIX}%")
        | AgentMemory.path.like(f"{_PESSOAL_PREFIX}%")
    ).delete(synchronize_session=False)
    db.session.commit()


@pytest.fixture
def limpa(app, monkeypatch):
    # Neutraliza embedding+KG best-effort do _save_empresa_memory (sync, import
    # local) — sem isso as memorias _pytest_prov geram ENTIDADES no KG do banco
    # local e poluem test_query_ontology (residuo descoberto na suite 2026-06-10).
    monkeypatch.setattr('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', False)
    monkeypatch.setattr('app.embeddings.config.MEMORY_KNOWLEDGE_GRAPH', False)
    _cleanup()
    yield
    _cleanup()


# ---------------------------------------------------------------------------
# 5.1 — Model
# ---------------------------------------------------------------------------

class TestModelColunasProveniencia:
    def test_model_tem_source_session_id(self):
        assert hasattr(AgentMemory, "source_session_id")
        col = AgentMemory.__table__.columns["source_session_id"]
        assert col.nullable is True

    def test_model_tem_last_confirmed(self):
        assert hasattr(AgentMemory, "last_confirmed")
        col = AgentMemory.__table__.columns["last_confirmed"]
        assert col.nullable is True

    def test_model_tem_confidence(self):
        assert hasattr(AgentMemory, "confidence")
        col = AgentMemory.__table__.columns["confidence"]
        assert col.nullable is True


# ---------------------------------------------------------------------------
# 5.2 — Helpers de proveniencia no save_memory (memory_mcp_tool)
# ---------------------------------------------------------------------------

class TestHelpersProvenance:
    def test_apply_provenance_on_create_com_sessao_ativa(self):
        from app.agente.config.permissions import set_current_session_id
        from app.agente.tools.memory_mcp_tool import _apply_provenance_on_create

        mem = SimpleNamespace(source_session_id=None, last_confirmed=None)
        set_current_session_id("sess-prov-123")
        try:
            _apply_provenance_on_create(mem)
        finally:
            set_current_session_id(None)
        assert mem.source_session_id == "sess-prov-123"
        assert mem.last_confirmed is not None

    def test_apply_provenance_on_create_sem_sessao(self):
        from app.agente.config.permissions import set_current_session_id
        from app.agente.tools.memory_mcp_tool import _apply_provenance_on_create

        mem = SimpleNamespace(source_session_id=None, last_confirmed=None)
        set_current_session_id(None)
        _apply_provenance_on_create(mem)
        assert mem.source_session_id is None
        assert mem.last_confirmed is not None  # criado = confirmado agora

    def test_touch_last_confirmed_preserva_origem(self):
        from app.agente.config.permissions import set_current_session_id
        from app.agente.tools.memory_mcp_tool import _touch_last_confirmed

        antigo = datetime(2026, 1, 1, 12, 0, 0)
        mem = SimpleNamespace(
            source_session_id="sess-origem", last_confirmed=antigo
        )
        set_current_session_id("sess-OUTRA")
        try:
            _touch_last_confirmed(mem)
        finally:
            set_current_session_id(None)
        # update NUNCA reescreve a origem; só renova o frescor
        assert mem.source_session_id == "sess-origem"
        assert mem.last_confirmed > antigo


# ---------------------------------------------------------------------------
# 5.2 — Daemons pos-sessao
# ---------------------------------------------------------------------------

class TestDaemonsProvenance:
    def test_summarizer_popula_source_session(self, app, limpa, monkeypatch):
        from app.agente.services import session_summarizer as ss

        # path isolado de teste (nao sobrescrever a memoria real do user)
        monkeypatch.setattr(
            ss, "_SUMMARY_MEMORY_PATH", f"{_PESSOAL_PREFIX}/session_summary.xml",
            raising=False,
        )
        summary = {"resumo": "teste proveniencia", "topicos": []}
        ss._save_summary_to_memory(0, "sess-summarizer-9", summary)
        db.session.commit()

        mem = AgentMemory.get_by_path(0, f"{_PESSOAL_PREFIX}/session_summary.xml")
        assert mem is not None
        assert mem.source_session_id == "sess-summarizer-9"

    def test_save_empresa_memory_propaga_session_id(self, app, limpa):
        from app.agente.services.pattern_analyzer import _save_empresa_memory

        path = f"{_PREFIX}/com-sessao.xml"
        content = (
            "<heuristica><nivel>5</nivel><titulo>T prov</titulo>"
            "<when>quando X</when><prescricao>faca Y</prescricao></heuristica>"
        )
        assert _save_empresa_memory(path, content, created_by=1,
                                    session_id="sess-extracao-7")
        mem = AgentMemory.get_by_path(0, path)
        assert mem.source_session_id == "sess-extracao-7"

    def test_save_empresa_memory_update_renova_frescor_preserva_origem(self, app, limpa):
        from app.agente.services.pattern_analyzer import _save_empresa_memory

        path = f"{_PREFIX}/update-frescor.xml"
        content_v1 = (
            "<heuristica><nivel>5</nivel><titulo>T v1</titulo>"
            "<when>quando A</when><prescricao>faca B</prescricao></heuristica>"
        )
        assert _save_empresa_memory(path, content_v1, created_by=1,
                                    session_id="sess-origem-1")
        mem = AgentMemory.get_by_path(0, path)
        origem, confirmado_v1 = mem.source_session_id, mem.last_confirmed

        content_v2 = (
            "<heuristica><nivel>5</nivel><titulo>T v2</titulo>"
            "<when>quando A2</when><prescricao>faca B2</prescricao></heuristica>"
        )
        assert _save_empresa_memory(path, content_v2, created_by=1,
                                    session_id="sess-OUTRA-2")
        mem = AgentMemory.get_by_path(0, path)
        assert mem.source_session_id == origem == "sess-origem-1"
        assert mem.last_confirmed >= confirmado_v1

    def test_save_empresa_memory_sem_session_id_fica_null(self, app, limpa):
        from app.agente.services.pattern_analyzer import _save_empresa_memory

        path = f"{_PREFIX}/sem-sessao.xml"
        content = (
            "<heuristica><nivel>5</nivel><titulo>T prov null</titulo>"
            "<when>quando Z</when><prescricao>faca W</prescricao></heuristica>"
        )
        assert _save_empresa_memory(path, content, created_by=1)
        mem = AgentMemory.get_by_path(0, path)
        assert mem.source_session_id is None


# ---------------------------------------------------------------------------
# 5.3 — Exposicao na injecao (cross-user-safe)
# ---------------------------------------------------------------------------

def _mem_stub(**kw):
    base = dict(
        path="/memories/x.xml",
        meta=None,
        user_id=5,
        source_session_id=None,
        created_by=None,
        created_at=datetime(2026, 6, 1, 10, 0, 0),
        updated_at=datetime(2026, 6, 5, 10, 0, 0),
    )
    base.update(kw)
    return SimpleNamespace(**base)


class TestOpenTagProvenance:
    def test_pessoal_expoe_session_e_date(self):
        from app.agente.sdk.memory_injection import _memory_open_tag

        mem = _mem_stub(user_id=5, source_session_id="sess-abc-1")
        tag = _memory_open_tag(mem)
        assert 'session="sess-abc-1"' in tag
        assert 'date="05/06/2026"' in tag

    def test_pessoal_sem_source_session_nao_quebra(self):
        from app.agente.sdk.memory_injection import _memory_open_tag

        mem = _mem_stub(user_id=5, source_session_id=None)
        tag = _memory_open_tag(mem)
        assert "session=" not in tag
        assert 'date="05/06/2026"' in tag

    def test_empresa_nao_vaza_session_expoe_created_by(self):
        from app.agente.sdk.memory_injection import _memory_open_tag

        # memoria EMPRESA criada na sessao de OUTRO usuario: o UUID nao pode vazar
        mem = _mem_stub(
            user_id=0, source_session_id="sess-de-outro-user",
            created_by=18,
        )
        tag = _memory_open_tag(mem)
        assert "sess-de-outro-user" not in tag
        assert "session=" not in tag
        assert 'created_by="18"' in tag
        assert 'date="05/06/2026"' in tag

    def test_empresa_sem_created_by_so_date(self):
        from app.agente.sdk.memory_injection import _memory_open_tag

        mem = _mem_stub(user_id=0, source_session_id=None, created_by=None)
        tag = _memory_open_tag(mem)
        assert "created_by=" not in tag
        assert "session=" not in tag
        assert 'date="05/06/2026"' in tag

    def test_stub_legado_sem_atributos_novos(self):
        """Robustez: objeto sem as colunas novas (mock antigo) nao explode."""
        from app.agente.sdk.memory_injection import _memory_open_tag

        mem = SimpleNamespace(path="/memories/y.xml", meta=None)
        tag = _memory_open_tag(mem)
        assert tag.startswith("<memory ")
