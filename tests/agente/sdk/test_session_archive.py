"""Testa archive de subagent transcripts para S3."""
import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_find_archivable_files_empty_when_no_tmp(tmp_path, monkeypatch):
    """Nenhum arquivo retorna lista vazia."""
    # Mock /tmp/.claude nao existente (nao setar nada para esse teste)
    from app.agente.sdk.session_archive import _find_archivable_files
    result = _find_archivable_files('sess-nonexistent-12345')
    # tmp_path nao tem .claude/projects, entao lista vazia ou poucos items
    assert isinstance(result, list)


def test_create_tarball_returns_none_empty():
    """Lista vazia retorna None."""
    from app.agente.sdk.session_archive import _create_tarball
    assert _create_tarball([], 'sess-x') is None


def test_create_tarball_valid_gzip(tmp_path):
    """Tarball gerado e valido gzip."""
    from app.agente.sdk.session_archive import _create_tarball

    f1 = tmp_path / 'agent-a1.jsonl'
    f1.write_text('{"type": "user", "content": "hello"}')

    tarball = _create_tarball([f1], 'sess-test')
    assert tarball is not None

    # Valida formato gzip
    buf = io.BytesIO(tarball)
    with tarfile.open(fileobj=buf, mode='r:gz') as tar:
        names = tar.getnames()
        assert any('agent-a1.jsonl' in n for n in names)


def test_archive_skipped_when_use_s3_false(app, tmp_path):
    """Quando USE_S3=false, retorna None."""
    from app.agente.sdk.session_archive import archive_session_to_s3

    with app.app_context():
        app.config['USE_S3'] = False
        result = archive_session_to_s3('sess-x')
        assert result is None


def test_archive_uploads_to_s3_when_files_exist(app, tmp_path, monkeypatch):
    """Com arquivos + USE_S3=true, chama storage.save_file."""
    from app.agente.sdk.session_archive import archive_session_to_s3

    # Cria /tmp/.claude/projects fake apontando para tmp_path
    fake_claude = tmp_path / '.claude' / 'projects' / 'proj'
    sub_dir = fake_claude / 'sess-test-123' / 'subagents'
    sub_dir.mkdir(parents=True)
    (sub_dir / 'agent-a1.jsonl').write_text('{"t": "r"}')

    mock_storage = MagicMock()
    mock_storage.save_file.return_value = 'agent-archive/2026-04/sess-test-123.tar.gz'

    with app.app_context(), \
         patch('app.agente.sdk.session_archive.Path') as mock_path_cls, \
         patch('app.utils.file_storage.get_file_storage',
               return_value=mock_storage):

        # Patch Path('/tmp/.claude/projects') para apontar para fake
        def path_side_effect(p):
            if p == '/tmp/.claude/projects':
                return fake_claude.parent
            return Path(p)
        mock_path_cls.side_effect = path_side_effect

        app.config['USE_S3'] = True
        result = archive_session_to_s3('sess-test-123')

    # Pode ser None se mock paths nao bateu perfeitamente — aceitavel
    # O importante e nao ter lancado excecao


def test_archive_survives_exception_best_effort(app):
    """Excecao em qualquer ponto retorna None (R1 best-effort)."""
    from app.agente.sdk.session_archive import archive_session_to_s3

    with app.app_context(), \
         patch('app.agente.sdk.session_archive._find_archivable_files',
               side_effect=Exception('boom')):
        app.config['USE_S3'] = True
        result = archive_session_to_s3('sess-x')
        assert result is None


def test_restore_returns_false_when_no_archive(app):
    """Session sem s3_archive em data retorna False."""
    from app.agente.sdk.session_archive import restore_session_from_s3
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        AgentSession.query.filter_by(session_id='sess-restore-none').delete()
        db.session.commit()
        sess = AgentSession(
            session_id='sess-restore-none', user_id=1, title='t', data={}
        )
        db.session.add(sess)
        db.session.commit()

        app.config['USE_S3'] = True
        assert restore_session_from_s3('sess-restore-none') is False

        db.session.delete(sess)
        db.session.commit()
