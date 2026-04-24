import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from app.chat.services.attachment_service import (
    AttachmentService, AttachmentError, MAX_SIZE_BYTES,
)


def test_rejects_oversized_file():
    svc = AttachmentService()
    big_stream = BytesIO(b'x' * 10)
    with pytest.raises(AttachmentError, match='tamanho'):
        svc.validate_upload(big_stream, 'test.pdf', 'application/pdf', MAX_SIZE_BYTES + 1)


def test_rejects_disallowed_mime():
    svc = AttachmentService()
    with pytest.raises(AttachmentError, match='tipo'):
        svc.validate_upload(BytesIO(b'x'), 'test.exe', 'application/x-msdownload', 100)


def test_accepts_valid_pdf():
    svc = AttachmentService()
    # validate_upload returns None on success
    assert svc.validate_upload(BytesIO(b'%PDF'), 'test.pdf', 'application/pdf', 100) is None


@patch('app.chat.services.attachment_service.boto3')
@patch('app.chat.services.attachment_service.S3_BUCKET', 'test-bucket')
def test_upload_returns_s3_key(mock_boto):
    mock_client = MagicMock()
    mock_boto.client.return_value = mock_client
    svc = AttachmentService()
    key = svc.upload(BytesIO(b'data'), 'doc.pdf', 'application/pdf', 4, user_id=1)
    assert key.startswith('chat/attachments/')
    assert key.endswith('.pdf')
    mock_client.upload_fileobj.assert_called_once()


@patch('app.chat.services.attachment_service.boto3')
@patch('app.chat.services.attachment_service.S3_BUCKET', 'test-bucket')
def test_upload_sanitizes_path_traversal_filename(mock_boto):
    """Filename com '../' nao deve escapar do prefixo chat/attachments/{user_id}/."""
    mock_boto.client.return_value = MagicMock()
    svc = AttachmentService()
    key = svc.upload(
        BytesIO(b'data'),
        filename='../../../etc/passwd',
        mime_type='text/plain', size=4, user_id=1,
    )
    assert '..' not in key
    assert key.startswith('chat/attachments/1/')


@patch('app.chat.services.attachment_service.S3_BUCKET', '')
def test_upload_raises_if_bucket_not_configured():
    svc = AttachmentService()
    with pytest.raises(AttachmentError, match='S3_BUCKET'):
        svc.upload(BytesIO(b'data'), 'doc.pdf', 'application/pdf', 4, user_id=1)
