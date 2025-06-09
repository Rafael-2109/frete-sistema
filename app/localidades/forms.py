from flask_wtf import FlaskForm

from wtforms.validators import DataRequired

from wtforms import StringField
from wtforms import SubmitField
from wtforms import BooleanField
from wtforms import SelectField

from app.utils.ufs import UF_LIST



class CidadeForm(FlaskForm):
    nome = StringField('Nome da Cidade', validators=[DataRequired()])
    uf = SelectField('UF', choices=UF_LIST, validators=[DataRequired()])
    codigo_ibge = StringField('Código IBGE', validators=[DataRequired()])
    icms = StringField('ICMS (%)', validators=[DataRequired()])
    substitui_icms_por_iss = BooleanField('Substitui ICMS por ISS')
    submit = SubmitField('Salvar')
    