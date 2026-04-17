"""Testes da migracao de screenshots para S3."""
import io
from unittest.mock import MagicMock, patch


def test_save_screenshot_local_only_when_s3_disabled(tmp_path, monkeypatch):
    """Quando USE_S3=False, salva apenas local."""
    monkeypatch.setattr(
        'app.agente.tools.playwright_mcp_tool.SCREENSHOTS_DIR',
        str(tmp_path)
    )
    from app.agente.tools.playwright_mcp_tool import _save_screenshot

    png_bytes = b'\x89PNG\r\n\x1a\n' + b'x' * 100  # PNG header + fake data

    mock_app = MagicMock()
    mock_app.config = {'USE_S3': False}

    with patch('flask.current_app', mock_app), \
         patch('app.utils.file_storage.FileStorage'):
        result = _save_screenshot(png_bytes, prefix='test')

    assert result['filename']
    assert result['local_path']
    assert result.get('s3_path') is None
    assert result.get('s3_url') is None


def test_save_screenshot_uploads_to_s3_when_enabled(tmp_path, monkeypatch):
    """Quando USE_S3=True, sobe pra S3 em playwright-screenshots/YYYY-MM/."""
    monkeypatch.setattr(
        'app.agente.tools.playwright_mcp_tool.SCREENSHOTS_DIR',
        str(tmp_path)
    )
    from app.agente.tools.playwright_mcp_tool import _save_screenshot

    png_bytes = b'\x89PNG\r\n\x1a\n' + b'x' * 100

    mock_storage = MagicMock()
    mock_storage.save_file.return_value = 'playwright-screenshots/2026-04/test.png'
    mock_storage.get_file_url.return_value = 'https://s3.example/presigned'

    mock_app = MagicMock()
    mock_app.config = {'USE_S3': True}

    with patch('flask.current_app', mock_app), \
         patch('app.agente.tools.playwright_mcp_tool.get_file_storage',
               return_value=mock_storage):
        result = _save_screenshot(png_bytes, prefix='ssw-cotacao')

    assert result['s3_path'] == 'playwright-screenshots/2026-04/test.png'
    assert result['s3_url'] == 'https://s3.example/presigned'
    # Verifica key com YYYY-MM prefix
    call_kwargs = mock_storage.save_file.call_args
    assert 'playwright-screenshots' in call_kwargs.kwargs.get('folder', '')


def test_save_screenshot_s3_failure_graceful(tmp_path, monkeypatch):
    """S3 falha nao quebra screenshot local."""
    monkeypatch.setattr(
        'app.agente.tools.playwright_mcp_tool.SCREENSHOTS_DIR',
        str(tmp_path)
    )
    from app.agente.tools.playwright_mcp_tool import _save_screenshot

    png_bytes = b'\x89PNG\r\n\x1a\n' + b'x' * 100

    mock_storage = MagicMock()
    mock_storage.save_file.side_effect = Exception('S3 down')

    mock_app = MagicMock()
    mock_app.config = {'USE_S3': True}

    with patch('flask.current_app', mock_app), \
         patch('app.agente.tools.playwright_mcp_tool.get_file_storage',
               return_value=mock_storage):
        result = _save_screenshot(png_bytes, prefix='test')

    # Local salvou, S3 falhou silencioso
    assert result['filename']
    assert result['local_path']
    assert result.get('s3_path') is None
    assert result.get('s3_url') is None
