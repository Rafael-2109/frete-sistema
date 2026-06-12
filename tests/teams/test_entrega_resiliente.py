"""P0 — Entrega resiliente do Teams (worktree fix/teams-entrega-resiliente).

Root cause provado: a Azure Function `frete-bot-func` esta no plano Consumption
(`sku: Dynamic`, `alwaysOn: false`, escala a zero). Em cold-start o `POST
/api/notify` do backend leva `Connection refused` TRANSITORIO. O desenho atual
desiste na 1a falha e nao tem rede de seguranca -> respostas longas "morrem mudas"
(48 tasks `completed` + `delivered_via IS NULL` em 7 dias).

Cobre:
  - retry+backoff no POST a function (absorve o refused transitorio de cold-start);
  - reconciliador: re-entrega tasks orfas (completed/error + delivered_via NULL +
    conversation_reference) quando a function volta a ficar alcancavel.
"""
import uuid
from datetime import timedelta

import pytest

from app import create_app, db as _db


@pytest.fixture(scope='module')
def app_ctx():
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
    })
    with _app.app_context():
        yield _app


def _nova_task(status='completed', resposta='resposta pronta', minutos_atras=0,
               conversation_reference=None):
    from app.teams.models import TeamsTask
    from app.utils.timezone import agora_utc_naive
    t = TeamsTask(
        conversation_id=f'19:test{uuid.uuid4().hex}@thread.v2',
        user_name='Teste Resiliente',
        status=status,
        mensagem='pergunta',
        resposta=resposta,
        conversation_reference=conversation_reference,
    )
    _db.session.add(t)
    _db.session.commit()
    if minutos_atras:
        from sqlalchemy import text as sql_text
        _db.session.execute(sql_text(
            "UPDATE teams_tasks SET created_at = :ts, completed_at = :ts WHERE id = :id"
        ), {'ts': agora_utc_naive() - timedelta(minutes=minutos_atras), 'id': t.id})
        _db.session.commit()
    return t


def _cleanup(tasks):
    try:
        _db.session.rollback()
        for t in tasks:
            obj = _db.session.merge(t)
            _db.session.delete(obj)
        _db.session.commit()
    except Exception:
        _db.session.rollback()


class TestRetryNotify:
    """Retry+backoff absorve o Connection refused transitorio de cold-start."""

    REF = {'conversation': {'id': 'x'}}

    def test_retenta_e_entrega_apos_refused_transitorio(self, app_ctx, monkeypatch):
        import time as _time
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        monkeypatch.setattr(_time, 'sleep', lambda s: None)  # nao dormir no teste
        tentativas = {'n': 0}

        def fake_post(url, **kwargs):
            tentativas['n'] += 1
            if tentativas['n'] < 3:
                raise ConnectionError('[Errno 111] Connection refused')

            class R:
                status_code = 200
                text = 'ok'
            return R()
        monkeypatch.setattr(proactive.requests, 'post', fake_post)
        t = _nova_task(status='completed', minutos_atras=10, conversation_reference=self.REF)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is True, out
            assert tentativas['n'] == 3  # 2 refused + 1 sucesso
            _db.session.expire_all()
            assert _db.session.merge(t).delivered_via == 'proactive'
        finally:
            _cleanup([t])

    def test_esgota_tentativas_e_faz_rollback_do_claim(self, app_ctx, monkeypatch):
        import time as _time
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        monkeypatch.setattr(_time, 'sleep', lambda s: None)
        tentativas = {'n': 0}

        def fake_post(url, **kwargs):
            tentativas['n'] += 1
            raise ConnectionError('function fria — RST')
        monkeypatch.setattr(proactive.requests, 'post', fake_post)
        t = _nova_task(status='completed', minutos_atras=10, conversation_reference=self.REF)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is False
            assert tentativas['n'] >= 2  # tentou mais de uma vez antes de desistir
            _db.session.expire_all()
            assert _db.session.merge(t).delivered_via is None  # claim revertido
        finally:
            _cleanup([t])


class TestReconciliador:
    """Rede de seguranca: re-entrega tasks finais orfas (delivered_via NULL)."""

    REF = {'conversation': {'id': 'x'}}

    def _fake_post_200(self, chamadas):
        def fake_post(url, **kwargs):
            chamadas.append(url)

            class R:
                status_code = 200
                text = 'ok'
            return R()
        return fake_post

    def test_reentrega_orfa_elegivel_e_ignora_resto(self, app_ctx, monkeypatch):
        import time as _time
        from sqlalchemy import text as sql_text
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        monkeypatch.setattr(_time, 'sleep', lambda s: None)
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', self._fake_post_200(chamadas))

        orfa = _nova_task(status='completed', minutos_atras=10, conversation_reference=self.REF)
        antiga = _nova_task(status='completed', minutos_atras=5000, conversation_reference=self.REF)
        entregue = _nova_task(status='completed', minutos_atras=10, conversation_reference=self.REF)
        _db.session.execute(sql_text(
            "UPDATE teams_tasks SET delivered_via='polling' WHERE id=:id"), {'id': entregue.id})
        sem_ref = _nova_task(status='completed', minutos_atras=10, conversation_reference=None)
        _db.session.commit()
        try:
            # janela curta isola das orfas reais do banco de dev
            res = proactive.reconciliar_entregas_pendentes(max_age_min=60)
            _db.session.expire_all()
            assert _db.session.merge(orfa).delivered_via == 'proactive'    # re-entregue
            assert _db.session.merge(antiga).delivered_via is None         # idade > teto
            assert _db.session.merge(entregue).delivered_via == 'polling'  # intocada
            assert _db.session.merge(sem_ref).delivered_via is None        # sem ref
            assert res['entregues'] >= 1
        finally:
            _cleanup([orfa, antiga, entregue, sem_ref])

    def test_flag_off_e_noop(self, app_ctx, monkeypatch):
        from app.teams import proactive
        import app.agente.config.feature_flags as ff
        monkeypatch.setattr(ff, 'TEAMS_RECONCILE_ENABLED', False, raising=False)
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        orfa = _nova_task(status='completed', minutos_atras=10, conversation_reference=self.REF)
        try:
            res = proactive.reconciliar_entregas_pendentes(max_age_min=60)
            assert res.get('motivo') == 'flag_off'
            _db.session.expire_all()
            assert _db.session.merge(orfa).delivered_via is None
        finally:
            _cleanup([orfa])
