"""Fallback ORGANICO 1b: quando o extrator pos-sessao OMITE error_signature numa correcao,
`_save_personal_insight` gera a assinatura via helper ANTES de gravar e de rastrear reincidencia.

Fecha o ~40% residual de omissao do extrator (medido em PROD 2026-06-04), reusando o mesmo helper
do backfill universal. Best-effort: se o helper falhar, a correcao ainda e salva (sem assinatura).

gerar_error_signature e' SEMPRE mockado -> sem custo de API. O fixture `limpa` purga as correcoes
do usuario de teste no setup E teardown (idempotente, robusto a residuo de runs anteriores).
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
    user = Usuario.query.filter_by(email='test_sig_fallback@test.com').first()
    if user:
        return user
    user = Usuario(email='test_sig_fallback@test.com', nome='Test Sig Fallback',
                   perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def limpa(app, test_user):
    """Purga /memories/corrections/ do usuario de teste antes e depois (idempotente).

    Usa db.session.delete por objeto (dispara cascade de versoes/embeddings, ao contrario de
    query.delete()). Robusto a residuo de execucoes anteriores que tenham vazado.
    """
    uid = test_user.id

    def _purge():
        try:
            db.session.rollback()
        except Exception:
            pass
        for m in AgentMemory.query.filter(
            AgentMemory.user_id == uid,
            AgentMemory.path.like('/memories/corrections/%'),
        ).all():
            db.session.delete(m)
        db.session.commit()

    _purge()
    yield uid
    _purge()


def _mock_dedup_none(monkeypatch):
    import app.agente.tools.memory_mcp_tool as mm
    monkeypatch.setattr(mm, '_check_memory_duplicate',
                        lambda uid, content, current_path='': None)


def test_correcao_sem_signature_recebe_assinatura_gerada(app, limpa, monkeypatch):
    """Extrator omitiu (error_signature='') -> 1b gera e grava a assinatura."""
    user_id = limpa
    _mock_dedup_none(monkeypatch)
    import app.agente.services.pattern_analyzer as pa
    monkeypatch.setattr(pa, 'gerar_error_signature', lambda desc, presc='', **k: 'gerada_auto')

    ok = pa._save_personal_insight(
        user_id, 'correcao',
        'agente respondeu sobre o cluster errado de novo',
        'confirmar qual cluster antes de buscar',
        error_signature='',  # extrator OMITIU
    )
    assert ok is True
    mem = AgentMemory.query.filter(
        AgentMemory.user_id == user_id,
        AgentMemory.error_signature == 'gerada_auto',
    ).first()
    assert mem is not None


def test_correcao_com_signature_do_extrator_mantem_a_original(app, limpa, monkeypatch):
    """Quando o extrator JA emitiu a assinatura, o 1b NAO chama o helper (respeita a original)."""
    user_id = limpa
    _mock_dedup_none(monkeypatch)
    import app.agente.services.pattern_analyzer as pa
    chamado = {'n': 0}

    def _fake(desc, presc='', **k):
        chamado['n'] += 1
        return 'NAO_DEVE_USAR'

    monkeypatch.setattr(pa, 'gerar_error_signature', _fake)

    ok = pa._save_personal_insight(
        user_id, 'correcao', 'erro que ja veio assinado', 'prescricao qualquer',
        error_signature='veio_do_extrator',
    )
    assert ok is True
    mem = AgentMemory.query.filter(
        AgentMemory.user_id == user_id,
        AgentMemory.error_signature == 'veio_do_extrator',
    ).first()
    assert mem is not None
    assert chamado['n'] == 0  # helper NAO chamado quando ja ha assinatura


def test_fallback_best_effort_nao_quebra_o_save(app, limpa, monkeypatch):
    """Se o helper levantar excecao, a correcao ainda e salva (sem assinatura)."""
    user_id = limpa
    _mock_dedup_none(monkeypatch)
    import app.agente.services.pattern_analyzer as pa

    def _boom(desc, presc='', **k):
        raise RuntimeError('llm explodiu')

    monkeypatch.setattr(pa, 'gerar_error_signature', _boom)

    ok = pa._save_personal_insight(
        user_id, 'correcao', 'erro relevante que importa muito', 'faca assim',
        error_signature='',
    )
    assert ok is True  # salvou apesar do helper quebrar
    mem = AgentMemory.query.filter(
        AgentMemory.user_id == user_id,
        AgentMemory.content.like('%erro relevante que importa muito%'),
    ).first()
    assert mem is not None
    assert mem.error_signature is None  # degradou sem quebrar


def test_fallback_alimenta_track_recurrence(app, limpa, monkeypatch):
    """A assinatura gerada no 1b RASTREIA reincidencia: regra dura viva com a mesma
    assinatura recebe harmful++ mesmo quando o extrator nao emitiu o campo."""
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_OUTCOME_TRACKING', True)
    user_id = limpa
    regra = AgentMemory.create_file(
        user_id, '/memories/corrections/dura-reincidente.xml', '[correcao] x\nDO: y')
    regra.priority = 'mandatory'
    regra.error_signature = 'erro_reincidente'
    regra.harmful_count = 0
    db.session.commit()

    _mock_dedup_none(monkeypatch)
    import app.agente.services.pattern_analyzer as pa
    monkeypatch.setattr(pa, 'gerar_error_signature', lambda desc, presc='', **k: 'erro_reincidente')

    ok = pa._save_personal_insight(
        user_id, 'correcao', 'usuario corrigiu o mesmo erro outra vez', 'fazer certo agora',
        error_signature='',  # extrator OMITIU, mas o 1b vai gerar 'erro_reincidente'
    )
    assert ok is True
    db.session.refresh(regra)
    assert regra.harmful_count == 1  # reincidencia casada pela assinatura GERADA no fallback
