"""
Naming determinístico do JSONL (turno 1) no perfil 'lojas' via o MOTOR.

Migrado de tests/agente_lojas/test_resume_build_options.py (fork aposentado na
FASE B do cutover). No motor, o `_build_options` pre-nomeia o JSONL com NOSSO UUID
(`session_id=our_session_id`) quando ele e um UUID valido — elimina a captura
assincrona fragil do sdk_session_id (anti-amnesia, FIX S1). O RESUME do turno 2
(`resume=sdk_session_id` via `_with_resume`) e mecanica GENERICA do motor, identica
para 'web' e 'lojas', exercitada em PROD pelo agente web.
"""
import uuid

from app.agente.sdk.client import get_client


def test_lojas_turno1_our_session_id_uuid_pre_nomeia_o_jsonl(app):
    our = str(uuid.uuid4())
    with app.app_context():
        opts = get_client('lojas')._build_options(our_session_id=our)
    assert getattr(opts, 'session_id', None) == our


def test_lojas_our_session_id_nao_uuid_e_ignorado(app):
    with app.app_context():
        opts = get_client('lojas')._build_options(our_session_id='nao-e-uuid-valido')
    assert getattr(opts, 'session_id', None) is None
