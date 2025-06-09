from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional

class ContatoAgendamentoForm(FlaskForm):
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    forma = SelectField('Forma de Agendamento', choices=[
        ('Portal', 'Portal'),
        ('Telefone', 'Telefone'),
        ('E-mail', 'E-mail'),
        ('WhatsApp', 'WhatsApp')
    ])
    contato = StringField('Contato', validators=[DataRequired()])
    observacao = TextAreaField('Observação', validators=[Optional()])
    submit = SubmitField('Salvar')