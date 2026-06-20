"""Testes do service de persistencia S3 + recuperacao de uploads — IMP-2026-06-19-007."""
import os
from datetime import timedelta

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
        '/tmp/nao_usado_s3_off.pdf', user_id=78, session_id='s', file_id='f',
        original_name='a.pdf', safe_name='f_a.pdf', file_type='pdf', size_bytes=1)
    assert result is None


def test_persistir_upload_s3_sobe_do_arquivo_local(db, monkeypatch, tmp_path):
    """Finding 1: persiste lendo do ARQUIVO LOCAL ja salvo (nao do stream exausto)."""
    from app.agente.services import upload_recovery_service as svc
    p = tmp_path / "ff_doc.pdf"
    p.write_bytes(b'conteudo-real')
    captured = {}

    class FakeStorage:
        use_s3 = True

        def save_file(self, fileobj, folder, filename=None):
            captured['data'] = fileobj.read()
            captured['folder'] = folder
            captured['filename'] = filename
            return f"{folder}/{filename}"

    monkeypatch.setattr(svc, 'get_file_storage', lambda: FakeStorage())
    up = svc.persistir_upload_s3(
        str(p), user_id=78, session_id='s', file_id='ff',
        original_name='doc.pdf', safe_name='ff_doc.pdf', file_type='pdf', size_bytes=13)
    assert up is not None
    assert captured['data'] == b'conteudo-real'  # leu do arquivo local, nao do stream
    assert captured['folder'] == 'agente-uploads/78'
    assert up.s3_key == 'agente-uploads/78/ff_doc.pdf'


def test_recuperar_upload_inexistente_retorna_none(db):
    """Sem manifesto ativo para (user, file_id) -> None."""
    from app.agente.services.upload_recovery_service import recuperar_upload
    assert recuperar_upload(78, 'nao-existe', target_session_id='s9') is None


def test_recuperar_upload_guarda_s3_off(db, monkeypatch):
    """Finding 6: com USE_S3 off, recuperar e no-op mesmo se houver row antiga."""
    from app.agente.models import AgenteUpload
    from app.agente.services import upload_recovery_service as svc
    now = agora_brasil_naive()
    db.session.add(AgenteUpload(
        user_id=78, session_id='s', file_id='zz', original_name='a.pdf',
        safe_name='zz_a.pdf', s3_key='agente-uploads/78/zz_a.pdf', file_type='pdf',
        size_bytes=1, criado_em=now, ativo=True))
    db.session.flush()

    class FakeStorage:
        use_s3 = False

        def download_file(self, key):
            return b'NAO DEVERIA BAIXAR'

    monkeypatch.setattr(svc, 'get_file_storage', lambda: FakeStorage())
    assert svc.recuperar_upload(78, 'zz', target_session_id='s9') is None


def test_recuperar_upload_neutraliza_safe_name_malicioso(db, monkeypatch):
    """Finding 3: safe_name com ../ nao escapa a pasta da sessao (defense-in-depth)."""
    from app.agente.models import AgenteUpload
    from app.agente.services import upload_recovery_service as svc
    now = agora_brasil_naive()
    db.session.add(AgenteUpload(
        user_id=78, session_id='s', file_id='ev', original_name='x',
        safe_name='../../../tmp/evil_escape_test.txt', s3_key='k', file_type='txt',
        size_bytes=1, criado_em=now, ativo=True))
    db.session.flush()

    class FakeStorage:
        use_s3 = True

        def download_file(self, key):
            return b'x'

    monkeypatch.setattr(svc, 'get_file_storage', lambda: FakeStorage())
    path = svc.recuperar_upload(78, 'ev', target_session_id='sess-trav')
    try:
        assert path is not None
        assert '..' not in path
        assert os.path.basename(os.path.dirname(path)) == 'sess-trav'
    finally:
        if path and os.path.exists(path):
            os.remove(path)
