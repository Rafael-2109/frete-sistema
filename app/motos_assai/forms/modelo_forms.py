import re
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, DecimalField
from wtforms.validators import DataRequired, Length, Optional, ValidationError, NumberRange


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
    peso_kg = DecimalField(
        'Peso físico (kg)', places=2,
        validators=[Optional(), NumberRange(min=0, max=999999.99)],
        description='Peso real da moto (usado em relatórios e portaria).',
    )
    peso_cubado_kg = DecimalField(
        'Peso cubado (kg)', places=2,
        validators=[Optional(), NumberRange(min=0, max=999999.99)],
        description='Peso cubado usado no CÁLCULO DO FRETE (motos vão montadas → ocupam muito espaço).',
    )
    ativo = BooleanField('Ativo', default=True)


class TestarRegexForm(FlaskForm):
    regex = StringField('Regex', validators=[DataRequired(), validar_regex_python])
    chassi = StringField('Chassi de teste', validators=[DataRequired()])
