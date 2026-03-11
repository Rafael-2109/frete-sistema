from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, FileField, HiddenField, BooleanField, TimeField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed

FORMAS_CHOICES = [
    ('', '-- Selecione --'),
    ('PORTAL', 'PORTAL'),
    ('TELEFONE', 'TELEFONE'),
    ('E-MAIL', 'E-MAIL'),
    ('COMERCIAL', 'COMERCIAL'),
    ('SEM AGENDAMENTO', 'SEM AGENDAMENTO'),
    ('ODOO', 'ODOO')
]

FORMAS_PESQUISA_CHOICES = [
    ('', '-- Todas --'),
    ('PORTAL', 'PORTAL'),
    ('TELEFONE', 'TELEFONE'),
    ('E-MAIL', 'E-MAIL'),
    ('COMERCIAL', 'COMERCIAL'),
    ('SEM AGENDAMENTO', 'SEM AGENDAMENTO'),
    ('ODOO', 'ODOO')
]

class ContatoAgendamentoForm(FlaskForm):
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    forma = SelectField('Forma de Agendamento', choices=FORMAS_CHOICES, validators=[Optional()])
    contato = StringField('Contato', validators=[DataRequired()])
    observacao = TextAreaField('Observação', validators=[Optional()])
    nao_aceita_nf_pallet = BooleanField('Não aceita NF de Pallet')
    horario_recebimento_de = TimeField('Horário Recebimento De', validators=[Optional()])
    horario_recebimento_ate = TimeField('Horário Recebimento Até', validators=[Optional()])
    observacoes_recebimento = TextAreaField('Obs. Recebimento', validators=[Optional()])
    submit = SubmitField('Salvar')

class EditarContatoAgendamentoForm(FlaskForm):
    id = HiddenField('ID')
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    forma = SelectField('Forma de Agendamento', choices=FORMAS_CHOICES, validators=[Optional()])
    contato = StringField('Contato', validators=[DataRequired()])
    observacao = TextAreaField('Observação', validators=[Optional()])
    nao_aceita_nf_pallet = BooleanField('Não aceita NF de Pallet')
    horario_recebimento_de = TimeField('Horário Recebimento De', validators=[Optional()])
    horario_recebimento_ate = TimeField('Horário Recebimento Até', validators=[Optional()])
    observacoes_recebimento = TextAreaField('Obs. Recebimento', validators=[Optional()])
    submit = SubmitField('Atualizar')

class PesquisarAgendamentoForm(FlaskForm):
    cnpj = StringField('CNPJ', validators=[Optional()])
    forma = SelectField('Forma de Agendamento', choices=FORMAS_PESQUISA_CHOICES, validators=[Optional()])
    contato = StringField('Contato', validators=[Optional()])
    submit = SubmitField('Buscar')
    limpar = SubmitField('Limpar')

class ImportarAgendamentosForm(FlaskForm):
    arquivo = FileField('Arquivo Excel (.xlsx)', validators=[
        DataRequired('Selecione um arquivo para importação'),
        FileAllowed(['xlsx'], 'Apenas arquivos .xlsx são permitidos')
    ])
    submit = SubmitField('Importar Agendamentos')