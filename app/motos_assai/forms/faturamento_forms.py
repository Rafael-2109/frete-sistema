from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed


class UploadNfQpaForm(FlaskForm):
    pdf = FileField('PDF da NF Q.P.A.', validators=[
        FileRequired(), FileAllowed(['pdf'], 'Apenas PDF.'),
    ])
