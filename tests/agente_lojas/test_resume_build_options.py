"""
Regressao FIX S1 (multi-turno): build_options deve usar `resume=` (carrega o
JSONL) em vez de `session_id=` (so nomeia) a partir do turno 2, e nunca os dois
juntos (--session-id + --resume exigiria --fork-session; forkar X->X = exit 1).

Antes do fix, o modulo passava apenas session_id reusando o id do turno
anterior -> amnesia + colisao de JSONL. Ver app/agente_lojas/sdk/client.py e
app/agente/sdk/client.py:2842 (_with_resume).
"""
import uuid

import pytest

from app.agente_lojas.sdk.client import get_lojas_client


def _build(sdk_session_id):
    client = get_lojas_client()
    return client.build_options(
        user_id=1,
        user_name='Test',
        perfil='administrador',
        loja_hora_id=None,
        sdk_session_id=sdk_session_id,
    )


class TestResumeBuildOptions:
    def test_turno1_sem_sdk_session_id_nao_seta_resume_nem_session_id(self):
        """Turno 1: SDK gera o id; nada de resume/session_id no build."""
        o = _build(None)
        assert getattr(o, 'resume', None) is None
        assert getattr(o, 'session_id', None) is None

    def test_turno2_uuid_valido_seta_resume_e_nao_session_id(self):
        """Turno 2+: resume=X (carrega historico) SEM session_id (evita fork)."""
        sid = str(uuid.uuid4())
        o = _build(sid)
        assert o.resume == sid
        assert getattr(o, 'session_id', None) is None

    @pytest.mark.parametrize('bad', ['teams_19:abc', 'not-a-uuid', '12345'])
    def test_sdk_session_id_invalido_e_ignorado(self, bad):
        """ID nao-UUID (dado envenenado) nao vira --resume (evitaria exit 1)."""
        o = _build(bad)
        assert getattr(o, 'resume', None) is None
        assert getattr(o, 'session_id', None) is None


class TestSessionIdTurno1:
    """F1.5(a): turno 1 pre-nomeia o JSONL com NOSSO UUID via --session-id."""

    def _build2(self, sdk_session_id, our_session_id):
        return get_lojas_client().build_options(
            user_id=1, user_name='Test', perfil='administrador',
            loja_hora_id=None, sdk_session_id=sdk_session_id,
            our_session_id=our_session_id,
        )

    def test_turno1_com_our_session_id_seta_session_id(self):
        """Turno 1 (sem sdk_session_id): session_id=our_uuid, SEM resume."""
        osid = str(uuid.uuid4())
        o = self._build2(None, osid)
        assert o.session_id == osid
        assert getattr(o, 'resume', None) is None

    def test_turno2_com_our_session_id_NAO_seta_session_id(self):
        """INVARIANTE FIX S1: turno 2 usa resume e NUNCA session_id junto
        (--session-id + --resume exigiria --fork-session; fork X->X = exit 1)."""
        sid = str(uuid.uuid4())
        osid = str(uuid.uuid4())
        o = self._build2(sid, osid)
        assert o.resume == sid
        assert getattr(o, 'session_id', None) is None

    def test_turno1_our_session_id_nao_uuid_e_ignorado(self):
        """our_session_id invalido nao vira --session-id (CLI gera o proprio)."""
        o = self._build2(None, 'nao-e-uuid')
        assert getattr(o, 'session_id', None) is None
        assert getattr(o, 'resume', None) is None
