from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, Regexp


UFs = [(s, s) for s in ['SP','RJ','MG','PR','SC','RS','BA','GO','DF','MT','MS','ES','CE','PE','PB','RN','SE','AL','MA','PI','PA','AP','AM','RR','RO','AC','TO']]


class CdForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    cnpj = StringField('CNPJ', validators=[Optional(),
        Regexp(r'^\d{14}$', message='Use 14 dígitos sem formatação')])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=80)])
    cep = StringField('CEP', validators=[Optional(), Length(max=10)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=80)])
    uf = SelectField('UF', choices=[('', '-')] + UFs, validators=[Optional()])
    ativo = BooleanField('Ativo', default=True)
