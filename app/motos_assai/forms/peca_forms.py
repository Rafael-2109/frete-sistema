from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Optional as Opt


class PecaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    codigo = StringField('Código', validators=[Opt()])
    custo_referencia = StringField('Custo referência (R$)', validators=[Opt()])
    ativo = BooleanField('Ativa', default=True)
    modelo_ids = SelectMultipleField('Modelos compatíveis', coerce=int, validators=[Opt()])
