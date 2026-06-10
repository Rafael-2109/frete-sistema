"""FRENTE 2 (plano 2026-06-10-engenharia-memoria-rerank-write-quality) —
validacao INSTRUTIVA no write-path de memorias operativas.

Diagnostico 2.1 (PROD 2026-06-10): 144 memorias de conhecimento ativas sem
meta.do; o fluxo VIVO (save_memory do agente) seguia gravando formatos que o
parser nao extraia. Apos o parser FRENTE 2 (armadilha/protocolo/escapado),
o residuo legitimo e content SEM acao extraivel — nesses casos a tool deve
retornar erro instrutivo (self-healing: o agente reescreve na hora, padrao
ja usado em outros guards). NAO bloqueia paths narrativos/perfil (meta=None).

Tambem cobre o gap colateral: update_memory (str-replace) alterava content
sem re-derivar meta -> meta stale.
"""
import pytest

from app.agente.tools.memory_mcp_tool import _formato_operativo_error


class TestFormatoOperativoError:
    def test_path_nao_estruturado_meta_none_passa(self):
        # user.xml, learned/, pendencias/ etc: normalize retorna meta=None
        assert _formato_operativo_error("/memories/user.xml", None) is None

    def test_meta_com_do_passa(self):
        meta = {"kind": "armadilha", "titulo": "T", "do": "faca X"}
        assert _formato_operativo_error(
            "/memories/empresa/armadilhas/fiscal/x.xml", meta
        ) is None

    def test_meta_estruturado_sem_do_retorna_erro_instrutivo(self):
        meta = {"kind": "armadilha", "titulo": "T", "when": "quando X",
                "parse": "partial"}
        msg = _formato_operativo_error(
            "/memories/empresa/armadilhas/fiscal/x.xml", meta
        )
        assert msg is not None
        # instrutivo: template sentinela completo para o agente reescrever
        assert "WHEN:" in msg
        assert "DO:" in msg
        assert "[armadilha" in msg


@pytest.fixture
def app_ctx():
    from app import create_app
    app = create_app()
    with app.app_context():
        yield app


_PREFIX = "/memories/empresa/armadilhas/_pytest_fmt_operativo"


def _cleanup():
    from app import db
    from app.agente.models import AgentMemory, AgentMemoryVersion
    mems = AgentMemory.query.filter(AgentMemory.path.like(f"{_PREFIX}%")).all()
    for m in mems:
        AgentMemoryVersion.query.filter_by(memory_id=m.id).delete(
            synchronize_session=False
        )
        from app import db as _d
        _d.session.delete(m)
    db.session.commit()


def test_rederive_meta_apos_content_change(app_ctx):
    """Helper chamado pelo update_memory apos o str-replace: meta NAO pode
    ficar stale em relacao ao content editado (path estruturado)."""
    from app import db
    from app.agente.models import AgentMemory
    from app.agente.services.memory_format import build_meta, render_content
    from app.agente.tools.memory_mcp_tool import _rederive_meta_after_content_change

    _cleanup()
    try:
        path = f"{_PREFIX}/caso.xml"
        meta = build_meta(tipo="armadilha", titulo="T", dominio="fiscal",
                          when="quando X", do="faca Y")
        mem = AgentMemory.create_file(0, path, render_content(meta))
        mem.escopo = "empresa"
        mem.meta = meta
        db.session.commit()

        # simula o str-replace do update_memory
        mem.content = mem.content.replace("DO: faca Y", "DO: faca Z")
        _rederive_meta_after_content_change(mem)
        db.session.commit()

        atual = AgentMemory.get_by_path(0, path)
        assert atual.meta["do"] == "faca Z", "meta.do stale apos update"
        assert atual.meta["when"] == "quando X"
    finally:
        _cleanup()


def test_rederive_meta_path_nao_estruturado_nao_toca(app_ctx):
    """Perfil/learned (meta None por design) seguem sem meta apos update."""
    from app import db
    from app.agente.models import AgentMemory
    from app.agente.tools.memory_mcp_tool import _rederive_meta_after_content_change

    path = "/memories/learned/_pytest_fmt_operativo_livre.xml"
    AgentMemory.query.filter_by(path=path).delete(synchronize_session=False)
    db.session.commit()
    try:
        mem = AgentMemory.create_file(1, path, "texto livre qualquer")
        db.session.commit()
        mem.content = "texto livre editado"
        _rederive_meta_after_content_change(mem)
        assert mem.meta is None
    finally:
        AgentMemory.query.filter_by(path=path).delete(synchronize_session=False)
        db.session.commit()
