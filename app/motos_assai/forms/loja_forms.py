from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Regexp


UFs = [
    ('AC','AC'),('AL','AL'),('AP','AP'),('AM','AM'),('BA','BA'),('CE','CE'),
    ('DF','DF'),('ES','ES'),('GO','GO'),('MA','MA'),('MT','MT'),('MS','MS'),
    ('MG','MG'),('PA','PA'),('PB','PB'),('PR','PR'),('PE','PE'),('PI','PI'),
    ('RJ','RJ'),('RN','RN'),('RS','RS'),('RO','RO'),('RR','RR'),('SC','SC'),
    ('SP','SP'),('SE','SE'),('TO','TO'),
]


class LojaForm(FlaskForm):
    numero = StringField('Número (LJ)', validators=[DataRequired(), Length(max=10)])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=120)])
    razao_social = StringField('Razão Social', validators=[DataRequired(), Length(max=200)])
    cnpj = StringField('CNPJ', validators=[
        DataRequired(),
        Regexp(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
               message='Use formato 00.000.000/0000-00'),
    ])
    ie = StringField('IE', validators=[Optional(), Length(max=20)])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=80)])
    cep = StringField('CEP', validators=[Optional(), Length(max=10)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=80)])
    uf = SelectField('UF', choices=UFs, validators=[DataRequired()])
    regional = StringField('Regional', validators=[Optional(), Length(max=80)])
    ativo = BooleanField('Ativo', default=True)
