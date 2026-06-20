"""Testes do service de persistencia S3 + recuperacao de uploads — IMP-2026-06-19-007."""
from datetime import timedelta
from io import BytesIO

from app.utils.timezone import agora_brasil_naive


def test_listar_uploads_usuario_filtra_por_recencia(db):
    from app.agente.models import AgenteUpload
    from app.agente.services.upload_recovery_service import listar_uploads_usuario
    now = agora_brasil_naive()
    db.session.add(AgenteUpload(
        user_id=78, session_id='s1', file_id='a', original_name='novo.pdf',
        safe_name='a_novo.pdf', s3_key='k1', file_type='pdf', size_bytes=1,
        criado_em=now, expira_em=now + timedelta(days=90), ativo=True))
    db.session.add(AgenteUpload(
        user_id=78, session_id='s0', file_id='b', original_name='velho.pdf',
        safe_name='b_velho.pdf', s3_key='k2', file_type='pdf', size_bytes=1,
        criado_em=now - timedelta(days=30), ativo=True))
    db.session.flush()
    achados = listar_uploads_usuario(78, dias=7)
    nomes = {u['original_name'] for u in achados}
    assert 'novo.pdf' in nomes and 'velho.pdf' not in nomes


def test_listar_uploads_usuario_filtra_por_user(db):
    """Escopo: usuario A nao ve uploads do usuario B."""
    from app.agente.models import AgenteUpload
    from app.agente.services.upload_recovery_service import listar_uploads_usuario
    now = agora_brasil_naive()
    db.session.add(AgenteUpload(
        user_id=78, session_id='s1', file_id='a', original_name='do_78.pdf',
        safe_name='a_do_78.pdf', s3_key='k1', file_type='pdf', size_bytes=1,
        criado_em=now, ativo=True))
    db.session.add(AgenteUpload(
        user_id=99, session_id='s2', file_id='c', original_name='do_99.pdf',
        safe_name='c_do_99.pdf', s3_key='k3', file_type='pdf', size_bytes=1,
        criado_em=now, ativo=True))
    db.session.flush()
    achados = listar_uploads_usuario(78, dias=7)
    nomes = {u['original_name'] for u in achados}
    assert nomes == {'do_78.pdf'}


def test_persistir_upload_s3_retorna_none_quando_s3_off(db, monkeypatch):
    """Degradacao segura: com USE_S3 off, persistir_upload_s3 e no-op (None)."""
    from app.agente.services import upload_recovery_service as svc

    class FakeStorage:
        use_s3 = False

    monkeypatch.setattr(svc, 'get_file_storage', lambda: FakeStorage())
    result = svc.persistir_upload_s3(
        BytesIO(b'x'), user_id=78, session_id='s', file_id='f',
        original_name='a.pdf', safe_name='f_a.pdf', file_type='pdf', size_bytes=1)
    assert result is None
