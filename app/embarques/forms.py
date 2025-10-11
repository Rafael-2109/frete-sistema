from flask_wtf import FlaskForm

from wtforms import HiddenField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import SelectField
from wtforms import FieldList
from wtforms import FormField
from wtforms import BooleanField
from wtforms import IntegerField
from wtforms import TextAreaField

from datetime import datetime

from wtforms.validators import DataRequired
from wtforms.validators import Optional
from wtforms.validators import ValidationError
from wtforms.validators import Regexp


def coerce_int_or_none(value):
    """Converte para int ou retorna None se vazio"""
    if value == '' or value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

class EmbarqueItemForm(FlaskForm):
    class Meta:
        csrf = False  # Desliga CSRF só neste subform
    
    # ✅ APENAS o ID para identificar item existente
    id = HiddenField('id')  
    
    # ✅ CAMPOS READONLY - Dados da cotação não editáveis
    cliente = StringField('Cliente', validators=[Optional()], render_kw={'readonly': True, 'class': 'form-control'})
    pedido = StringField('Pedido', validators=[Optional()], render_kw={'readonly': True, 'class': 'form-control'})
    uf_destino = StringField('UF', validators=[Optional()], render_kw={'readonly': True, 'class': 'form-control'})
    cidade_destino = StringField('Cidade', validators=[Optional()], render_kw={'readonly': True, 'class': 'form-control'})
    
    # ✅ CAMPOS EDITÁVEIS pelo usuário
    protocolo_agendamento = StringField('Protocolo de Agendamento', validators=[Optional()])
    data_agenda = StringField('Data do Embarque', validators=[Optional()])
    agendamento_confirmado = BooleanField('Agendamento Confirmado', validators=[Optional()])  # ✅ ADICIONADO
    nota_fiscal = StringField('Nota Fiscal', validators=[Optional()])
    volumes = StringField('Volumes', validators=[Optional()])

    # ✅ REMOVIDOS: Todos os campos ocultos desnecessários
    # cnpj_cliente, separacao_lote_id, peso, valor, erro_validacao
    # modalidade, tabela_*, icms_destino, cotacao_id
    # Esses dados ficam preservados automaticamente no banco!
    
    submit = SubmitField('Adicionar Item')

    def validate_data_agenda(self, field):
        if field.data:
            try:
                datetime.strptime(field.data, '%d/%m/%Y')
            except ValueError:
                raise ValidationError('Use o formato dd/mm/aaaa')

class EmbarqueForm(FlaskForm):
    # ✅ CAMPOS EDITÁVEIS pelo usuário
    data_prevista_embarque = StringField('Data Prevista de Embarque', validators=[Optional()], render_kw={'placeholder': 'DD/MM/AAAA', 'class': 'form-control'})
    
    # ✅ CAMPOS READONLY - Dados da cotação não editáveis
    data_embarque = StringField('Data do Embarque', validators=[Optional()], render_kw={'readonly': True, 'class': 'form-control'})
    transportadora = StringField('Transportadora', validators=[Optional()], render_kw={'readonly': True, 'class': 'form-control'})
    
    # ✅ CAMPOS EDITÁVEIS pelo usuário
    observacoes = StringField('Observações')
    itens = FieldList(FormField(EmbarqueItemForm), min_entries=1)
    placa_veiculo = StringField(
        'Placa do Veículo',
        validators=[
            Optional(),
            Regexp(
                r'^[A-Z]{3}-?\d{4}$|^[A-Z]{3}-?\d{1}[A-Z]{1}\d{2}$',
                message='Placa deve estar no formato ABC-1234 (antiga) ou ABC-1D23 (Mercosul)'
            )
        ],
        render_kw={'placeholder': 'ABC-1234 ou ABC-1D23', 'style': 'text-transform: uppercase;'}
    )
    paletizado = BooleanField('Paletizado')
    laudo_anexado = BooleanField('Laudo Anexado')
    embalagem_aprovada = BooleanField('Embalagem Aprovada')
    transporte_aprovado = BooleanField('Transporte Aprovado')
    horario_carregamento = StringField('Horário de Carregamento')
    responsavel_carregamento = StringField('Responsável pelo Carregamento')
    numero = IntegerField('Número', render_kw={'readonly': True})
    
    # ✅ REMOVIDOS: Todos os campos ocultos desnecessários
    # cotacao_id, modalidade, tipo_carga, valor_total, pallet_total, peso_total
    # tabela_*, icms_destino, transportadora_optante
    # Esses dados ficam preservados automaticamente no banco!

    def validate_data_embarque(self, field):
        if field.data:
            try:
                datetime.strptime(field.data, '%d/%m/%Y')
            except ValueError:
                raise ValidationError('Use o formato dd/mm/aaaa')

    def validate_data_prevista_embarque(self, field):
        if field.data:
            try:
                datetime.strptime(field.data, '%d/%m/%Y')
            except ValueError:
                raise ValidationError('Use o formato dd/mm/aaaa')

    # Motorista
    nome_motorista = StringField('Nome do Motorista')
    cpf_motorista = StringField('CPF')
    qtd_pallets = StringField('Qtd. Pallets PBR')

    submit = SubmitField('Salvar Embarque')

# Formulário antigo removido - substituído por FiltrosEmbarqueExpandidoForm

class CancelamentoEmbarqueForm(FlaskForm):
    """
    Formulário para cancelamento de embarque
    """
    motivo_cancelamento = TextAreaField(
        'Motivo do Cancelamento',
        validators=[DataRequired(message='O motivo do cancelamento é obrigatório')],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Descreva o motivo do cancelamento...'
        }
    )
    submit = SubmitField('Confirmar Cancelamento', render_kw={'class': 'btn btn-danger'})

class FiltrosEmbarqueExpandidoForm(FlaskForm):
    """
    Formulário expandido para filtros na listagem de embarques
    """
    data_inicio = StringField(
        'Data Início',
        validators=[Optional()],
        render_kw={'placeholder': 'DD/MM/AAAA', 'class': 'form-control'}
    )
    
    data_fim = StringField(
        'Data Fim', 
        validators=[Optional()],
        render_kw={'placeholder': 'DD/MM/AAAA', 'class': 'form-control'}
    )
    
    data_prevista_inicio = StringField(
        'Data Prevista Início',
        validators=[Optional()],
        render_kw={'placeholder': 'DD/MM/AAAA', 'class': 'form-control'}
    )
    
    data_prevista_fim = StringField(
        'Data Prevista Fim', 
        validators=[Optional()],
        render_kw={'placeholder': 'DD/MM/AAAA', 'class': 'form-control'}
    )
    
    nota_fiscal = StringField(
        'Nota Fiscal',
        validators=[Optional()],
        render_kw={'placeholder': 'Número da NF', 'class': 'form-control'}
    )
    
    pedido = StringField(
        'Pedido',
        validators=[Optional()],
        render_kw={'placeholder': 'Número do pedido', 'class': 'form-control'}
    )
    
    transportadora_id = SelectField(
        'Transportadora',
        coerce=coerce_int_or_none,
        validators=[Optional()],
        choices=[],  # Será populado dinamicamente
        render_kw={'class': 'form-control'}
    )
    
    status = SelectField(
        'Status do Embarque',
        choices=[
            ('', 'Todos os status'),
            ('ativo', 'Ativo'),
            ('cancelado', 'Cancelado')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    status_portaria = SelectField(
        'Status da Portaria',
        choices=[
            ('', 'Todos os status'),
            ('Sem Registro', 'Sem Registro'),
            ('PENDENTE', 'Pendente'),
            ('AGUARDANDO', 'Aguardando'),
            ('DENTRO', 'Carregando'),
            ('SAIU', 'Saiu para entrega')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    status_nfs = SelectField(
        'Status das NFs',
        choices=[
            ('', 'Todos os status'),
            ('NFs pendentes', 'NFs Pendentes'),
            ('Pendente Import.', 'Pendente Importação'),
            ('NFs Lançadas', 'NFs Lançadas')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    status_fretes = SelectField(
        'Status dos Fretes',
        choices=[
            ('', 'Todos os status'),
            ('Pendentes', 'Pendentes'),
            ('Emitido', 'Emitido'),
            ('Lançado', 'Lançado')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    buscar_texto = StringField(
        'Busca Geral',
        validators=[Optional()],
        render_kw={'placeholder': 'Buscar por qualquer campo...', 'class': 'form-control'}
    )
    
    def validate_data_inicio(self, field):
        if field.data:
            try:
                datetime.strptime(field.data, '%d/%m/%Y')
            except ValueError:
                raise ValidationError('Use o formato DD/MM/AAAA')
    
    def validate_data_fim(self, field):
        if field.data:
            try:
                datetime.strptime(field.data, '%d/%m/%Y')
            except ValueError:
                raise ValidationError('Use o formato DD/MM/AAAA')

    def validate_data_prevista_inicio(self, field):
        if field.data:
            try:
                datetime.strptime(field.data, '%d/%m/%Y')
            except ValueError:
                raise ValidationError('Use o formato DD/MM/AAAA')
    
    def validate_data_prevista_fim(self, field):
        if field.data:
            try:
                datetime.strptime(field.data, '%d/%m/%Y')
            except ValueError:
                raise ValidationError('Use o formato DD/MM/AAAA')
