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
def test_upload_returns_s3_key(mock_boto):
    mock_client = MagicMock()
    mock_boto.client.return_value = mock_client
    svc = AttachmentService()
    key = svc.upload(BytesIO(b'data'), 'doc.pdf', 'application/pdf', 4, user_id=1)
    assert key.startswith('chat/attachments/')
    assert key.endswith('.pdf')
    mock_client.upload_fileobj.assert_called_once()
