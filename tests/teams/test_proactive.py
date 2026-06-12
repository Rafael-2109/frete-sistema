"""Entrega proativa Teams (Fase C — Tasks C2/C3; Fase E2 — blocos parciais).

Cobre:
  - claim atomico de entrega em /bot/status ('polling' ganha 1x; se 'proactive'
    ja entregou -> {"status": "already_delivered"})
  - notify_function_delivery: claim 'proactive' + POST a function; rollback do
    claim se o POST falhar; gate de elapsed (so notifica task antiga o bastante
    para o polling ter morrido); no-op sem TEAMS_FUNCTION_URL.
  - persistencia do conversation_reference na TeamsTask.
  - Fase E2: notify_function_partial (blocos pos-polling SEM claim; offset
    proactive_partial_chars avanca SO apos POST 200) + entrega final por delta
    (resposta[offset:]; error ignora offset; delta vazio -> marcador).
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
               conversation_reference=None, partial_chars=None):
    from app.teams.models import TeamsTask
    from app.utils.timezone import agora_utc_naive
    t = TeamsTask(
        conversation_id=f'19:test{uuid.uuid4().hex}@thread.v2',
        user_name='Teste Proactive',
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
            "UPDATE teams_tasks SET created_at = :ts WHERE id = :id"
        ), {'ts': agora_utc_naive() - timedelta(minutes=minutos_atras), 'id': t.id})
        _db.session.commit()
    if partial_chars is not None:
        from sqlalchemy import text as sql_text
        _db.session.execute(sql_text(
            "UPDATE teams_tasks SET proactive_partial_chars = :n WHERE id = :id"
        ), {'n': partial_chars, 'id': t.id})
        _db.session.commit()
    return t


def _fake_post_200(chamadas):
    def fake_post(url, **kwargs):
        chamadas.append((url, kwargs))

        class R:
            status_code = 200
            text = 'ok'
        return R()
    return fake_post


def _cleanup(tasks):
    try:
        _db.session.rollback()
        for t in tasks:
            obj = _db.session.merge(t)
            _db.session.delete(obj)
        _db.session.commit()
    except Exception:
        _db.session.rollback()


class TestClaimPollingNoStatus:
    def test_primeira_consulta_clama_polling(self, app_ctx, monkeypatch):
        import app.teams.bot_routes as br
        monkeypatch.setattr(br, 'TEAMS_BOT_API_KEY', 'test-key')
        t = _nova_task(status='completed')
        try:
            client = app_ctx.test_client()
            resp = client.get(f'/api/teams/bot/status/{t.id}',
                              headers={'X-API-Key': 'test-key'})
            assert resp.status_code == 200
            assert resp.get_json()['status'] == 'completed'
            _db.session.expire_all()
            assert _db.session.merge(t).delivered_via == 'polling'
        finally:
            _cleanup([t])

    def test_ja_entregue_proactive_responde_already_delivered(self, app_ctx, monkeypatch):
        import app.teams.bot_routes as br
        monkeypatch.setattr(br, 'TEAMS_BOT_API_KEY', 'test-key')
        t = _nova_task(status='completed')
        try:
            from sqlalchemy import text as sql_text
            _db.session.execute(sql_text(
                "UPDATE teams_tasks SET delivered_via='proactive' WHERE id=:id"
            ), {'id': t.id})
            _db.session.commit()
            client = app_ctx.test_client()
            resp = client.get(f'/api/teams/bot/status/{t.id}',
                              headers={'X-API-Key': 'test-key'})
            assert resp.status_code == 200
            assert resp.get_json()['status'] == 'already_delivered'
        finally:
            _cleanup([t])

    def test_polling_repetido_continua_entregando(self, app_ctx, monkeypatch):
        """2a consulta do MESMO polling (claim ja e 'polling') segue retornando a resposta."""
        import app.teams.bot_routes as br
        monkeypatch.setattr(br, 'TEAMS_BOT_API_KEY', 'test-key')
        t = _nova_task(status='completed')
        try:
            client = app_ctx.test_client()
            client.get(f'/api/teams/bot/status/{t.id}', headers={'X-API-Key': 'test-key'})
            resp2 = client.get(f'/api/teams/bot/status/{t.id}', headers={'X-API-Key': 'test-key'})
            assert resp2.get_json()['status'] == 'completed'
        finally:
            _cleanup([t])


class TestNotifyFunctionDelivery:
    def test_sem_url_configurada_e_noop(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: '')
        t = _nova_task(status='completed', minutos_atras=10)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is False
            assert out['motivo'] == 'sem_url'
        finally:
            _cleanup([t])

    def test_task_recente_nao_notifica(self, app_ctx, monkeypatch):
        """Polling ainda vivo (elapsed < min_elapsed) -> deixa o polling entregar."""
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        t = _nova_task(status='completed', minutos_atras=0,
                       conversation_reference={'conversation': {'id': 'x'}})
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is False
            assert out['motivo'] == 'polling_vivo'
        finally:
            _cleanup([t])

    def test_post_ok_clama_proactive(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []

        def fake_post(url, **kwargs):
            chamadas.append((url, kwargs))
            class R:
                status_code = 200
                text = 'ok'
            return R()
        monkeypatch.setattr(proactive.requests, 'post', fake_post)
        t = _nova_task(status='completed', minutos_atras=10,
                       conversation_reference={'conversation': {'id': 'x'}})
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is True
            assert len(chamadas) == 1
            assert '/api/notify' in chamadas[0][0]
            _db.session.expire_all()
            assert _db.session.merge(t).delivered_via == 'proactive'
        finally:
            _cleanup([t])

    def test_post_falha_faz_rollback_do_claim(self, app_ctx, monkeypatch):
        import time as _time
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        monkeypatch.setattr(_time, 'sleep', lambda s: None)  # retry+backoff: nao dormir

        def fake_post(url, **kwargs):
            raise ConnectionError('function fora do ar')
        monkeypatch.setattr(proactive.requests, 'post', fake_post)
        t = _nova_task(status='completed', minutos_atras=10,
                       conversation_reference={'conversation': {'id': 'x'}})
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is False
            _db.session.expire_all()
            # claim revertido — polling (se vivo) ou retry futuro pode entregar
            assert _db.session.merge(t).delivered_via is None
        finally:
            _cleanup([t])

    def test_sem_conversation_reference_nao_notifica(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        t = _nova_task(status='completed', minutos_atras=10, conversation_reference=None)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is False
            assert out['motivo'] == 'sem_reference'
        finally:
            _cleanup([t])


class TestNotifyFunctionPartial:
    """Fase E2: blocos proativos pos-polling (sem claim; offset por CAS)."""

    REF = {'conversation': {'id': 'x'}}

    def test_partial_envia_delta_sem_clamar_e_avanca_offset(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        resposta = 'x' * 500  # sem quebra de linha — delta integral
        t = _nova_task(status='processing', resposta=resposta, minutos_atras=10,
                       conversation_reference=self.REF)
        try:
            out = proactive.notify_function_partial(t.id)
            assert out['ok'] is True
            assert len(chamadas) == 1
            payload = chamadas[0][1]['json']
            assert payload['tipo'] == 'partial'
            assert payload['texto_delta'] == resposta
            assert payload['task_id'] == t.id
            assert payload['conversation_reference'] == self.REF
            _db.session.expire_all()
            t2 = _db.session.merge(t)
            assert t2.delivered_via is None          # partial NUNCA clama
            assert t2.proactive_partial_chars == 500
        finally:
            _cleanup([t])

    def test_partial_corta_em_quebra_de_paragrafo(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        resposta = 'a' * 300 + '\n\n' + 'b' * 50
        t = _nova_task(status='processing', resposta=resposta, minutos_atras=10,
                       conversation_reference=self.REF)
        try:
            out = proactive.notify_function_partial(t.id)
            assert out['ok'] is True
            payload = chamadas[0][1]['json']
            assert payload['texto_delta'] == 'a' * 300  # corta no \n\n
            _db.session.expire_all()
            assert _db.session.merge(t).proactive_partial_chars == 300
        finally:
            _cleanup([t])

    def test_partial_post_falha_nao_avanca_offset(self, app_ctx, monkeypatch):
        import time as _time
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        monkeypatch.setattr(_time, 'sleep', lambda s: None)  # retry+backoff: nao dormir

        def fake_post(url, **kwargs):
            raise ConnectionError('function fora do ar')
        monkeypatch.setattr(proactive.requests, 'post', fake_post)
        t = _nova_task(status='processing', resposta='x' * 500, minutos_atras=10,
                       conversation_reference=self.REF)
        try:
            out = proactive.notify_function_partial(t.id)
            assert out['ok'] is False
            _db.session.expire_all()
            t2 = _db.session.merge(t)
            assert t2.proactive_partial_chars == 0   # offset NAO avancou
            assert t2.delivered_via is None
        finally:
            _cleanup([t])

    def test_partial_delta_pequeno_nao_envia(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        t = _nova_task(status='processing', resposta='x' * 100, minutos_atras=10,
                       conversation_reference=self.REF)
        try:
            out = proactive.notify_function_partial(t.id)
            assert out['ok'] is False
            assert out['motivo'] == 'delta_pequeno'
            assert chamadas == []
        finally:
            _cleanup([t])

    def test_partial_respeita_offset_anterior(self, app_ctx, monkeypatch):
        """Delta = resposta[offset:] — blocos anteriores nao sao reenviados."""
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        resposta = 'a' * 300 + 'b' * 300
        t = _nova_task(status='processing', resposta=resposta, minutos_atras=10,
                       conversation_reference=self.REF, partial_chars=300)
        try:
            out = proactive.notify_function_partial(t.id)
            assert out['ok'] is True
            assert chamadas[0][1]['json']['texto_delta'] == 'b' * 300
            _db.session.expire_all()
            assert _db.session.merge(t).proactive_partial_chars == 600
        finally:
            _cleanup([t])

    def test_partial_polling_vivo_nao_envia(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        t = _nova_task(status='processing', resposta='x' * 500, minutos_atras=0,
                       conversation_reference=self.REF)
        try:
            out = proactive.notify_function_partial(t.id)
            assert out['ok'] is False
            assert out['motivo'] == 'polling_vivo'
        finally:
            _cleanup([t])

    def test_partial_status_nao_processing_nao_envia(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        t = _nova_task(status='completed', resposta='x' * 500, minutos_atras=10,
                       conversation_reference=self.REF)
        try:
            out = proactive.notify_function_partial(t.id)
            assert out['ok'] is False
            assert out['motivo'] == 'task_nao_processing'
        finally:
            _cleanup([t])


class TestFinalDeltaPorOffset:
    """Fase E2: entrega final envia apenas resposta[proactive_partial_chars:]."""

    REF = {'conversation': {'id': 'x'}}

    def test_final_envia_somente_delta(self, app_ctx, monkeypatch):
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        resposta = 'x' * 1000
        t = _nova_task(status='completed', resposta=resposta, minutos_atras=10,
                       conversation_reference=self.REF, partial_chars=600)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is True
            payload = chamadas[0][1]['json']
            assert payload['tipo'] == 'final'
            assert payload['resposta'] == 'x' * 400
        finally:
            _cleanup([t])

    def test_final_offset_zero_envia_resposta_completa(self, app_ctx, monkeypatch):
        """Comportamento atual preservado quando nenhum bloco foi entregue."""
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        resposta = 'resposta completa do agente ' * 10
        t = _nova_task(status='completed', resposta=resposta, minutos_atras=10,
                       conversation_reference=self.REF)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is True
            assert chamadas[0][1]['json']['resposta'] == resposta
        finally:
            _cleanup([t])

    def test_final_delta_vazio_envia_marcador(self, app_ctx, monkeypatch):
        """Blocos ja entregaram tudo -> final envia marcador (nunca 'Sem resposta')."""
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        resposta = 'x' * 500
        t = _nova_task(status='completed', resposta=resposta, minutos_atras=10,
                       conversation_reference=self.REF, partial_chars=500)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is True
            assert chamadas[0][1]['json']['resposta'] == proactive.PARTIAL_FINAL_MARKER
            _db.session.expire_all()
            assert _db.session.merge(t).delivered_via == 'proactive'  # claim intocado
        finally:
            _cleanup([t])

    def test_final_error_ignora_offset(self, app_ctx, monkeypatch):
        """Texto de erro SUBSTITUI o parcial (nao continua) -> envia completo."""
        from app.teams import proactive
        monkeypatch.setattr(proactive, '_function_url', lambda: 'https://fake.azurewebsites.net')
        chamadas = []
        monkeypatch.setattr(proactive.requests, 'post', _fake_post_200(chamadas))
        resposta = 'Erro ao processar: deu ruim.'
        t = _nova_task(status='error', resposta=resposta, minutos_atras=10,
                       conversation_reference=self.REF, partial_chars=600)
        try:
            out = proactive.notify_function_delivery(t.id)
            assert out['ok'] is True
            assert chamadas[0][1]['json']['resposta'] == resposta
        finally:
            _cleanup([t])
