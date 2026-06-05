"""Backend da tela de GESTAO de memorias (admin) — substitui a session-store.

Testa as funcoes core (query com filtros + stats) com DB real. As rotas finas (auth + jsonify)
sao validadas a parte. Fixture `limpa` purga /memories/ do usuario de teste (setup+teardown).
"""
import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    user = Usuario.query.filter_by(email='test_mem_admin@test.com').first()
    if user:
        return user
    user = Usuario(email='test_mem_admin@test.com', nome='Test Mem Admin',
                   perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def limpa(app, test_user):
    uid = test_user.id

    def _purge():
        try:
            db.session.rollback()
        except Exception:
            pass
        for m in AgentMemory.query.filter(
            AgentMemory.user_id == uid,
            AgentMemory.path.like('/memories/%'),
        ).all():
            db.session.delete(m)
        db.session.commit()

    _purge()
    yield uid
    _purge()


def _mem(user_id, path, *, content='[correcao] x\nDO: y', category='structural',
         priority='contextual', is_cold=False, conflict=False, error_signature=None,
         harmful_count=0, reviewed=False):
    m = AgentMemory.create_file(user_id, path, content)
    m.category = category
    m.priority = priority
    m.is_cold = is_cold
    m.has_potential_conflict = conflict
    m.error_signature = error_signature
    m.harmful_count = harmful_count
    if reviewed:
        from app.utils.timezone import agora_utc_naive
        m.reviewed_at = agora_utc_naive()
    db.session.commit()
    return m


def _cenario(uid):
    """4 vivas (1 conflito, 1 dura) + 1 cold."""
    _mem(uid, '/memories/corrections/m1.xml')
    _mem(uid, '/memories/corrections/m2.xml', conflict=True)
    _mem(uid, '/memories/corrections/m3.xml', priority='mandatory',
         error_signature='sig_dura', harmful_count=2)
    _mem(uid, '/memories/empresa/regras/m5.xml', category='empresa')
    _mem(uid, '/memories/corrections/m4cold.xml', is_cold=True)


# ───────────────────────── query_admin_memories ─────────────────────────

def test_query_lista_vivas_exclui_cold_e_diretorio(app, limpa):
    from app.agente.routes.memories import query_admin_memories
    uid = limpa
    _cenario(uid)
    res = query_admin_memories(user_id=uid)
    paths = {r['path'] for r in res}
    assert '/memories/corrections/m1.xml' in paths
    assert '/memories/corrections/m4cold.xml' not in paths   # cold excluida por default
    assert not any(r.get('is_directory') for r in res)        # nenhum diretorio
    assert len([r for r in res if r['path'].startswith('/memories/corrections/m')
                or r['path'].endswith('m5.xml')]) == 4


def test_query_conflicts_only(app, limpa):
    from app.agente.routes.memories import query_admin_memories
    uid = limpa
    _cenario(uid)
    res = query_admin_memories(user_id=uid, conflicts_only=True)
    assert {r['path'] for r in res} == {'/memories/corrections/m2.xml'}
    assert res[0]['has_potential_conflict'] is True


def test_query_include_cold(app, limpa):
    from app.agente.routes.memories import query_admin_memories
    uid = limpa
    _cenario(uid)
    res = query_admin_memories(user_id=uid, include_cold=True)
    assert '/memories/corrections/m4cold.xml' in {r['path'] for r in res}


def test_query_filtra_category(app, limpa):
    from app.agente.routes.memories import query_admin_memories
    uid = limpa
    _cenario(uid)
    res = query_admin_memories(user_id=uid, category='empresa')
    assert {r['path'] for r in res} == {'/memories/empresa/regras/m5.xml'}


def test_query_search_em_path_e_conteudo(app, limpa):
    from app.agente.routes.memories import query_admin_memories
    uid = limpa
    _mem(uid, '/memories/corrections/busca-unica.xml', content='conteudo NORTEMBA especial')
    res_path = query_admin_memories(user_id=uid, search='busca-unica')
    res_content = query_admin_memories(user_id=uid, search='NORTEMBA')
    assert any(r['path'].endswith('busca-unica.xml') for r in res_path)
    assert any(r['path'].endswith('busca-unica.xml') for r in res_content)


def test_query_payload_completo(app, limpa):
    from app.agente.routes.memories import query_admin_memories
    uid = limpa
    _cenario(uid)
    res = query_admin_memories(user_id=uid)
    dura = next(r for r in res if r['path'].endswith('m3.xml'))
    assert dura['is_hard_rule'] is True                # priority mandatory
    assert dura['error_signature'] == 'sig_dura'
    assert dura['harmful_count'] == 2
    assert 'correction_count' in dura and 'usage_count' in dura


def test_query_conflitos_primeiro_na_ordenacao(app, limpa):
    from app.agente.routes.memories import query_admin_memories
    uid = limpa
    _cenario(uid)
    res = query_admin_memories(user_id=uid)
    assert res[0]['has_potential_conflict'] is True   # conflitos no topo


# ───────────────────────── compute_memory_stats ─────────────────────────

def test_stats_conta_total_conflitos_duras_cold(app, limpa):
    from app.agente.routes.memories import compute_memory_stats
    uid = limpa
    _cenario(uid)
    s = compute_memory_stats(user_id=uid)
    assert s['total'] == 4          # vivas (exclui cold)
    assert s['conflicts'] == 1
    assert s['hard_rules'] == 1     # priority mandatory
    assert s['cold'] == 1
