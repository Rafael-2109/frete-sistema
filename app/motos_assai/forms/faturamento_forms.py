from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import MultipleFileField
from wtforms.validators import ValidationError


# Cap de PDFs por envio (IMP-2026-06-23-002): o upload e SINCRONO no request
# (pdfplumber + ate 3 LLM/arquivo + S3), sem worker RQ. Lotes grandes faziam a
# memoria estourar (722->882MB) e o web reiniciava no meio, sumindo arquivos.
# Limita por request; lotes maiores devem ser divididos.
MAX_PDFS_POR_UPLOAD = 25


def _limitar_qtd_pdfs(form, field):
    arquivos = [f for f in (field.data or []) if f and getattr(f, 'filename', '')]
    if len(arquivos) > MAX_PDFS_POR_UPLOAD:
        raise ValidationError(
            f'Maximo de {MAX_PDFS_POR_UPLOAD} PDFs por envio (recebidos '
            f'{len(arquivos)}). Divida em lotes menores para evitar '
            f'timeout/memoria.'
        )


class UploadNfQpaForm(FlaskForm):
    """Aceita 1 ou N PDFs de NF Q.P.A. para importação em lote."""
    pdfs = MultipleFileField('PDFs da NF Q.P.A.', validators=[
        FileRequired(message='Selecione ao menos 1 PDF.'),
        FileAllowed(['pdf'], 'Apenas PDF.'),
        _limitar_qtd_pdfs,
    ])
