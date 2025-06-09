from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional

class UploadExcelForm(FlaskForm):
    arquivo = StringField('Arquivo Excel (.xlsx)', validators=[DataRequired()])
    submit = SubmitField('Importar')
