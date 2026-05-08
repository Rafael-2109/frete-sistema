from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed


class UploadReciboForm(FlaskForm):
    arquivo = FileField('Recibo Motochefe (PDF ou XLSX)', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'xlsx', 'xls'], 'Apenas PDF ou Excel.'),
    ])
