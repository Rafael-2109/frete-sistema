from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FloatField, HiddenField, DateField, TimeField, SubmitField, BooleanField
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

class ExportarMonitoramentoForm(FlaskForm):
    # Filtros de período
    data_faturamento_inicio = DateField('Data Faturamento Início', validators=[Optional()])
    data_faturamento_fim = DateField('Data Faturamento Fim', validators=[Optional()])
    data_embarque_inicio = DateField('Data Embarque Início', validators=[Optional()])
    data_embarque_fim = DateField('Data Embarque Fim', validators=[Optional()])
    
    # Filtros de dados
    cliente = StringField('Cliente', validators=[Optional()])
    cnpj = StringField('CNPJ', validators=[Optional()])
    uf = StringField('UF', validators=[Optional()])
    municipio = StringField('Município', validators=[Optional()])
    transportadora = StringField('Transportadora', validators=[Optional()])
    vendedor = StringField('Vendedor', validators=[Optional()])
    numero_nf = StringField('Número NF', validators=[Optional()])
    
    # Filtros de status
    entregue = SelectField('Status Entrega', choices=[
        ('', 'Todos'),
        ('true', 'Apenas Entregues'),
        ('false', 'Apenas Não Entregues')
    ], validators=[Optional()])
    
    pendencia_financeira = SelectField('Pendência Financeira', choices=[
        ('', 'Todos'),
        ('true', 'Apenas com Pendência'),
        ('false', 'Apenas sem Pendência')
    ], validators=[Optional()])
    
    nf_cd = SelectField('NF no CD', choices=[
        ('', 'Todos'),
        ('true', 'Apenas NF no CD'),
        ('false', 'Apenas NF não no CD')
    ], validators=[Optional()])
    
    status_finalizacao = SelectField('Status Finalização', choices=[
        ('', 'Todos'),
        ('nao_finalizado', 'Não Finalizados'),
        ('Entregue', 'Entregue'),
        ('Cancelada', 'Cancelada'),
        ('Devolvida', 'Devolvida'),
        ('Troca de NF', 'Troca de NF')
    ], validators=[Optional()])
    
    # Filtros predefinidos
    mes_atual = BooleanField('Mês Atual (Faturamento)')
    ultimo_mes = BooleanField('Último Mês (Faturamento)')
    pendentes = BooleanField('Apenas Pendentes (Não Finalizados)')
    
    # Opções de exportação
    nome_arquivo = StringField('Nome do Arquivo', default='monitoramento_export.xlsx', validators=[DataRequired()])
    
    submit = SubmitField('Exportar para Excel')
