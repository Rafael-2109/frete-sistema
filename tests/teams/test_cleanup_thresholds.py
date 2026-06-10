"""Thresholds do cleanup lazy de TeamsTask (Fase C — Task C4).

Novos thresholds (eram 5/5/10 min):
  - pending/processing: 15 min (heartbeat renova updated_at a cada 60s; task
    sem heartbeat por 15 min = thread realmente morta)
  - awaiting_user_input: 30 min (usuario pode demorar a responder o card)
  - queued: 15 min
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
    })
    with _app.app_context():
        yield _app


def _nova_task(status, minutos_sem_update):
    from sqlalchemy import text as sql_text
    from app.teams.models import TeamsTask
    from app.utils.timezone import agora_utc_naive
    t = TeamsTask(
        conversation_id=f'cleanup-test-{uuid.uuid4().hex}',
        user_name='Cleanup Test',
        status=status,
        mensagem='msg',
    )
    _db.session.add(t)
    _db.session.commit()
    _db.session.execute(sql_text(
        "UPDATE teams_tasks SET updated_at = :ts WHERE id = :id"
    ), {'ts': agora_utc_naive() - timedelta(minutes=minutos_sem_update), 'id': t.id})
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


def _status_de(task):
    _db.session.expire_all()
    return _db.session.merge(task).status


class TestCleanupThresholds:
    def test_processing_10min_sobrevive_20min_morre(self, app_ctx):
        from app.teams.services import cleanup_stale_teams_tasks
        viva = _nova_task('processing', 10)
        morta = _nova_task('processing', 20)
        try:
            cleanup_stale_teams_tasks()
            assert _status_de(viva) == 'processing'
            assert _status_de(morta) == 'timeout'
        finally:
            _cleanup([viva, morta])

    def test_awaiting_20min_sobrevive_40min_morre(self, app_ctx):
        from app.teams.services import cleanup_stale_teams_tasks
        viva = _nova_task('awaiting_user_input', 20)
        morta = _nova_task('awaiting_user_input', 40)
        try:
            cleanup_stale_teams_tasks()
            assert _status_de(viva) == 'awaiting_user_input'
            assert _status_de(morta) == 'timeout'
        finally:
            _cleanup([viva, morta])

    def test_queued_10min_sobrevive_20min_morre(self, app_ctx):
        from app.teams.services import cleanup_stale_teams_tasks
        viva = _nova_task('queued', 10)
        morta = _nova_task('queued', 20)
        try:
            cleanup_stale_teams_tasks()
            assert _status_de(viva) == 'queued'
            assert _status_de(morta) == 'timeout'
        finally:
            _cleanup([viva, morta])
