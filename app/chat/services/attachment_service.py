"""Upload de anexos para S3 + validacao."""
import os
import uuid
from typing import BinaryIO, Optional

import boto3

from app.utils.logging_config import logger
from app.utils.timezone import agora_utc_naive


MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20MB
MAX_PER_MESSAGE = 5

ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/gif', 'image/webp',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
    'application/vnd.ms-excel',  # xls
    'text/csv', 'text/plain',
}

# Project convention: S3_BUCKET_NAME (from app/utils/file_storage.py)
# Also check AWS_S3_BUCKET as fallback for compatibility
S3_BUCKET = os.environ.get('S3_BUCKET_NAME') or os.environ.get('AWS_S3_BUCKET', '')
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')


class AttachmentError(Exception):
    pass


class AttachmentService:

    def validate_upload(
        self, stream: BinaryIO, filename: str, mime_type: str, size: int,
    ) -> Optional[None]:
        """Valida tamanho e tipo. Raises AttachmentError se invalido. Retorna None em sucesso."""
        if size > MAX_SIZE_BYTES:
            raise AttachmentError(
                f'Arquivo excede tamanho maximo ({MAX_SIZE_BYTES} bytes)'
            )
        if mime_type not in ALLOWED_MIME_TYPES:
            raise AttachmentError(f'tipo de arquivo nao permitido: {mime_type}')
        return None

    def upload(
        self, stream: BinaryIO, filename: str, mime_type: str, size: int, user_id: int,
    ) -> str:
        """Upload para S3 e retorna a key gerada."""
        self.validate_upload(stream, filename, mime_type, size)
        key = (
            f'chat/attachments/{user_id}/'
            f'{agora_utc_naive():%Y/%m/%d}/'
            f'{uuid.uuid4().hex}_{filename}'
        )
        client = boto3.client('s3', region_name=S3_REGION)
        client.upload_fileobj(stream, S3_BUCKET, key, ExtraArgs={'ContentType': mime_type})
        logger.info(f'[CHAT] attachment uploaded: {key} ({size} bytes)')
        return key

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """URL presigned para download temporario (expiracao em segundos)."""
        client = boto3.client('s3', region_name=S3_REGION)
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': key},
            ExpiresIn=expires_in,
        )
