from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import MultipleFileField


class UploadNfQpaForm(FlaskForm):
    """Aceita 1 ou N PDFs de NF Q.P.A. para importação em lote."""
    pdfs = MultipleFileField('PDFs da NF Q.P.A.', validators=[
        FileRequired(message='Selecione ao menos 1 PDF.'),
        FileAllowed(['pdf'], 'Apenas PDF.'),
    ])
