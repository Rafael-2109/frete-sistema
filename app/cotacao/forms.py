# app/cotacao/forms.py
from flask_wtf import FlaskForm
from wtforms import HiddenField, SubmitField

class CotarFreteForm(FlaskForm):
    """
    Formulário minimalista apenas para manter CSRF.
    """
    dummy = HiddenField()  # só de exemplo
    submit_fechar = SubmitField("Fechar Frete")
