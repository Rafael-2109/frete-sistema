import re
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


def validar_regex_python(form, field):
    if not field.data:
        return
    try:
        re.compile(field.data)
    except re.error as e:
        raise ValidationError(f'Regex inválido: {e}')


class ModeloForm(FlaskForm):
    codigo = StringField('Código canônico', validators=[
        DataRequired(),
        Length(max=30),
    ])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    descricao_qpa = StringField('Descrição Q.P.A.', validators=[Optional(), Length(max=200)])
    codigo_qpa = StringField('Código no sistema Q.P.A.', validators=[Optional(), Length(max=20)])
    regex_chassi = StringField('Regex de validação de chassi (Python re)', validators=[
        Optional(), Length(max=120), validar_regex_python,
    ])
    ativo = BooleanField('Ativo', default=True)


class TestarRegexForm(FlaskForm):
    regex = StringField('Regex', validators=[DataRequired(), validar_regex_python])
    chassi = StringField('Chassi de teste', validators=[DataRequired()])
