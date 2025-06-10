from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional

class ContatoAgendamentoForm(FlaskForm):
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    forma = SelectField('Forma de Agendamento', choices=[
        ('PORTAL', 'PORTAL'),
        ('TELEFONE', 'TELEFONE'),
        ('E-MAIL', 'E-MAIL'),
        ('COMERCIAL', 'COMERCIAL'),
        ('SEM AGENDAMENTO', 'SEM AGENDAMENTO')
    ])
    contato = StringField('Contato', validators=[DataRequired()])
    observacao = TextAreaField('Observação', validators=[Optional()])
    submit = SubmitField('Salvar')