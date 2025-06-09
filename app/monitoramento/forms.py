from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FloatField, HiddenField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileField, FileAllowed

class LogEntregaForm(FlaskForm):
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[('Info', 'Informação'), ('Contato', 'Contato'), ('Ação', 'Ação')])
    lembrete_para = DateField('Lembrete para', validators=[Optional()])
    submit_log = SubmitField('Salvar Log')

class EventoEntregaForm(FlaskForm):
    data_hora_chegada = DateField('Data Chegada', validators=[Optional()])
    hora_chegada = TimeField('Hora Chegada', validators=[Optional()])
    data_hora_saida = DateField('Data Saída', validators=[Optional()])
    hora_saida = TimeField('Hora Saída', validators=[Optional()])
    tipo_evento = SelectField('Tipo de Evento', choices=[('Entrega', 'Entrega'), ('Reentrega', 'Reentrega'), ('Tentativa', 'Tentativa'), ('NF no CD','NF no CD')])
    motorista = StringField('Motorista', validators=[Optional()])
    observacao = TextAreaField('Observação', validators=[Optional()])
    submit_evento = SubmitField('Registrar Evento')

class CustoExtraForm(FlaskForm):
    tipo = SelectField('Tipo', choices=[('TDE', 'TDE'), ('Diária', 'Diária'), ('Reentrega', 'Reentrega')])
    valor = FloatField('Valor', validators=[DataRequired()])
    motivo = TextAreaField('Motivo', validators=[DataRequired(message="O motivo é obrigatório.")])
    submit_custo = SubmitField('Registrar Custo')

class AgendamentoEntregaForm(FlaskForm):
    data_agendada = DateField('Data Agendada', validators=[DataRequired()])
    hora_agendada = TimeField('Hora Agendada', validators=[Optional()])
    forma_agendamento = SelectField('Forma', choices=[('Portal', 'Portal'), ('Telefone', 'Telefone'), ('E-mail', 'E-mail'), ('WhatsApp', 'WhatsApp')])
    contato_agendamento = StringField('Contato', validators=[Optional()])
    protocolo_agendamento = StringField('Protocolo', validators=[Optional()])
    motivo = TextAreaField('Motivo', validators=[Optional()])
    observacao = TextAreaField('Observação', validators=[Optional()])  # ← NOVO CAMPO
    submit_agendamento = SubmitField('Registrar Agendamento')

class FormComentarioNF(FlaskForm):
    texto = TextAreaField('Comentário', validators=[DataRequired()])
    arquivo = FileField('Arquivo', validators=[Optional(), FileAllowed(['jpg', 'png', 'pdf', 'xlsx', 'docx'])])
    resposta_a_id = HiddenField()
    submit = SubmitField('Enviar')
