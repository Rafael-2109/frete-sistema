"""Forms do modulo Pessoal."""
from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField, FileAllowed
from wtforms import IntegerField
from wtforms.validators import Optional, NumberRange


class ImportarCSVForm(FlaskForm):
    """Form para upload de CSVs Bradesco (multi-file, auto-detect)."""
    arquivos = MultipleFileField('Arquivos CSV', validators=[
        FileAllowed(['csv'], message='Apenas arquivos CSV sao permitidos.'),
    ])
    ano_referencia = IntegerField('Ano de referencia', validators=[
        Optional(),
        NumberRange(min=2020, max=2099, message='Ano deve estar entre 2020 e 2099.'),
    ])
