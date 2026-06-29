"""Forms do modulo Pessoal."""
from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField, FileAllowed
from wtforms import IntegerField
from wtforms.validators import Optional, NumberRange


class ImportarCSVForm(FlaskForm):
    """Form para upload de extratos (multi-file, auto-detect): CSV Bradesco e OFX Nubank."""
    arquivos = MultipleFileField('Arquivos (CSV ou OFX)', validators=[
        FileAllowed(['csv', 'ofx'], message='Apenas arquivos CSV ou OFX sao permitidos.'),
    ])
    ano_referencia = IntegerField('Ano de referencia', validators=[
        Optional(),
        NumberRange(min=2020, max=2099, message='Ano deve estar entre 2020 e 2099.'),
    ])
