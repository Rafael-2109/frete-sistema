from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import Optional, Length, Regexp


class NovaCompraForm(FlaskForm):
    motochefe_cnpj = StringField('CNPJ Motochefe', validators=[
        Optional(),
        Length(max=18),
        Regexp(r'^[\d\.\-/]+$', message='Apenas dígitos e pontuação.'),
    ])
