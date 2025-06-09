from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired

class ImportarExcelForm(FlaskForm):
    arquivo_excel = FileField("Arquivo Excel", validators=[DataRequired()])
    submit = SubmitField("Importar")
