"""Integracao DB do formato canonico de memorias (coluna meta JSONB).

Valida o pipeline end-to-end: gerador grava meta -> indice navegavel le meta ->
consumidor (operational_directives) prefere meta. Usa paths de teste isolados
(prefixo _pytest_meta, user_id=0 empresa) e limpa antes/depois.

NOTA: nao usa a fixture `db` (savepoint) do conftest porque _save_empresa_memory
faz commit() explicito (furaria o savepoint). Limpeza manual via _cleanup().
"""
import pytest

from app import db as _db
from app.agente.models import AgentMemory

_PREFIX = "/memories/empresa/heuristicas/_pytest_meta"


def _cleanup():
    AgentMemory.query.filter(AgentMemory.path.like(f"{_PREFIX}%")).delete(
        synchronize_session=False
    )
    _db.session.commit()


@pytest.fixture
def limpa(app):
    with app.app_context():
        _cleanup()
        yield
        _cleanup()


def test_save_empresa_memory_deriva_meta_de_path_estruturado(app, limpa):
    """Gerador empresa sem meta explicito: deriva via normalize_for_storage e
    normaliza o content XML legado para o sentinela canonico."""
    from app.agente.services.pattern_analyzer import _save_empresa_memory
    with app.app_context():
        path = f"{_PREFIX}/x.xml"
        content = (
            "<heuristica><nivel>5</nivel><titulo>T meta</titulo>"
            "<when>quando X</when><prescricao>faca Y</prescricao></heuristica>"
        )
        assert _save_empresa_memory(path, content, created_by=1)

        mem = AgentMemory.get_by_path(0, path)
        assert mem.meta is not None
        assert mem.meta["kind"] == "heuristica"
        assert mem.meta["nivel"] == 5
        assert mem.meta["do"] == "faca Y"
        # content normalizado (XML legado -> sentinela), parse foi 'full'
        assert mem.content.startswith("[heuristica]")
        assert "DO: faca Y" in mem.content
        assert "<heuristica>" not in mem.content


def test_save_empresa_memory_meta_explicito(app, limpa):
    """Gerador estruturado passa meta explicito (precedencia sobre o derivado)."""
    from app.agente.services.pattern_analyzer import _save_empresa_memory
    from app.agente.services.memory_format import build_meta, render_content
    with app.app_context():
        meta = build_meta(tipo="heuristica", nivel=5, titulo="Tit",
                          descricao="quando", prescricao="faca")
        path = f"{_PREFIX}/y.xml"
        assert _save_empresa_memory(path, render_content(meta), created_by=1, meta=meta)
        mem = AgentMemory.get_by_path(0, path)
        assert mem.meta["do"] == "faca"
        assert mem.meta["when"] == "quando"


def test_build_memory_index_agrupa_e_exclui_frias(app, limpa):
    """Indice: agrupa por kind, conta, exclui tier frio, e NAO inclui o conteudo."""
    from app.agente.tools.memory_mcp_tool import _build_memory_index
    from app.agente.services.memory_format import build_meta
    with app.app_context():
        for slug, cold in [("a", False), ("b", False), ("c", True)]:
            m = AgentMemory.create_file(0, f"{_PREFIX}/{slug}.xml", f"[heuristica] {slug}")
            m.escopo = "empresa"
            m.is_cold = cold
            m.meta = build_meta(tipo="heuristica", nivel=5, titulo=slug, prescricao="faca")
        _db.session.commit()

        text, st = _build_memory_index(0, prefix=_PREFIX)
        assert st["total"] == 2                       # fria excluida
        assert st["por_kind"]["heuristica"] == 2
        assert "WHEN:" not in text and "DO:" not in text  # sem conteudo, so indice

        # filtro por kind inexistente -> vazio
        _, st2 = _build_memory_index(0, prefix=_PREFIX, kind="armadilha")
        assert st2["total"] == 0

        # incluir_frias traz a fria de volta
        _, st3 = _build_memory_index(0, prefix=_PREFIX, incluir_frias=True)
        assert st3["total"] == 3


def test_build_memory_index_fallback_path_sem_meta(app, limpa):
    """Memoria legada sem meta: kind/dominio derivados do PATH (indice resiliente)."""
    from app.agente.tools.memory_mcp_tool import _build_memory_index
    with app.app_context():
        m = AgentMemory.create_file(
            0, f"{_PREFIX}/legada-sem-meta.xml", "<regra><descricao>x</descricao></regra>"
        )
        m.escopo = "empresa"
        _db.session.commit()
        _, st = _build_memory_index(0, prefix=_PREFIX)
        assert st["total"] == 1
        assert st["memories"][0]["kind"] == "heuristica"  # secao do path
        assert st["memories"][0]["titulo"]                # derivado do slug


def test_build_operational_directives_prefere_meta(app, limpa, monkeypatch):
    """Consumidor: quando ha meta, le titulo/when/do direto (sem regex fragil)."""
    import app.agente.config.feature_flags as ff
    monkeypatch.setattr(ff, "USE_OPERATIONAL_DIRECTIVES", True, raising=False)
    monkeypatch.setattr(ff, "MANDATORY_IMPORTANCE_THRESHOLD", 0.5, raising=False)
    monkeypatch.setattr(ff, "MANDATORY_MAX_COUNT", 12, raising=False)

    from app.agente.sdk.memory_injection import _build_operational_directives
    from app.agente.services.memory_format import build_meta, render_content
    with app.app_context():
        meta = build_meta(tipo="heuristica", nivel=5, titulo="Regra Meta XYZ",
                          when="quando Z", prescricao="faca ABC unico")
        m = AgentMemory.create_file(0, f"{_PREFIX}/consumidor.xml", render_content(meta))
        m.escopo = "empresa"
        m.importance_score = 0.9
        m.meta = meta
        _db.session.commit()

        out = _build_operational_directives(1)
        assert out is not None
        assert "faca ABC unico" in out
        assert "Regra Meta XYZ" in out


def test_memory_open_tag_inclui_atributos_meta():
    """6c: apresentacao XML enriquecida — atributos kind/dominio/nivel no <memory>."""
    from types import SimpleNamespace
    from app.agente.sdk.memory_injection import _memory_open_tag
    mem = SimpleNamespace(
        path="/memories/empresa/heuristicas/recebimento/x.xml",
        meta={"kind": "heuristica", "dominio": "recebimento", "nivel": 5},
    )
    tag = _memory_open_tag(mem, "heuristica")
    assert tag.startswith("<memory ") and tag.endswith(">")
    assert 'path="/memories/empresa/heuristicas/recebimento/x.xml"' in tag
    assert 'tier="heuristica"' in tag
    assert 'kind="heuristica"' in tag
    assert 'dominio="recebimento"' in tag
    assert 'nivel="5"' in tag


def test_memory_open_tag_sem_meta_robusto():
    """getattr: objeto legado/mock sem coluna meta -> so path (nao quebra)."""
    from types import SimpleNamespace
    from app.agente.sdk.memory_injection import _memory_open_tag
    mem = SimpleNamespace(path="/memories/user.xml")  # sem atributo meta
    assert _memory_open_tag(mem) == '<memory path="/memories/user.xml">'
