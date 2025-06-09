from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired

class UploadRelatorioForm(FlaskForm):
    arquivo = FileField('Arquivo Excel (.xlsx)', validators=[DataRequired()])
    submit = SubmitField('Importar')
