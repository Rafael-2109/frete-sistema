from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import MultipleFileField


class UploadCceForm(FlaskForm):
    """Aceita 1 ou N PDFs de Carta de Correcao Eletronica para upload avulso."""
    pdfs = MultipleFileField('PDFs da CCe', validators=[
        FileRequired(message='Selecione ao menos 1 PDF.'),
        FileAllowed(['pdf'], 'Apenas PDF.'),
    ])
