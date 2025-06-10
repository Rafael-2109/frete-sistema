from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, FileField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed

class ContatoAgendamentoForm(FlaskForm):
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    forma = SelectField('Forma de Agendamento', choices=[
        ('', '-- Selecione --'),
        ('PORTAL', 'PORTAL'),
        ('TELEFONE', 'TELEFONE'),
        ('E-MAIL', 'E-MAIL'),
        ('COMERCIAL', 'COMERCIAL'),
        ('SEM AGENDAMENTO', 'SEM AGENDAMENTO')
    ], validators=[Optional()])
    contato = StringField('Contato', validators=[DataRequired()])
    observacao = TextAreaField('Observação', validators=[Optional()])
    submit = SubmitField('Salvar')

class ImportarAgendamentosForm(FlaskForm):
    arquivo = FileField('Arquivo Excel (.xlsx)', validators=[
        DataRequired('Selecione um arquivo para importação'),
        FileAllowed(['xlsx'], 'Apenas arquivos .xlsx são permitidos')
    ])
    submit = SubmitField('Importar Agendamentos')